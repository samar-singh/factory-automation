"""Inventory-related tools for orchestrators"""

import json
import logging
from typing import Any, Dict, List

from agents import function_tool

logger = logging.getLogger(__name__)


class InventoryTools:
    """Inventory search and management tools"""
    
    def __init__(self, chromadb_client, embeddings_manager=None, mode="execute"):
        """
        Initialize inventory tools
        
        Args:
            chromadb_client: ChromaDB client for vector search
            embeddings_manager: Embeddings manager for v4 (optional)
            mode: "execute" for v3, "propose" for v4
        """
        self.chromadb_client = chromadb_client
        self.embeddings_manager = embeddings_manager
        self.mode = mode
    
    def create_tools(self):
        """Create and return inventory-related tools"""
        tools = []
        
        # Inventory search tool
        @function_tool(
            name_override="search_inventory" if self.mode == "execute" else "search_inventory_for_proposal",
            description_override="Search inventory using semantic similarity in ChromaDB" if self.mode == "execute" else "Search inventory to enrich proposal with accurate data. Does not reserve or modify inventory.",
        )
        def search_inventory(query: str, min_quantity: int = 0, limit: int = 5) -> str:
            """Search ChromaDB for matching inventory"""
            try:
                # For v4 with embeddings manager
                if self.mode == "propose" and self.embeddings_manager:
                    # Generate embedding for the query
                    query_embeddings = self.embeddings_manager.encode_queries([query])
                    # Convert to list if it's a numpy array
                    if hasattr(query_embeddings, 'tolist'):
                        query_embedding = query_embeddings[0].tolist()
                    else:
                        query_embedding = query_embeddings[0]
                    
                    # Search with pre-computed embedding
                    results = self.chromadb_client.search(
                        query=query,
                        query_embedding=query_embedding,
                        n_results=limit
                    )
                else:
                    # For v3 or when no embeddings manager
                    where = {}
                    if min_quantity > 0:
                        where["stock"] = {"$gte": min_quantity}
                    
                    results = self.chromadb_client.collection.query(
                        query_texts=[query],
                        n_results=limit,
                        where=where if where else None,
                        include=["metadatas", "distances", "documents"],
                    )
                
                # Format results
                matches = []
                if results and results.get("ids") and len(results["ids"]) > 0:
                    for i in range(len(results["ids"][0]) if isinstance(results["ids"][0], list) else len(results["ids"])):
                        # Handle both nested and flat result structures
                        if isinstance(results["ids"][0], list):
                            item_id = results["ids"][0][i]
                            metadata = results["metadatas"][0][i] if "metadatas" in results else {}
                            distance = results["distances"][0][i] if "distances" in results else 0.5
                            document = results["documents"][0][i] if "documents" in results else ""
                        else:
                            item_id = results["ids"][i]
                            metadata = results["metadatas"][i] if "metadatas" in results else {}
                            distance = results["distances"][i] if "distances" in results else 0.5
                            document = results["documents"][i] if "documents" in results else ""
                        
                        similarity = 1 - distance
                        
                        match_data = {
                            "item_id": item_id,
                            "name": metadata.get("trim_name", metadata.get("tag_name", "Unknown")),
                            "code": metadata.get("trim_code", metadata.get("tag_code", item_id)),
                            "brand": metadata.get("brand", "Unknown"),
                            "stock": metadata.get("stock", metadata.get("quantity", 0)),
                            "price": metadata.get("price", 0),
                            "similarity_score": similarity,
                            "description": document[:200] if document else "",
                        }
                        
                        # Add mode-specific fields
                        if self.mode == "propose":
                            match_data["confidence"] = similarity
                            match_data["metadata"] = metadata
                        
                        matches.append(match_data)
                
                # Return format based on mode
                if self.mode == "propose":
                    return json.dumps({
                        "success": True,
                        "query": query,
                        "matches_found": len(matches),
                        "matches": matches,
                        "message": f"Found {len(matches)} inventory matches for proposal"
                    })
                else:
                    return json.dumps(matches, indent=2)
                    
            except Exception as e:
                logger.error(f"Error searching inventory: {e}")
                if self.mode == "propose":
                    return json.dumps({
                        "success": False,
                        "error": str(e),
                        "matches": []
                    })
                else:
                    return json.dumps({"error": str(e), "matches": []})
        
        tools.append(search_inventory)
        
        # Visual search tool
        @function_tool(
            name_override="search_visual",
            description_override="Search inventory by visual features or image description",
        )
        def search_visual(description: str, limit: int = 5) -> List[Dict[str, Any]]:
            """Visual similarity search"""
            try:
                # For now, use text-based search with visual keywords
                visual_query = f"visual appearance {description}"
                
                if self.mode == "propose" and self.embeddings_manager:
                    # Use embeddings for v4
                    query_embeddings = self.embeddings_manager.encode_queries([visual_query])
                    if hasattr(query_embeddings, 'tolist'):
                        query_embedding = query_embeddings[0].tolist()
                    else:
                        query_embedding = query_embeddings[0]
                    
                    results = self.chromadb_client.search(
                        query=visual_query,
                        query_embedding=query_embedding,
                        n_results=limit
                    )
                else:
                    # Use standard query for v3
                    results = self.chromadb_client.collection.query(
                        query_texts=[visual_query],
                        n_results=limit,
                        where=(
                            {"has_image": True}
                            if hasattr(self.chromadb_client, "has_image_field")
                            else None
                        ),
                        include=["metadatas", "distances"],
                    )
                
                matches = []
                if results and results.get("ids"):
                    for i in range(len(results["ids"][0]) if isinstance(results["ids"][0], list) else len(results["ids"])):
                        if isinstance(results["ids"][0], list):
                            item_id = results["ids"][0][i]
                            metadata = results["metadatas"][0][i] if "metadatas" in results else {}
                            distance = results["distances"][0][i] if "distances" in results else 0.5
                        else:
                            item_id = results["ids"][i]
                            metadata = results["metadatas"][i] if "metadatas" in results else {}
                            distance = results["distances"][i] if "distances" in results else 0.5
                        
                        similarity = 1 - distance
                        
                        matches.append(
                            {
                                "item_id": item_id,
                                "name": metadata.get("trim_name", metadata.get("tag_name", "Unknown")),
                                "visual_match_score": similarity,
                                "image_available": metadata.get("has_image", False),
                                "visual_features": metadata.get("visual_features", []),
                            }
                        )
                
                return json.dumps(matches)  # Return JSON string for consistency
            except Exception as e:
                logger.error(f"Error in visual search: {e}")
                return json.dumps([])  # Return empty JSON array string
        
        tools.append(search_visual)
        
        return tools