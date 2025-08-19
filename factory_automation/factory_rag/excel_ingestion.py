"""Excel to ChromaDB ingestion module for inventory data with Stella-400M embeddings"""

import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ..factory_config.settings import settings
from ..factory_database.vector_db import ChromaDBClient
from .embeddings_config import EmbeddingsManager

logger = logging.getLogger(__name__)


class ExcelInventoryIngestion:
    """Handles ingestion of Excel inventory files into ChromaDB for RAG with enhanced embeddings"""

    # Column mappings to handle variations across Excel files
    COLUMN_MAPPINGS = {
        "code": [
            "TRIM CODE",
            "TRIMCODE",
            "CODE",
            "ITEM CODE",
            "SL.NO",
            "TAG CODE",
            "S.NO",
        ],
        "name": [
            "TRIM NAME",
            "TAG NAME",
            "NAME",
            "ITEM NAME",
            "DESCRIPTION",
            "THREAD NAME",
            "THREAD NAME ",
            "TAGNAME",
        ],
        "stock": ["STOCK", "QTY", " QTY", "QUANTITY", "AVAILABLE", "INVENTORY"],
        "image": [
            "TAGS IMAGE",
            "TAG IMAGES",
            "TAG IMAGE",
            "IMAGE",
            "IMAGES",
            "THREAD IMAGE",
            "TAGIMAGE",
        ],
        "serial": ["S NO", "S.NO", "SL .NO", "SR NO", "SERIAL", "SL.NO", "S.NO"],
        "brand": ["BRAND", "TRIMS BRAND", "TAG BRAND"],
    }

    def __init__(
        self,
        chroma_client: Optional[ChromaDBClient] = None,
        embedding_model: str = "stella-400m",
        device: str = "cpu",
    ):
        """Initialize ingestion module with Stella embeddings

        Args:
            chroma_client: ChromaDB client instance
            embedding_model: Which embedding model to use ('stella-400m', 'e5-large-v2', etc.)
            device: 'cpu' or 'cuda'
        """
        self.settings = settings
        self.chroma_client = chroma_client or ChromaDBClient()

        # Initialize embeddings manager with Stella-400M
        logger.info(f"Initializing {embedding_model} embeddings on {device}")
        self.embeddings_manager = EmbeddingsManager(embedding_model, device)

        # Update ChromaDB collection to use custom embeddings
        self._update_chroma_collection()

    def _update_chroma_collection(self):
        """Update ChromaDB collection to use Stella embeddings"""
        # ChromaDB will use our custom embeddings function
        self.embedding_function = (
            lambda texts: self.embeddings_manager.encode_documents(texts)
        )

    def _normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to standard format"""
        normalized_df = df.copy()

        # Create reverse mapping
        for standard_name, variations in self.COLUMN_MAPPINGS.items():
            for col in df.columns:
                # Convert column to string if it's not already (handles datetime objects)
                col_str = str(col) if not isinstance(col, str) else col

                # Check if the column matches any variation
                if col_str.upper().strip() in [v.upper() for v in variations]:
                    normalized_df.rename(columns={col: standard_name}, inplace=True)
                    break

        return normalized_df

    def _clean_stock_value(self, value: Any) -> int:
        """Clean stock values - convert NILL/NIL to 0"""
        if pd.isna(value):
            return 0

        str_value = str(value).upper().strip()
        if str_value in ["NILL", "NIL", "NULL", "NA", "N/A", "-"]:
            return 0

        try:
            # Handle float values first
            if isinstance(value, (int, float)):
                return int(value)
            
            # Remove any commas and convert to int
            # Also handle decimal points by converting to float first
            clean_value = str(value).replace(",", "")
            if "." in clean_value:
                return int(float(clean_value))
            return int(clean_value)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse stock value: {value}")
            return 0

    def _extract_brand_from_filename(self, filename: str) -> str:
        """Extract brand name from Excel filename"""
        # Remove extension and year suffix
        base_name = Path(filename).stem
        base_name = base_name.replace(" STOCK 2026", "").replace(" 2026", "")
        base_name = base_name.replace(" STOCK", "").strip()

        # Handle special cases
        if "(" in base_name and ")" in base_name:
            # Extract text before parentheses
            base_name = base_name.split("(")[0].strip()

        return base_name

    def _create_searchable_text(self, row: pd.Series, brand: str) -> str:
        """Create comprehensive searchable text for RAG - optimized for Stella embeddings"""
        parts = []

        # Brand is important for matching
        parts.append(f"Brand: {brand}")

        # Add code if exists
        if "code" in row and pd.notna(row["code"]):
            code = str(row["code"]).strip()
            parts.append(f"Code: {code}")
            # Also add code without prefix for better matching
            parts.append(code)

        # Add name/description if exists
        if "name" in row and pd.notna(row["name"]):
            # Clean up newlines and extra spaces
            clean_name = " ".join(str(row["name"]).split())
            parts.append(f"Product: {clean_name}")

            # Extract key attributes from name for better semantic matching
            name_lower = clean_name.lower()

            # Material attributes
            materials = []
            if "silk" in name_lower:
                materials.append("silk")
            if "cotton" in name_lower:
                materials.append("cotton")
            if "polyester" in name_lower:
                materials.append("polyester")
            if "wool" in name_lower:
                materials.append("wool")
            if materials:
                parts.append(f"Material: {', '.join(materials)}")

            # Color attributes
            colors = []
            for color in [
                "black",
                "white",
                "blue",
                "red",
                "green",
                "gold",
                "silver",
                "purple",
                "pink",
                "grey",
                "gray",
                "navy",
                "brown",
            ]:
                if color in name_lower:
                    colors.append(color)

            # Also check for COLOUR column
            if "COLOUR" in row and pd.notna(row["COLOUR"]):
                color_value = str(row["COLOUR"]).strip().lower()
                if color_value and color_value not in colors:
                    colors.append(color_value)

            if colors:
                parts.append(f"Color: {', '.join(colors)}")

            # Style attributes
            if "formal" in name_lower:
                parts.append("Style: formal")
            if "casual" in name_lower:
                parts.append("Style: casual")
            if "sport" in name_lower:
                parts.append("Style: sport")

            # Special features
            if "thread" in name_lower:
                parts.append("Feature: with thread")
            if "sustainable" in name_lower or "fsc" in name_lower:
                parts.append("Feature: sustainable")
            if "premium" in name_lower:
                parts.append("Feature: premium")

        # Add stock status
        stock = self._clean_stock_value(row.get("stock", 0))
        if stock > 0:
            parts.append(f"Stock available: {stock} units")
            parts.append("In stock")
        else:
            parts.append("Out of stock")
            parts.append("No stock available")

        # Create a natural sentence as well for better semantic understanding
        if (
            "name" in row
            and pd.notna(row["name"])
            and "code" in row
            and pd.notna(row["code"])
        ):
            natural_desc = f"This is a {brand} tag with code {row['code']} described as {row['name']}"
            parts.append(natural_desc)

        return " | ".join(parts)

    def _create_document_id(self, row: pd.Series, brand: str) -> str:
        """Create unique document ID for ChromaDB"""
        # Use code if available and not NILL/NIL/empty
        if "code" in row and pd.notna(row["code"]):
            # Convert to string first (handles datetime or other objects)
            code = str(row["code"]).strip().upper()
            # Check if code is actually meaningful
            if code and code not in ["NILL", "NIL", "NA", "-", ""]:
                return f"{brand}_{code}".replace(" ", "_")

        # Otherwise use hash of all available data to ensure uniqueness
        content_parts = [brand]

        # Add name if available
        if "name" in row and pd.notna(row["name"]):
            content_parts.append(str(row["name"]).strip())

        # Add row index from original dataframe if available
        if "row_index" in row:
            content_parts.append(str(row["row_index"]))

        # Add any other identifying fields
        for field in ["serial", "stock", "image"]:
            if field in row and pd.notna(row[field]):
                content_parts.append(str(row[field]))

        # Create hash from combined content
        content = "_".join(content_parts)
        return hashlib.md5(content.encode()).hexdigest()

    def ingest_excel_file(
        self, file_path: str, batch_size: int = 100, sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ingest a single Excel file into ChromaDB with Stella embeddings
        
        Args:
            file_path: Path to Excel file
            batch_size: Number of items to process at once
            sheet_name: Specific sheet to ingest (None = all sheets)
        """
        logger.info(f"Ingesting Excel file: {file_path}")

        try:
            # Check available sheets first
            xl_file = pd.ExcelFile(file_path)
            available_sheets = xl_file.sheet_names
            logger.info(f"Available sheets: {available_sheets}")
            
            # Determine which sheets to process
            if sheet_name:
                sheets_to_process = [sheet_name] if sheet_name in available_sheets else []
            else:
                # Process all sheets
                sheets_to_process = available_sheets
            
            all_results = {
                "status": "success",
                "file": file_path,
                "sheets_processed": [],
                "total_items_ingested": 0,
                "embedding_model": self.embeddings_manager.model_name,
            }
            
            for sheet in sheets_to_process:
                logger.info(f"Processing sheet: {sheet}")
                
                # Read Excel sheet - first try with default header
                df = pd.read_excel(file_path, sheet_name=sheet)

                # Check if any column is a datetime object (indicates header might be in wrong row)
                has_datetime_column = any(
                    isinstance(col, pd.Timestamp) or hasattr(col, "date")
                    for col in df.columns
                )

                # Also check if columns are mostly unnamed (another indicator of wrong header)
                unnamed_columns = sum(1 for col in df.columns if "Unnamed" in str(col))
                total_columns = len(df.columns)
                mostly_unnamed = unnamed_columns > total_columns / 2

                # Check if file is PETER ENGLAND (specific case)
                is_peter_england = "PETER ENGLAND" in file_path.upper()

                # Don't re-read if columns look reasonable
                has_name_column = any("NAME" in str(col).upper() for col in df.columns)

                if (has_datetime_column or is_peter_england) and not has_name_column:
                    logger.info("Detected header issue, re-reading with header=1")
                    # Re-read with header in second row
                    df = pd.read_excel(file_path, sheet_name=sheet, header=1)
                elif mostly_unnamed and not has_name_column:
                    logger.info("Many unnamed columns, checking if header is in wrong row")
                    # Check if first row contains actual headers
                    first_row = df.iloc[0]
                    if any(
                        "NAME" in str(val).upper()
                        for val in first_row.values
                        if pd.notna(val)
                    ):
                        logger.info(
                            "Found headers in first data row, re-reading with header=1"
                        )
                        df = pd.read_excel(file_path, sheet_name=sheet, header=1)
                
                # Handle merged cells for Sheet2 (common pattern in inventory files)
                if sheet.lower() == 'sheet2' or 'sheet2' in sheet.lower():
                    logger.info("Detected Sheet2, checking for merged cells...")
                    
                    # Check if TRIM NAME column has many NaN values (indicates merged cells)
                    if 'TRIM NAME' in df.columns:
                        nan_count = df['TRIM NAME'].isna().sum()
                        total_rows = len(df)
                        if nan_count > total_rows * 0.5:  # More than 50% NaN likely means merged cells
                            logger.info(f"Found {nan_count}/{total_rows} NaN values in TRIM NAME, applying forward fill for merged cells")
                            df['TRIM NAME'] = df['TRIM NAME'].fillna(method='ffill')
                    
                    # Also handle other columns that might have merged cells
                    for col in ['NAME', 'ITEM NAME', 'PRODUCT NAME']:
                        if col in df.columns:
                            nan_count = df[col].isna().sum()
                            if nan_count > len(df) * 0.5:
                                logger.info(f"Applying forward fill to {col} column")
                                df[col] = df[col].fillna(method='ffill')

                # Normalize columns
                df = self._normalize_column_names(df)

                # Extract brand from filename
                brand = self._extract_brand_from_filename(os.path.basename(file_path))

                # Prepare documents for ChromaDB
                documents = []
                metadatas = []
                ids = []
                id_counter = {}  # Track duplicate IDs

                for idx, row in df.iterrows():
                    # Skip rows with no meaningful data
                    if "name" not in row or pd.isna(row.get("name")):
                        continue

                    # Create searchable text optimized for Stella
                    text = self._create_searchable_text(row, brand)

                    # Create metadata
                    metadata = {
                        "brand": brand,
                        "excel_source": os.path.basename(file_path),
                        "sheet": sheet,  # Add sheet name to metadata
                        "row_index": idx,
                        "stock": self._clean_stock_value(row.get("stock", 0)),
                    }

                    # Add optional fields if they exist
                    if "code" in row and pd.notna(row["code"]):
                        metadata["trim_code"] = str(row["code"]).strip()
                        metadata["tag_code"] = str(row["code"]).strip()  # Add tag_code for compatibility
                    if "name" in row and pd.notna(row["name"]):
                        metadata["trim_name"] = str(row["name"]).strip()
                        metadata["tag_name"] = str(row["name"]).strip()  # Add tag_name for compatibility
                    if "image" in row and pd.notna(row["image"]):
                        metadata["has_image"] = True
                        metadata["image_ref"] = str(row["image"])
                    else:
                        metadata["has_image"] = False
                    if "COLOUR" in row and pd.notna(row["COLOUR"]):
                        metadata["colour"] = str(row["COLOUR"]).strip()
                    
                    # Add size and quantity for Sheet2 data
                    if "SIZE" in df.columns and pd.notna(row.get("SIZE")):
                        metadata["size"] = str(row["SIZE"]).strip()
                    
                    # Handle quantity - it might be in QTY column or already in stock
                    if "QTY" in df.columns and pd.notna(row.get("QTY")):
                        qty_value = self._clean_stock_value(row["QTY"])
                        metadata["quantity"] = str(qty_value)
                        metadata["QTY"] = str(qty_value)  # Keep both for compatibility
                    elif "stock" in row and pd.notna(row.get("stock")):
                        # If QTY column doesn't exist but stock does, use stock as quantity
                        metadata["quantity"] = str(metadata["stock"])
                        metadata["QTY"] = str(metadata["stock"])
                    
                    if "brand" in row and pd.notna(row["brand"]):
                        # Override file-based brand with Excel data brand
                        metadata["brand"] = str(row["brand"]).strip()

                    # Create document ID (include sheet and row index for uniqueness)
                    row_with_index = row.copy()
                    row_with_index["row_index"] = idx
                    doc_id = f"{sheet}_{self._create_document_id(row_with_index, brand)}"

                    # Handle duplicate IDs by appending counter
                    if doc_id in id_counter:
                        id_counter[doc_id] += 1
                        doc_id = f"{doc_id}_{id_counter[doc_id]}"
                    else:
                        id_counter[doc_id] = 0

                    documents.append(text)
                    metadatas.append(metadata)
                    ids.append(doc_id)

                # Process in batches and add to ChromaDB for this sheet
                if documents:
                    sheet_added = 0
                    for i in range(0, len(documents), batch_size):
                        batch_docs = documents[i : i + batch_size]
                        batch_metas = metadatas[i : i + batch_size]
                        batch_ids = ids[i : i + batch_size]

                        # Generate embeddings using Stella
                        embeddings = self.embeddings_manager.encode_documents(batch_docs)

                        # Add to ChromaDB with custom embeddings
                        self.chroma_client.collection.add(
                            documents=batch_docs,
                            metadatas=batch_metas,
                            ids=batch_ids,
                            embeddings=embeddings.tolist(),
                        )

                        sheet_added += len(batch_docs)
                        logger.info(
                            f"Sheet {sheet}: Added batch {i//batch_size + 1}, total: {sheet_added}/{len(documents)}"
                        )

                    logger.info(
                        f"Successfully ingested {len(documents)} items from {file_path} - {sheet}"
                    )
                    
                    all_results["sheets_processed"].append({
                        "sheet": sheet,
                        "items_ingested": len(documents)
                    })
                    all_results["total_items_ingested"] += len(documents)
                else:
                    logger.warning(f"No valid items found in {file_path} - {sheet}")
                    all_results["sheets_processed"].append({
                        "sheet": sheet,
                        "items_ingested": 0,
                        "message": "No valid items found"
                    })
            
            # Add brand to results
            all_results["brand"] = self._extract_brand_from_filename(os.path.basename(file_path))
            
            return all_results

        except Exception as e:
            logger.error(f"Error ingesting {file_path}: {e}")
            return {"status": "error", "file": file_path, "error": str(e)}

    def ingest_inventory_folder(self, folder_path: str, include_sheet2: bool = True) -> List[Dict[str, Any]]:
        """Ingest all Excel files from inventory folder
        
        Args:
            folder_path: Path to folder containing Excel files
            include_sheet2: Whether to process Sheet2 (handles merged cells automatically)
        """
        results = []

        # Find all Excel files
        excel_extensions = [".xlsx", ".xls"]
        excel_files = []

        for file in os.listdir(folder_path):
            if any(file.lower().endswith(ext) for ext in excel_extensions):
                # Skip temporary Excel files that start with ~$
                if not file.startswith('~$'):
                    excel_files.append(os.path.join(folder_path, file))

        logger.info(f"Found {len(excel_files)} Excel files to ingest")

        # Ingest each file
        for file_path in excel_files:
            result = self.ingest_excel_file(file_path)
            results.append(result)

        # Summary
        total_items = sum(
            r.get("total_items_ingested", r.get("items_ingested", 0)) 
            for r in results if r.get("status") == "success"
        )
        total_sheets = sum(
            len(r.get("sheets_processed", [])) 
            for r in results if r.get("status") == "success"
        )
        
        logger.info(f"Total items ingested: {total_items} from {total_sheets} sheets")

        return results

    def search_inventory(
        self,
        query: str,
        brand_filter: Optional[str] = None,
        min_stock: int = 0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search inventory using RAG with Stella embeddings"""

        # Generate query embedding using Stella's query mode
        query_embedding = self.embeddings_manager.encode_queries([query])[0]

        # Build filter
        where_filter = {}
        if brand_filter:
            where_filter["brand"] = brand_filter
        if min_stock > 0:
            where_filter["stock"] = {"$gte": min_stock}

        # Perform search with custom embedding
        results = self.chroma_client.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=limit,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted_results = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                result = {
                    "id": results["ids"][0][i],
                    "score": 1
                    - results["distances"][0][i],  # Convert distance to similarity
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                }
                formatted_results.append(result)

        return formatted_results

    def find_similar_items(
        self, item_code: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find items similar to a given item code"""

        # First, get the item's embedding
        item_result = self.chroma_client.collection.get(
            ids=[item_code], include=["documents", "embeddings"]
        )

        if not item_result["ids"]:
            return []

        # Use the item's embedding to find similar items
        item_embedding = item_result["embeddings"][0]

        results = self.chroma_client.collection.query(
            query_embeddings=[item_embedding],
            n_results=limit + 1,  # +1 because it will include itself
            include=["documents", "metadatas", "distances"],
        )

        # Format and exclude the original item
        formatted_results = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                if results["ids"][0][i] != item_code:
                    result = {
                        "id": results["ids"][0][i],
                        "score": 1 - results["distances"][0][i],
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                    }
                    formatted_results.append(result)

        return formatted_results[:limit]


# Utility function to test the ingestion
def test_excel_ingestion():
    """Test the Excel ingestion with Stella embeddings"""
    ingestion = ExcelInventoryIngestion(embedding_model="stella-400m")

    # Test search functionality
    test_queries = [
        "Allen Solly black cotton casual tag",
        "Myntra sustainable tag with thread",
        "Peter England formal blue tag",
        "tags with available stock",
    ]

    print("Testing search with Stella-400M embeddings:\n")
    for query in test_queries:
        print(f"Query: {query}")
        results = ingestion.search_inventory(query, min_stock=1, limit=3)

        if results:
            for result in results:
                print(
                    f"  - {result['metadata'].get('trim_name', 'N/A')} "
                    f"(Code: {result['metadata'].get('trim_code', 'N/A')}, "
                    f"Stock: {result['metadata'].get('stock', 0)}, "
                    f"Score: {result['score']:.3f})"
                )
        else:
            print("  No results found")
        print()
