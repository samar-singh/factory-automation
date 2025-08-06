"""Bridge module to connect AI orchestrator with Gradio UI."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from openai import AsyncOpenAI

from ..factory_config.settings import settings
from ..factory_database.vector_db import ChromaDBClient
from ..factory_rag.excel_ingestion import ExcelInventoryIngestion
from .orchestrator_agent import OrchestratorAgent

logger = logging.getLogger(__name__)


class AIBridge:
    """Connects the AI orchestrator to the Gradio UI for intelligent processing."""

    def __init__(
        self,
        chroma_client: Optional[ChromaDBClient] = None,
        embedding_model: str = "stella-400m",
    ):
        """Initialize the AI bridge with necessary components."""
        self.chroma_client = chroma_client or ChromaDBClient(
            collection_name="tag_inventory_stella"
        )
        self.orchestrator = OrchestratorAgent(self.chroma_client)
        self.ingestion = ExcelInventoryIngestion(
            chroma_client=self.chroma_client, embedding_model=embedding_model
        )

        # Initialize OpenAI client for AI enhancements
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def process_order_with_ai(
        self, order_text: str
    ) -> Tuple[pd.DataFrame, str, Dict[str, Any]]:
        """Process order text using AI orchestrator for intelligent parsing and matching.

        Args:
            order_text: Raw order text from email or UI

        Returns:
            Tuple of (results_dataframe, recommendation, ai_context)
        """
        try:
            # First, use GPT-4 to understand the order
            logger.info("Using GPT-4 to understand the order")

            # Get AI understanding of the order
            ai_understanding = await self._analyze_order_with_gpt4(order_text)

            # Extract order lines using AI insights
            order_lines = await self._extract_order_lines_with_ai(
                order_text, ai_understanding
            )

            results = []
            auto_approve = True

            for line in order_lines:
                # Search for each item using our embeddings
                search_results = self.ingestion.search_inventory(
                    query=line["query"], limit=3
                )

                if search_results:
                    match = search_results[0]
                    metadata = match.get("metadata", {})
                    stock = metadata.get("stock", 0)
                    confidence_score = match.get("score", 0)
                    product_name = metadata.get("trim_name", "Unknown Product")
                    brand = metadata.get("brand", "Unknown")

                    # Determine action based on confidence and stock
                    if stock > 0:
                        action = "Auto-approve" if confidence_score > 0.8 else "Review"
                    else:
                        action = "Find alternative"
                        auto_approve = False

                    if confidence_score < 0.7:
                        auto_approve = False

                    results.append(
                        {
                            "Order Line": (
                                line["original"][:50] + "..."
                                if len(line["original"]) > 50
                                else line["original"]
                            ),
                            "Best Match": f"{brand} - {product_name}",
                            "Stock Status": f"{stock} units",
                            "Confidence": f"{confidence_score*100:.1f}%",
                            "Action": action,
                            "AI Understanding": line.get("ai_understanding", ""),
                        }
                    )
                else:
                    results.append(
                        {
                            "Order Line": (
                                line["original"][:50] + "..."
                                if len(line["original"]) > 50
                                else line["original"]
                            ),
                            "Best Match": "No match found",
                            "Stock Status": "N/A",
                            "Confidence": "0%",
                            "Action": "Manual search",
                            "AI Understanding": line.get("ai_understanding", ""),
                        }
                    )
                    auto_approve = False

            # Create recommendation based on AI analysis
            if auto_approve:
                recommendation = "✅ AI Recommendation: AUTO-APPROVE - All items available with high confidence"
            else:
                recommendation = (
                    "⚠️ AI Recommendation: MANUAL REVIEW - Some items need attention"
                )

            # Add AI reasoning to recommendation
            recommendation += f"\n\n🤖 AI Analysis:\n{ai_understanding[:500]}..."

            ai_context = {
                "ai_understanding": ai_understanding,
                "order_lines": order_lines,
                "processing_time": asyncio.get_event_loop().time(),
            }

            return pd.DataFrame(results), recommendation, ai_context

        except Exception as e:
            logger.error(f"Error in AI processing: {e}")
            return (
                pd.DataFrame({"Error": [str(e)]}),
                f"❌ AI processing error: {str(e)}",
                {},
            )

    async def _analyze_order_with_gpt4(self, order_text: str) -> str:
        """Use GPT-4 to analyze and understand the order."""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at understanding garment tag orders. 
                        Analyze the order text and extract:
                        1. Each item requested with quantity
                        2. Any special requirements (color, material, urgency)
                        3. Customer intent and priority
                        Provide a clear, structured understanding.""",
                    },
                    {"role": "user", "content": f"Analyze this order:\n\n{order_text}"},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"GPT-4 analysis error: {e}")
            return "AI analysis unavailable"

    async def _extract_order_lines_with_ai(
        self, original_text: str, ai_understanding: str
    ) -> List[Dict[str, str]]:
        """Extract order lines using AI understanding."""
        try:
            # Use GPT-4 to extract structured order lines
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """Extract order lines from the text. For each line provide:
                        1. The original text
                        2. A clean search query for inventory matching
                        3. The quantity requested
                        4. Any special attributes (color, material, brand)
                        
                        Format each line as: ITEM|QUERY|QUANTITY|ATTRIBUTES""",
                    },
                    {
                        "role": "user",
                        "content": f"Original order:\n{original_text}\n\nAI Understanding:\n{ai_understanding}",
                    },
                ],
                temperature=0.1,
                max_tokens=800,
            )

            ai_extraction = response.choices[0].message.content
            order_lines = []

            for line in ai_extraction.split("\n"):
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        # Skip header lines
                        original = parts[0].strip()
                        if original.upper() in [
                            "ITEM",
                            "ORIGINAL",
                            "ORDER LINE",
                            "LINE",
                        ]:
                            continue

                        order_lines.append(
                            {
                                "original": original,
                                "query": parts[1].strip(),
                                "quantity": parts[2].strip(),
                                "ai_understanding": (
                                    parts[3].strip() if len(parts) > 3 else ""
                                ),
                            }
                        )

            # Fallback to simple extraction if AI parsing fails
            if not order_lines:
                import re

                for line in original_text.split("\n"):
                    line = line.strip()
                    if line and any(
                        word in line.lower()
                        for word in ["tag", "tags", "pcs", "pieces", "units"]
                    ):
                        if line.startswith("-"):
                            line = line[1:].strip()

                        quantity_match = re.search(
                            r"(\d+)\s*(pcs|pieces|units)?", line, re.IGNORECASE
                        )
                        quantity = (
                            quantity_match.group(1) if quantity_match else "unknown"
                        )
                        search_query = re.sub(
                            r"\d+\s*(pcs|pieces|units)?", "", line, flags=re.IGNORECASE
                        ).strip()

                        order_lines.append(
                            {
                                "original": line,
                                "query": search_query,
                                "quantity": quantity,
                                "ai_understanding": "Fallback extraction",
                            }
                        )

            return order_lines

        except Exception as e:
            logger.error(f"Order extraction error: {e}")
            # Return empty list on error
            return []

    async def search_with_ai_enhancement(
        self, query: str, confidence_threshold: float, max_results: int
    ) -> pd.DataFrame:
        """Perform search with AI enhancement for better understanding.

        Args:
            query: Search query
            confidence_threshold: Minimum confidence threshold
            max_results: Maximum number of results

        Returns:
            DataFrame with search results
        """
        try:
            # Use GPT-4 to enhance the search query
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a search query optimizer for garment tag inventory.
                        Enhance the user's search query by:
                        1. Expanding abbreviations (VH, FM, etc.)
                        2. Adding relevant synonyms
                        3. Including material and color variations
                        4. Making it more specific for inventory matching
                        Return only the enhanced search query.""",
                    },
                    {"role": "user", "content": f"Enhance this search query: {query}"},
                ],
                temperature=0.3,
                max_tokens=200,
            )

            search_query = response.choices[0].message.content.strip()

            # Perform search
            results = self.ingestion.search_inventory(
                query=search_query, limit=int(max_results)
            )

            # Format results
            if results:
                data = []
                for match in results:
                    metadata = match.get("metadata", {})
                    confidence = match.get("score", 0) * 100

                    if confidence >= confidence_threshold:
                        data.append(
                            {
                                "Item": metadata.get("trim_name", "Unknown"),
                                "Brand": metadata.get("brand", "Unknown"),
                                "Stock": f"{metadata.get('stock', 0)} units",
                                "Confidence %": f"{confidence:.1f}%",
                                "Match Reason": "AI-enhanced search",
                            }
                        )
                return (
                    pd.DataFrame(data)
                    if data
                    else pd.DataFrame({"Message": ["No matches above threshold"]})
                )
            else:
                return pd.DataFrame({"Message": ["No matches found"]})

        except Exception as e:
            logger.error(f"Search error: {e}")
            return pd.DataFrame({"Error": [str(e)]})


# Singleton instance for use in Gradio
_ai_bridge = None


def get_ai_bridge(
    chroma_client: Optional[ChromaDBClient] = None, embedding_model: str = "stella-400m"
) -> AIBridge:
    """Get or create the AI bridge singleton."""
    global _ai_bridge
    if _ai_bridge is None:
        _ai_bridge = AIBridge(chroma_client, embedding_model)
    return _ai_bridge
