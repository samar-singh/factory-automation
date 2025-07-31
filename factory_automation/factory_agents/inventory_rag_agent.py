"""Inventory RAG Agent - Integrates RAG search into the order processing workflow"""

import logging
import re
from typing import Any, Dict, List, Optional

from ..factory_rag.excel_ingestion import ExcelInventoryIngestion
from .base import BaseAgent

logger = logging.getLogger(__name__)


class InventoryRAGAgent(BaseAgent):
    """Agent that uses RAG to match order requests with inventory"""

    def __init__(self, name: str = "InventoryRAGAgent"):
        instructions = """You are an inventory matching agent that uses RAG to find the best matching inventory items for customer orders.
        You analyze order text, extract quantities and requirements, and search the inventory database using semantic search.
        You provide confidence scores and recommendations for each match."""

        super().__init__(name, instructions)
        self.rag_system = ExcelInventoryIngestion(embedding_model="stella-400m")

        # Confidence thresholds
        self.HIGH_CONFIDENCE = 0.85
        self.MEDIUM_CONFIDENCE = 0.70

    def extract_quantity_from_text(self, text: str) -> Optional[int]:
        """Extract quantity from order text"""
        # Look for patterns like "500 tags", "need 1000", "quantity: 200"
        patterns = [
            r"(\d+)\s*(?:tags?|pieces?|units?|nos?|numbers?)",
            r"(?:quantity|qty|need|require)[:\s]+(\d+)",
            r"(\d+)\s+\w+\s+tags?",
        ]

        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return int(match.group(1))

        return None

    def extract_brand_from_text(self, text: str) -> Optional[str]:
        """Extract brand name from order text"""
        # Known brands from Excel files
        known_brands = [
            "ALLEN SOLLY",
            "MYNTRA",
            "PETER ENGLAND",
            "AMAZON",
            "LIFE STYLE",
            "NETPLAY",
            "VH DLS",
            "WOTNOT",
        ]

        text_upper = text.upper()
        for brand in known_brands:
            if brand in text_upper:
                return brand

        return None

    def process_order_request(self, order_text: str) -> Dict[str, Any]:
        """Process an order request and find matching inventory items"""

        logger.info(f"Processing order request: {order_text}")

        # Extract quantity needed
        quantity_needed = self.extract_quantity_from_text(order_text)
        if not quantity_needed:
            quantity_needed = 1  # Default to 1 if not specified

        # Extract brand if mentioned
        brand_filter = self.extract_brand_from_text(order_text)

        # Search inventory
        search_results = self.rag_system.search_inventory(
            query=order_text,
            brand_filter=brand_filter,
            min_stock=0,  # Get all results, we'll filter later
            limit=10,
        )

        # Analyze results
        matches = []
        for result in search_results:
            match_info = {
                "item_code": result["metadata"].get("trim_code", "N/A"),
                "item_name": result["metadata"].get("trim_name", "N/A"),
                "brand": result["metadata"].get("brand", "N/A"),
                "available_stock": result["metadata"].get("stock", 0),
                "confidence_score": result["score"],
                "sufficient_stock": result["metadata"].get("stock", 0)
                >= quantity_needed,
                "match_text": result["text"],
            }
            matches.append(match_info)

        # Determine action based on best match
        if matches:
            best_match = matches[0]
            confidence = best_match["confidence_score"]

            if confidence >= self.HIGH_CONFIDENCE:
                if best_match["sufficient_stock"]:
                    action = "auto_proceed"
                    status = "matched_with_stock"
                else:
                    action = "insufficient_stock"
                    status = "matched_no_stock"
            elif confidence >= self.MEDIUM_CONFIDENCE:
                action = "human_review"
                status = "needs_confirmation"
            else:
                action = "manual_intervention"
                status = "low_confidence"
        else:
            action = "manual_intervention"
            status = "no_matches"

        return {
            "order_text": order_text,
            "quantity_needed": quantity_needed,
            "brand_filter": brand_filter,
            "matches": matches,
            "recommended_action": action,
            "status": status,
            "message": self._generate_status_message(status, matches, quantity_needed),
        }

    def _generate_status_message(
        self, status: str, matches: List[Dict], quantity: int
    ) -> str:
        """Generate human-readable status message"""

        if status == "matched_with_stock":
            match = matches[0]
            return (
                f"Found matching item: {match['item_name']} "
                f"(Code: {match['item_code']}) with {match['available_stock']} units in stock. "
                f"Sufficient for order of {quantity} units."
            )

        elif status == "matched_no_stock":
            match = matches[0]
            return (
                f"Found matching item: {match['item_name']} "
                f"(Code: {match['item_code']}) but only {match['available_stock']} units available. "
                f"Need {quantity} units."
            )

        elif status == "needs_confirmation":
            return (
                f"Found {len(matches)} potential matches. "
                f"Best match: {matches[0]['item_name']} "
                f"with {matches[0]['confidence_score']:.0%} confidence. "
                "Human review recommended."
            )

        elif status == "low_confidence":
            return (
                f"Found {len(matches)} possible matches but confidence is low "
                f"(best: {matches[0]['confidence_score']:.0%}). "
                "Manual intervention required."
            )

        else:
            return "No matching items found in inventory. Manual intervention required."

    def find_alternatives(
        self, item_code: str, min_stock: int = 0
    ) -> List[Dict[str, Any]]:
        """Find alternative items similar to a given item"""

        similar_items = self.rag_system.find_similar_items(item_code, limit=5)

        # Filter by stock if needed
        if min_stock > 0:
            similar_items = [
                item
                for item in similar_items
                if item["metadata"].get("stock", 0) >= min_stock
            ]

        return similar_items

    def run(self, task: str) -> str:
        """Execute the inventory matching task"""

        # Process the order request
        result = self.process_order_request(task)

        # Format response based on action
        response_parts = [
            f"Order Analysis: {result['message']}",
            f"Action Required: {result['recommended_action'].replace('_', ' ').title()}",
        ]

        if result["matches"]:
            response_parts.append("\nTop Matches:")
            for i, match in enumerate(result["matches"][:3], 1):
                stock_status = "✓" if match["sufficient_stock"] else "✗"
                response_parts.append(
                    f"{i}. {match['item_name']} ({match['item_code']})\n"
                    f"   Brand: {match['brand']}, Stock: {match['available_stock']} {stock_status}, "
                    f"Confidence: {match['confidence_score']:.0%}"
                )

        # Add recommendations
        if result["recommended_action"] == "insufficient_stock" and result["matches"]:
            # Find alternatives with sufficient stock
            alternatives = self.find_alternatives(
                result["matches"][0]["item_code"], min_stock=result["quantity_needed"]
            )
            if alternatives:
                response_parts.append("\nAlternative items with sufficient stock:")
                for alt in alternatives[:3]:
                    response_parts.append(
                        f"- {alt['metadata']['trim_name']} "
                        f"(Stock: {alt['metadata']['stock']})"
                    )

        return "\n".join(response_parts)


# Integration with orchestrator
def create_inventory_tool():
    """Create a tool for the orchestrator to use"""
    agent = InventoryRAGAgent()
    return agent.as_tool(
        description="Search inventory using RAG to find matching items for order requests"
    )
