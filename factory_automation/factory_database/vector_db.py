"""Synchronous ChromaDB client for vector storage and retrieval."""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ChromaDBClient:
    """Synchronous client for interacting with ChromaDB."""
    
    def __init__(self, persist_directory: str = "./chroma_data"):
        """Initialize ChromaDB client."""
        self.persist_directory = persist_directory
        
        # Create persistent client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create inventory collection
        self.collection = self.client.get_or_create_collection(
            name="tag_inventory",
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"ChromaDB initialized at {self.persist_directory}")
    
    def add_texts(self, 
                  texts: List[str], 
                  metadatas: List[Dict[str, Any]],
                  ids: List[str],
                  embeddings: Optional[List[List[float]]] = None) -> None:
        """Add texts with metadata to collection"""
        if embeddings:
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
        else:
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
        logger.info(f"Added {len(texts)} documents to collection")
    
    def search(self, 
               query: str, 
               n_results: int = 10,
               where: Optional[Dict[str, Any]] = None,
               query_embedding: Optional[List[float]] = None) -> Dict[str, Any]:
        """Search collection with query"""
        if query_embedding:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
        else:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )
        return results
    
    def delete_all(self) -> None:
        """Delete all documents from collection"""
        # Get all IDs
        results = self.collection.get()
        if results['ids']:
            self.collection.delete(ids=results['ids'])
            logger.info(f"Deleted {len(results['ids'])} documents")
    
    def count(self) -> int:
        """Get count of documents in collection"""
        return self.collection.count()