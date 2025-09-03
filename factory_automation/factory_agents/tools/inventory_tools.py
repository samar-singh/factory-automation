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
            description_override="Search inventory using semantic similarity in ChromaDB. Use AFTER email classification to find matching products. Do NOT use before understanding what the customer needs." if self.mode == "execute" else "Search inventory to enrich proposal with accurate data. Does not reserve or modify inventory. Use AFTER email analysis.",
        )
        async def search_inventory(query: str, min_quantity: int = 0, limit: int = 5) -> str:
            """Search ChromaDB inventory collection for products matching the query.
            
            This tool searches the vector database for inventory items that match the
            given query using semantic similarity. Use this AFTER email classification
            to find products that match customer requirements.
            
            Args:
                query: Search query describing what to find (e.g., "black woven labels size 32", "Allen Solly hang tags")
                min_quantity: Minimum stock quantity required (default 0, filters items with insufficient stock)
                limit: Maximum number of results to return (default 5, max recommended 10)
            
            Returns:
                JSON string with search results:
                - Array of matching items with item_id, name, code, brand, stock, price
                - similarity_score for each match (0.0 to 1.0)
                - description snippet for each item
                - Empty array if no matches found
            """
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
                    # V3 mode - return consistent dict format
                    return json.dumps({
                        "success": True,
                        "query": query,
                        "matches_found": len(matches),
                        "matches": matches,
                        "message": f"Found {len(matches)} inventory matches"
                    })
                    
            except Exception as e:
                logger.error(f"Error searching inventory: {e}")
                # Return consistent error format for both modes
                return json.dumps({
                    "success": False,
                    "error": str(e),
                    "query": query,
                    "matches_found": 0,
                    "matches": [],
                    "message": f"Error searching inventory: {str(e)}"
                })
        
        tools.append(search_inventory)
        
        # Visual search tool
        @function_tool(
            name_override="search_visual",
            description_override="Search inventory by visual features or image description. Use ONLY when you have visual information about products (colors, shapes, images). Do NOT use for text-based searches.",
        )
        async def search_visual(description: str, limit: int = 5) -> str:
            """Search inventory using visual features and image similarity.
            
            This tool searches for products based on visual characteristics like colors,
            shapes, patterns, or appearance. Use this when you have visual information
            from images or detailed visual descriptions in emails.
            
            Args:
                description: Visual description of what to find (e.g., "red rectangular label with white text", "circular hang tag with logo")
                limit: Maximum number of results to return (default 5)
            
            Returns:
                JSON string with visual search results:
                - Array of items with visual similarity scores
                - image_available boolean for each item
                - visual_features list for each match
                - Empty array if no visual matches found
            """
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
                
                # Return consistent dict format
                return json.dumps({
                    "success": True,
                    "image_path": image_path,
                    "matches_found": len(matches),
                    "matches": matches,
                    "message": f"Found {len(matches)} visual matches"
                })
            except Exception as e:
                logger.error(f"Error in visual search: {e}")
                # Return consistent error format
                return json.dumps({
                    "success": False,
                    "error": str(e),
                    "image_path": image_path,
                    "matches_found": 0,
                    "matches": [],
                    "message": f"Error in visual search: {str(e)}"
                })
        
        tools.append(search_visual)
        
        return tools