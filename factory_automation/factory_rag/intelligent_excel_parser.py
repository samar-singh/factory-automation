"""Intelligent Excel Parser using LLMs for dynamic schema detection"""

import json
import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from openai import OpenAI

logger = logging.getLogger(__name__)


class IntelligentExcelParser:
    """AI-powered Excel parser that learns and adapts to any schema"""

    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.schema_cache_path = Path("schema_cache.pkl")
        self.learned_mappings = self._load_learned_mappings()

    def _load_learned_mappings(self) -> Dict[str, Dict]:
        """Load previously learned schema mappings"""
        if self.schema_cache_path.exists():
            with open(self.schema_cache_path, "rb") as f:
                return pickle.load(f)
        return {}

    def _save_learned_mappings(self):
        """Save learned mappings for future use"""
        with open(self.schema_cache_path, "wb") as f:
            pickle.dump(self.learned_mappings, f)

    def analyze_excel_schema(self, df: pd.DataFrame, file_name: str) -> Dict[str, Any]:
        """Use GPT-4 to understand the Excel schema"""

        # Create a sample of the data for analysis
        sample_data = self._create_data_sample(df)

        prompt = f"""Analyze this Excel data structure and identify the schema.
        
File: {file_name}
Columns: {df.columns.tolist()}
Sample data (first 5 rows):
{sample_data}

Identify and map columns to these standard fields:
- product_code: Unique identifier/SKU/code
- product_name: Name/description of the product  
- stock_quantity: Available stock/quantity
- price: Price/cost (if available)
- brand: Brand name
- category: Product category/type
- color: Color information
- size: Size information
- image_reference: Image path/URL
- additional_attributes: Any other relevant fields

Response format:
{{
    "column_mappings": {{
        "actual_column_name": "standard_field_name"
    }},
    "data_quality_issues": [],
    "recommendations": []
}}"""

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing Excel data structures and identifying schemas.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        result = json.loads(response.choices[0].message.content)

        # Cache the learned mapping
        file_pattern = self._extract_file_pattern(file_name)
        self.learned_mappings[file_pattern] = result
        self._save_learned_mappings()

        return result

    def _create_data_sample(self, df: pd.DataFrame) -> str:
        """Create a representative sample of the data"""
        sample_df = df.head(5).copy()

        # Truncate long strings for readability
        for col in sample_df.columns:
            if sample_df[col].dtype == "object":
                sample_df[col] = sample_df[col].apply(
                    lambda x: (
                        str(x)[:50] + "..." if pd.notna(x) and len(str(x)) > 50 else x
                    )
                )

        return sample_df.to_string()

    def _extract_file_pattern(self, file_name: str) -> str:
        """Extract a pattern from filename for caching"""
        # Remove year, dates, and version numbers
        import re

        pattern = re.sub(r"\d{4}", "", file_name)  # Remove years
        pattern = re.sub(r"v\d+", "", pattern)  # Remove versions
        pattern = re.sub(r"\s+", " ", pattern).strip()
        return pattern

    def parse_excel_intelligently(
        self, file_path: str
    ) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """Parse Excel file with intelligent schema detection"""

        # Read the Excel file
        df = pd.read_excel(file_path)
        file_name = Path(file_path).name

        # Check if we've seen similar file before
        file_pattern = self._extract_file_pattern(file_name)

        if file_pattern in self.learned_mappings:
            logger.info(f"Using cached schema for {file_pattern}")
            schema = self.learned_mappings[file_pattern]
        else:
            logger.info(f"Analyzing new schema for {file_name}")
            schema = self.analyze_excel_schema(df, file_name)

        # Apply the mappings
        normalized_df = self._apply_schema_mappings(df, schema["column_mappings"])

        return normalized_df, schema

    def _apply_schema_mappings(
        self, df: pd.DataFrame, mappings: Dict[str, str]
    ) -> pd.DataFrame:
        """Apply the learned mappings to normalize the dataframe"""
        normalized_df = df.copy()

        # Rename columns based on mappings
        rename_dict = {}
        for actual_col, standard_col in mappings.items():
            if actual_col in df.columns and standard_col:
                rename_dict[actual_col] = standard_col

        normalized_df.rename(columns=rename_dict, inplace=True)

        return normalized_df

    def extract_products_with_ai(
        self, df: pd.DataFrame, brand: str
    ) -> List[Dict[str, Any]]:
        """Extract product information using AI to handle any format"""

        products = []

        for idx, row in df.iterrows():
            # Use GPT to extract structured data from unstructured row
            row_text = " | ".join(
                [f"{col}: {val}" for col, val in row.items() if pd.notna(val)]
            )

            if len(row_text.strip()) < 10:  # Skip empty rows
                continue

            prompt = f"""Extract product information from this row:
{row_text}

Brand: {brand}

Return a JSON object with these fields (use null if not found):
{{
    "product_code": "extracted code/sku",
    "product_name": "extracted name/description",
    "stock": "extracted quantity as integer",
    "color": "extracted color",
    "size": "extracted size",
    "category": "inferred category",
    "search_keywords": ["keyword1", "keyword2", ...]
}}"""

            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "Extract structured product data from text.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                )

                product_data = json.loads(response.choices[0].message.content)
                product_data["brand"] = brand
                product_data["row_index"] = idx
                products.append(product_data)

            except Exception as e:
                logger.warning(f"Failed to parse row {idx}: {e}")

        return products


class SelfImprovingExcelIngestion:
    """Excel ingestion that improves over time"""

    def __init__(self, parser: IntelligentExcelParser, chroma_client):
        self.parser = parser
        self.chroma_client = chroma_client
        self.feedback_log = Path("ingestion_feedback.json")

    def ingest_with_feedback(self, file_path: str) -> Dict[str, Any]:
        """Ingest file and collect feedback for improvement"""

        # Parse intelligently
        df, schema = self.parser.parse_excel_intelligently(file_path)

        # Extract brand
        brand = self._extract_brand_from_filename(Path(file_path).name)

        # Extract products with AI
        products = self.parser.extract_products_with_ai(df, brand)

        # Generate quality metrics
        quality_metrics = self._assess_extraction_quality(products)

        # Log the results for learning
        self._log_ingestion_feedback(
            {
                "file": file_path,
                "schema": schema,
                "products_extracted": len(products),
                "quality_metrics": quality_metrics,
            }
        )

        return {
            "status": "success",
            "products": products,
            "schema": schema,
            "quality_metrics": quality_metrics,
        }

    def _assess_extraction_quality(self, products: List[Dict]) -> Dict[str, float]:
        """Assess the quality of extraction"""

        total = len(products)
        if total == 0:
            return {"overall_quality": 0.0}

        metrics = {
            "has_code": sum(1 for p in products if p.get("product_code")) / total,
            "has_name": sum(1 for p in products if p.get("product_name")) / total,
            "has_stock": sum(1 for p in products if p.get("stock") is not None) / total,
            "has_keywords": sum(1 for p in products if p.get("search_keywords"))
            / total,
        }

        metrics["overall_quality"] = sum(metrics.values()) / len(metrics)

        return metrics

    def _log_ingestion_feedback(self, feedback: Dict):
        """Log feedback for continuous improvement"""

        logs = []
        if self.feedback_log.exists():
            with open(self.feedback_log, "r") as f:
                logs = json.load(f)

        logs.append(feedback)

        with open(self.feedback_log, "w") as f:
            json.dump(logs, f, indent=2)

    def _extract_brand_from_filename(self, filename: str) -> str:
        """AI-powered brand extraction"""
        # Could use GPT here too, but keeping simple for now
        base_name = filename.replace(" STOCK 2026", "").replace(".xlsx", "")
        return base_name.split("(")[0].strip()
