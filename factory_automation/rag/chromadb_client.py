"""ChromaDB client for vector storage and retrieval."""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging
import numpy as np

from config.settings import settings

logger = logging.getLogger(__name__)

class ChromaDBClient:
    """Client for interacting with ChromaDB."""
    
    def __init__(self):
        """Initialize ChromaDB client."""
        self.client = None
        self.inventory_collection = None
        self.order_history_collection = None
        self._connected = False
        
    async def initialize(self):
        """Initialize ChromaDB connection and collections."""
        try:
            # Create persistent client
            self.client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Create or get collections
            self.inventory_collection = self.client.get_or_create_collection(
                name="tag_inventory",
                metadata={"hnsw:space": "cosine"}
            )
            
            self.order_history_collection = self.client.get_or_create_collection(
                name="order_history",
                metadata={"hnsw:space": "cosine"}
            )
            
            self._connected = True
            logger.info("ChromaDB initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            self._connected = False
            raise
    
    def is_connected(self) -> bool:
        """Check if ChromaDB is connected."""
        return self._connected
    
    async def add_inventory_item(
        self,
        tag_code: str,
        description: str,
        size: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add an inventory item to the collection.
        
        Args:
            tag_code: Unique tag code
            description: Tag description
            size: Tag size
            embedding: Vector embedding
            metadata: Additional metadata
            
        Returns:
            Document ID
        """
        try:
            doc_id = f"tag_{tag_code}"
            document = f"{tag_code} {description} {size}"
            
            item_metadata = {
                "tag_code": tag_code,
                "description": description,
                "size": size,
                **(metadata or {})
            }
            
            self.inventory_collection.add(
                documents=[document],
                embeddings=[embedding],
                metadatas=[item_metadata],
                ids=[doc_id]
            )
            
            logger.info(f"Added inventory item: {tag_code}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error adding inventory item: {str(e)}")
            raise
    
    async def search_inventory(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search inventory using vector similarity.
        
        Args:
            query_embedding: Query vector
            n_results: Number of results to return
            filter_dict: Optional metadata filters
            
        Returns:
            List of matching items with metadata
        """
        try:
            results = self.inventory_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_dict,
                include=["metadatas", "distances", "documents"]
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "similarity": 1 - results["distances"][0][i]  # Convert distance to similarity
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching inventory: {str(e)}")
            return []
    
    async def update_inventory_item(
        self,
        tag_code: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update an inventory item.
        
        Args:
            tag_code: Tag code to update
            updates: Dictionary of updates
            
        Returns:
            Success status
        """
        try:
            doc_id = f"tag_{tag_code}"
            
            # Get existing item
            existing = self.inventory_collection.get(ids=[doc_id])
            if not existing["ids"]:
                logger.warning(f"Tag {tag_code} not found")
                return False
            
            # Update metadata
            current_metadata = existing["metadatas"][0]
            current_metadata.update(updates)
            
            # Update in collection
            self.inventory_collection.update(
                ids=[doc_id],
                metadatas=[current_metadata]
            )
            
            logger.info(f"Updated inventory item: {tag_code}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating inventory item: {str(e)}")
            return False
    
    async def delete_inventory_item(self, tag_code: str) -> bool:
        """Delete an inventory item.
        
        Args:
            tag_code: Tag code to delete
            
        Returns:
            Success status
        """
        try:
            doc_id = f"tag_{tag_code}"
            self.inventory_collection.delete(ids=[doc_id])
            logger.info(f"Deleted inventory item: {tag_code}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting inventory item: {str(e)}")
            return False
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about collections.
        
        Returns:
            Collection statistics
        """
        try:
            inv_count = self.inventory_collection.count()
            order_count = self.order_history_collection.count()
            
            return {
                "inventory_items": inv_count,
                "order_history": order_count,
                "status": "connected"
            }
            
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {
                "error": str(e),
                "status": "error"
            }