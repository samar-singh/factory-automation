"""AI Bridge with debug breakpoints for pdb debugging."""

import asyncio
import logging
import pdb
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from openai import AsyncOpenAI

from ..factory_config.settings import settings
from ..factory_database.vector_db import ChromaDBClient
from ..factory_rag.excel_ingestion import ExcelInventoryIngestion
from .orchestrator_agent import OrchestratorAgent

logger = logging.getLogger(__name__)


class AIBridgeDebug:
    """AI Bridge with debugging breakpoints."""

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
        """Process order text using AI with debug breakpoints."""

        print("\n[DEBUG] Entering process_order_with_ai")
        print(f"[DEBUG] Order text length: {len(order_text)}")

        try:
            print("\n[DEBUG] About to analyze order with GPT-4...")
            pdb.set_trace()  # BREAKPOINT 1: Before GPT-4 analysis

            # Get AI understanding of the order
            ai_understanding = await self._analyze_order_with_gpt4(order_text)
            print(f"[DEBUG] AI understanding length: {len(ai_understanding)}")

            print("\n[DEBUG] About to extract order lines...")
            pdb.set_trace()  # BREAKPOINT 2: Before order line extraction

            # Extract order lines using AI insights
            order_lines = await self._extract_order_lines_with_ai(
                order_text, ai_understanding
            )
            print(f"[DEBUG] Extracted {len(order_lines)} order lines")

            results = []
            auto_approve = True

            print("\n[DEBUG] About to search inventory for each line...")
            pdb.set_trace()  # BREAKPOINT 3: Before inventory search

            for idx, line in enumerate(order_lines):
                print(f"\n[DEBUG] Processing line {idx + 1}: {line['query']}")

                # Search for each item using our embeddings
                search_results = self.ingestion.search_inventory(
                    query=line["query"], limit=3
                )

                if search_results:
                    print(f"[DEBUG] Found {len(search_results)} matches")
                    match = search_results[0]
                    metadata = match.get("metadata", {})
                    stock = metadata.get("stock", 0)
                    confidence_score = match.get("score", 0)
                    product_name = metadata.get("trim_name", "Unknown Product")
                    brand = metadata.get("brand", "Unknown")

                    print(
                        f"[DEBUG] Best match: {brand} - {product_name} (conf: {confidence_score:.2f})"
                    )

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
                    print(f"[DEBUG] No matches found for: {line['query']}")
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

            print(f"\n[DEBUG] Processed all lines. Auto-approve: {auto_approve}")
            pdb.set_trace()  # BREAKPOINT 4: Before creating recommendation

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

            print("\n[DEBUG] Returning results")
            return pd.DataFrame(results), recommendation, ai_context

        except Exception as e:
            logger.error(f"Error in AI processing: {e}")
            print(f"\n[DEBUG] ERROR: {e}")
            print("[DEBUG] Entering exception breakpoint...")
            pdb.set_trace()  # BREAKPOINT 5: Exception handling

            return (
                pd.DataFrame({"Error": [str(e)]}),
                f"❌ AI processing error: {str(e)}",
                {},
            )

    async def _analyze_order_with_gpt4(self, order_text: str) -> str:
        """Use GPT-4 to analyze and understand the order."""
        print("\n[DEBUG] Inside _analyze_order_with_gpt4")

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

            result = response.choices[0].message.content
            print(f"[DEBUG] GPT-4 response received: {len(result)} chars")
            return result

        except Exception as e:
            logger.error(f"GPT-4 analysis error: {e}")
            print(f"[DEBUG] GPT-4 ERROR: {e}")
            return "AI analysis unavailable"

    async def _extract_order_lines_with_ai(
        self, original_text: str, ai_understanding: str
    ) -> List[Dict[str, str]]:
        """Extract order lines using AI understanding."""
        print("\n[DEBUG] Inside _extract_order_lines_with_ai")

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
            print(f"[DEBUG] GPT-4 extraction received: {len(ai_extraction)} chars")
            print(f"[DEBUG] Raw extraction:\n{ai_extraction[:200]}...")

            order_lines = []

            for line in ai_extraction.split("\n"):
                if "|" in line:
                    parts = line.split("|")
                    print(
                        f"[DEBUG] Parsing line with {len(parts)} parts: {line[:50]}..."
                    )

                    if len(parts) >= 3:
                        order_lines.append(
                            {
                                "original": parts[0].strip(),
                                "query": parts[1].strip(),
                                "quantity": parts[2].strip(),
                                "ai_understanding": (
                                    parts[3].strip() if len(parts) > 3 else ""
                                ),
                            }
                        )

            print(f"[DEBUG] Parsed {len(order_lines)} order lines")

            # Fallback to simple extraction if AI parsing fails
            if not order_lines:
                print("[DEBUG] No lines parsed, using fallback extraction")
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

                print(f"[DEBUG] Fallback extracted {len(order_lines)} lines")

            return order_lines

        except Exception as e:
            logger.error(f"Order extraction error: {e}")
            print(f"[DEBUG] Extraction ERROR: {e}")
            return []


# Singleton instance for debugging
_ai_bridge_debug = None


def get_ai_bridge_debug(
    chroma_client: Optional[ChromaDBClient] = None, embedding_model: str = "stella-400m"
) -> AIBridgeDebug:
    """Get or create the debug AI bridge singleton."""
    global _ai_bridge_debug
    if _ai_bridge_debug is None:
        _ai_bridge_debug = AIBridgeDebug(chroma_client, embedding_model)
    return _ai_bridge_debug
