"""Enhanced Inventory RAG Agent with Reranking - Version 2"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..factory_database.vector_db import ChromaDBClient
from ..factory_rag.embeddings_config import EmbeddingsManager
from ..factory_rag.enhanced_search import EnhancedRAGSearch
from .base import BaseAgent

logger = logging.getLogger(__name__)


class InventoryRAGAgentV2(BaseAgent):
    """Enhanced agent with reranking and hybrid search for better accuracy"""

    def __init__(
        self,
        chromadb_client: Optional[ChromaDBClient] = None,
        name: str = "InventoryRAGAgentV2",
        embedding_model: str = "stella-400m",
        reranker_model: str = "bge-reranker-base",
        enable_reranking: bool = True,
        enable_hybrid_search: bool = True,
    ):
        instructions = """You are an enhanced inventory matching agent that uses advanced RAG with reranking.
        You analyze order text, extract quantities and requirements, and search inventory using semantic + keyword search.
        You use cross-encoder reranking for better accuracy and provide detailed confidence scores."""

        super().__init__(name, instructions)

        # Initialize components
        self.chromadb_client = chromadb_client or ChromaDBClient()
        self.embeddings_manager = EmbeddingsManager(embedding_model)

        # Initialize enhanced search with reranking
        self.enhanced_search = EnhancedRAGSearch(
            chromadb_client=self.chromadb_client,
            embeddings_manager=self.embeddings_manager,
            reranker_model=reranker_model,
            enable_reranking=enable_reranking,
            enable_hybrid_search=enable_hybrid_search,
        )

        # Updated confidence thresholds for reranked results
        self.VERY_HIGH_CONFIDENCE = 0.9  # Auto-approve only at 90%+
        self.HIGH_CONFIDENCE = 0.8
        self.MEDIUM_CONFIDENCE = 0.6
        self.LOW_CONFIDENCE = 0.4

        logger.info(
            f"Initialized Enhanced Inventory RAG Agent with reranking={enable_reranking}, hybrid={enable_hybrid_search}"
        )

    def extract_specifications(self, text: str) -> Dict[str, Any]:
        """Extract additional specifications from order text"""
        specs = {}

        # Colors
        colors = ["black", "white", "blue", "red", "green", "yellow", "gold", "silver"]
        for color in colors:
            if color in text.lower():
                specs["color"] = color
                break

        # Materials
        materials = [
            "cotton",
            "polyester",
            "leather",
            "paper",
            "plastic",
            "satin",
            "silk",
        ]
        for material in materials:
            if material in text.lower():
                specs["material"] = material
                break

        # Tag types
        tag_types = [
            "main tag",
            "care label",
            "price tag",
            "hang tag",
            "woven tag",
            "barcode",
        ]
        for tag_type in tag_types:
            if tag_type in text.lower():
                specs["tag_type"] = tag_type
                break

        # Special requirements
        if any(
            word in text.lower() for word in ["sustainable", "eco", "fsc", "recycled"]
        ):
            specs["sustainable"] = True

        if any(
            word in text.lower() for word in ["urgent", "rush", "asap", "immediate"]
        ):
            specs["urgent"] = True

        return specs

    def process_order_request(self, order_text: str) -> Dict[str, Any]:
        """Process order with enhanced search and reranking"""

        logger.info(
            f"Processing order request with enhanced search: {order_text[:100]}..."
        )

        # Note: Quantity and brand extraction should be done by the AI in OrderProcessorAgent
        # This agent focuses purely on inventory matching, not order parsing
        # Using defaults for standalone testing only
        quantity_needed = 1  # Default quantity for matching purposes
        specifications = self.extract_specifications(order_text)

        # No hardcoded filters - let the semantic search handle brand matching
        filters = None

        # Perform enhanced search with reranking
        search_results, search_stats = self.enhanced_search.search(
            query=order_text,
            n_results=5,  # Final results after reranking
            n_candidates=20,  # Initial candidates before reranking
            filters=filters if filters else None,
            score_threshold=self.LOW_CONFIDENCE,  # Minimum threshold
        )

        # Log search statistics
        logger.info(
            f"Search stats: {search_stats['semantic_candidates']} semantic, "
            f"{search_stats['bm25_candidates']} BM25, "
            f"{search_stats['after_reranking']} after reranking, "
            f"{search_stats['final_results']} final results"
        )

        # Analyze and format results
        matches = []
        for result in search_results:
            # Use rerank score if available, otherwise use regular score
            confidence_score = result.get("rerank_score", result.get("score", 0))

            match_info = {
                "item_code": result["metadata"].get("trim_code", "N/A"),
                "item_name": result["metadata"].get("trim_name", "N/A"),
                "brand": result["metadata"].get("brand", "N/A"),
                "available_stock": result["metadata"].get("stock", 0),
                "confidence_score": confidence_score,
                "confidence_level": result.get("confidence_level", "unknown"),
                "confidence_percentage": result.get("confidence_percentage", 0),
                "sufficient_stock": result["metadata"].get("stock", 0)
                >= quantity_needed,
                "match_text": result.get("text", "")[:200],
                "search_method": result.get("source", "unknown"),
                "has_rerank_score": "rerank_score" in result,
            }
            matches.append(match_info)

        # Determine action based on enhanced confidence
        action, status = self._determine_action(matches, quantity_needed)

        return {
            "order_text": order_text,
            "quantity_needed": quantity_needed,
            "specifications": specifications,
            "matches": matches,
            "recommended_action": action,
            "status": status,
            "message": self._generate_status_message(status, matches, quantity_needed),
            "search_statistics": search_stats,
            "reranking_used": self.enhanced_search.enable_reranking,
            "hybrid_search_used": self.enhanced_search.enable_hybrid_search,
        }

    def _determine_action(
        self, matches: List[Dict[str, Any]], quantity_needed: int = 1
    ) -> Tuple[str, str]:
        """Determine action based on enhanced confidence scoring"""

        if not matches:
            return "manual_intervention", "no_matches"

        best_match = matches[0]
        confidence = best_match["confidence_score"]
        has_stock = best_match["sufficient_stock"]

        # New logic: Only auto-approve at 90%+ confidence
        if confidence >= self.VERY_HIGH_CONFIDENCE:
            if has_stock:
                return "auto_approve", "matched_with_stock"
            else:
                return "auto_approve_with_restock", "matched_needs_restock"

        # All other cases go to human review
        elif confidence >= self.MEDIUM_CONFIDENCE:
            if has_stock:
                return "human_review", "good_match_verify"
            else:
                return "human_review", "good_match_no_stock"

        else:
            return "human_review", "low_confidence_verify"

    def _generate_status_message(
        self, status: str, matches: List[Dict], quantity: int
    ) -> str:
        """Generate detailed status message"""

        if not matches:
            return "No matching items found. Manual search required."

        match = matches[0]
        confidence_pct = match["confidence_percentage"]

        messages = {
            "matched_with_stock": (
                f"✅ EXCELLENT MATCH ({confidence_pct}% confidence): {match['item_name']} "
                f"(Code: {match['item_code']}) with {match['available_stock']} units in stock. "
                f"Auto-approving order for {quantity} units."
            ),
            "matched_needs_restock": (
                f"✅ EXCELLENT MATCH ({confidence_pct}% confidence): {match['item_name']} "
                f"(Code: {match['item_code']}) - Only {match['available_stock']} units available. "
                f"Need to restock for {quantity} units."
            ),
            "good_match_verify": (
                f"🔍 Good match found ({confidence_pct}% confidence): {match['item_name']} "
                f"(Code: {match['item_code']}) with {match['available_stock']} units. "
                f"Human verification recommended before processing."
            ),
            "good_match_no_stock": (
                f"🔍 Good match found ({confidence_pct}% confidence): {match['item_name']} "
                f"but insufficient stock ({match['available_stock']}/{quantity} units). "
                f"Human review needed for alternatives."
            ),
            "low_confidence_verify": (
                f"⚠️ Uncertain match ({confidence_pct}% confidence): {match['item_name']}. "
                f"Found {len(matches)} possible matches. Human review required to confirm."
            ),
        }

        return messages.get(status, f"Status: {status}")

    def find_alternatives_enhanced(
        self, item_code: str, min_stock: int = 0, exclude_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Find alternatives using enhanced search"""

        # Get the original item details
        original_item = self.chromadb_client.collection.get(
            ids=[item_code], include=["documents", "metadatas"]
        )

        if not original_item or not original_item["documents"]:
            return []

        # Use the item description as query
        query = original_item["documents"][0]

        # Search for similar items
        results, _ = self.enhanced_search.search(
            query=query,
            n_results=10,
            n_candidates=30,
        )

        # Filter out the original item and apply stock filter
        alternatives = []
        for result in results:
            if result["id"] != item_code and (
                exclude_ids is None or result["id"] not in exclude_ids
            ):
                if min_stock == 0 or result["metadata"].get("stock", 0) >= min_stock:
                    alternatives.append(result)

        return alternatives[:5]  # Return top 5 alternatives

    def explain_match(self, query: str, match: Dict[str, Any]) -> Dict[str, Any]:
        """Explain why an item was matched"""
        return self.enhanced_search.explain_search_result(query, match)

    def run(self, task: str) -> str:
        """Execute enhanced inventory matching"""

        # Process the order request
        result = self.process_order_request(task)

        # Format response
        response_parts = [
            f"📊 Search Method: {'Reranked ' if result['reranking_used'] else ''}"
            f"{'Hybrid' if result['hybrid_search_used'] else 'Semantic'} Search",
            f"\n{result['message']}",
            f"\n🎯 Recommended Action: {result['recommended_action'].replace('_', ' ').title()}",
        ]

        if result["matches"]:
            response_parts.append("\n\n📋 Top Matches:")
            for i, match in enumerate(result["matches"][:3], 1):
                stock_icon = "✅" if match["sufficient_stock"] else "❌"
                rerank_icon = "🔄" if match["has_rerank_score"] else ""

                response_parts.append(
                    f"\n{i}. {match['item_name']} (Code: {match['item_code']})"
                )
                response_parts.append(
                    f"   • Brand: {match['brand']}"
                    f"\n   • Stock: {match['available_stock']} units {stock_icon}"
                    f"\n   • Confidence: {match['confidence_percentage']}% ({match['confidence_level']}) {rerank_icon}"
                    f"\n   • Method: {match['search_method']}"
                )

        # Add search statistics
        stats = result["search_statistics"]
        response_parts.append(
            f"\n\n📈 Search Performance:"
            f"\n   • Candidates examined: {stats['semantic_candidates']}"
            f"\n   • After reranking: {stats.get('after_reranking', 'N/A')}"
            f"\n   • Processing time: {stats.get('rerank_stats', {}).get('time_ms', 'N/A')}ms"
        )

        # Add alternatives for insufficient stock
        if (
            result["status"] in ["matched_needs_restock", "good_match_no_stock"]
            and result["matches"]
        ):
            alternatives = self.find_alternatives_enhanced(
                result["matches"][0]["item_code"], min_stock=result["quantity_needed"]
            )
            if alternatives:
                response_parts.append("\n\n🔄 Alternative items with sufficient stock:")
                for alt in alternatives[:3]:
                    response_parts.append(
                        f"\n   • {alt['metadata']['trim_name']} "
                        f"(Stock: {alt['metadata']['stock']}, "
                        f"Confidence: {alt.get('confidence_percentage', 0)}%)"
                    )

        return "\n".join(response_parts)


# Integration function
def create_enhanced_inventory_tool(
    chromadb_client: Optional[ChromaDBClient] = None,
    enable_reranking: bool = True,
    enable_hybrid_search: bool = True,
):
    """Create enhanced inventory tool with reranking"""
    agent = InventoryRAGAgentV2(
        chromadb_client=chromadb_client,
        enable_reranking=enable_reranking,
        enable_hybrid_search=enable_hybrid_search,
    )
    return agent.as_tool(
        description="Enhanced inventory search with reranking and hybrid search for better accuracy"
    )
