"""Excel to ChromaDB ingestion module for inventory data with Stella-400M embeddings"""

import pandas as pd
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib
from ..factory_database.vector_db import ChromaDBClient
from ..factory_config.settings import settings
from .embeddings_config import EmbeddingsManager
import logging
import numpy as np

logger = logging.getLogger(__name__)

class ExcelInventoryIngestion:
    """Handles ingestion of Excel inventory files into ChromaDB for RAG with enhanced embeddings"""
    
    # Column mappings to handle variations across Excel files
    COLUMN_MAPPINGS = {
        'code': ['TRIM CODE', 'TRIMCODE', 'CODE', 'ITEM CODE'],
        'name': ['TRIM NAME', 'TAG NAME', 'NAME', 'ITEM NAME', 'DESCRIPTION'],
        'stock': ['STOCK', 'QTY', ' QTY', 'QUANTITY', 'AVAILABLE'],
        'image': ['TAGS IMAGE', 'TAG IMAGES', 'TAG IMAGE', 'IMAGE', 'IMAGES'],
        'serial': ['S NO', 'S.NO', 'SL .NO', 'SR NO', 'SERIAL']
    }
    
    def __init__(self, 
                 chroma_client: Optional[ChromaDBClient] = None,
                 embedding_model: str = 'stella-400m',
                 device: str = 'cpu'):
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
        self.embedding_function = lambda texts: self.embeddings_manager.encode_documents(texts)
        
    def _normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to standard format"""
        normalized_df = df.copy()
        
        # Create reverse mapping
        for standard_name, variations in self.COLUMN_MAPPINGS.items():
            for col in df.columns:
                if col.upper().strip() in [v.upper() for v in variations]:
                    normalized_df.rename(columns={col: standard_name}, inplace=True)
                    break
                    
        return normalized_df
    
    def _clean_stock_value(self, value: Any) -> int:
        """Clean stock values - convert NILL/NIL to 0"""
        if pd.isna(value):
            return 0
        
        str_value = str(value).upper().strip()
        if str_value in ['NILL', 'NIL', 'NULL', 'NA', 'N/A', '-']:
            return 0
            
        try:
            # Remove any commas and convert to int
            return int(str(value).replace(',', ''))
        except ValueError:
            logger.warning(f"Could not parse stock value: {value}")
            return 0
    
    def _extract_brand_from_filename(self, filename: str) -> str:
        """Extract brand name from Excel filename"""
        # Remove extension and year suffix
        base_name = Path(filename).stem
        base_name = base_name.replace(' STOCK 2026', '').replace(' 2026', '')
        base_name = base_name.replace(' STOCK', '').strip()
        
        # Handle special cases
        if '(' in base_name and ')' in base_name:
            # Extract text before parentheses
            base_name = base_name.split('(')[0].strip()
            
        return base_name
    
    def _create_searchable_text(self, row: pd.Series, brand: str) -> str:
        """Create comprehensive searchable text for RAG - optimized for Stella embeddings"""
        parts = []
        
        # Brand is important for matching
        parts.append(f"Brand: {brand}")
        
        # Add code if exists
        if 'code' in row and pd.notna(row['code']):
            code = str(row['code']).strip()
            parts.append(f"Code: {code}")
            # Also add code without prefix for better matching
            parts.append(code)
            
        # Add name/description if exists
        if 'name' in row and pd.notna(row['name']):
            # Clean up newlines and extra spaces
            clean_name = ' '.join(str(row['name']).split())
            parts.append(f"Product: {clean_name}")
            
            # Extract key attributes from name for better semantic matching
            name_lower = clean_name.lower()
            
            # Material attributes
            materials = []
            if 'silk' in name_lower:
                materials.append("silk")
            if 'cotton' in name_lower:
                materials.append("cotton")
            if 'polyester' in name_lower:
                materials.append("polyester")
            if 'wool' in name_lower:
                materials.append("wool")
            if materials:
                parts.append(f"Material: {', '.join(materials)}")
            
            # Color attributes
            colors = []
            for color in ['black', 'white', 'blue', 'red', 'green', 'gold', 'silver', 'purple', 'pink', 'grey', 'gray']:
                if color in name_lower:
                    colors.append(color)
            if colors:
                parts.append(f"Color: {', '.join(colors)}")
            
            # Style attributes
            if 'formal' in name_lower:
                parts.append("Style: formal")
            if 'casual' in name_lower:
                parts.append("Style: casual")
            if 'sport' in name_lower:
                parts.append("Style: sport")
                
            # Special features
            if 'thread' in name_lower:
                parts.append("Feature: with thread")
            if 'sustainable' in name_lower or 'fsc' in name_lower:
                parts.append("Feature: sustainable")
            if 'premium' in name_lower:
                parts.append("Feature: premium")
                
        # Add stock status
        stock = row.get('stock', 0)
        if stock > 0:
            parts.append(f"Stock available: {stock} units")
            parts.append("In stock")
        else:
            parts.append("Out of stock")
            parts.append("No stock available")
            
        # Create a natural sentence as well for better semantic understanding
        if 'name' in row and pd.notna(row['name']) and 'code' in row and pd.notna(row['code']):
            natural_desc = f"This is a {brand} tag with code {row['code']} described as {row['name']}"
            parts.append(natural_desc)
            
        return " | ".join(parts)
    
    def _create_document_id(self, row: pd.Series, brand: str) -> str:
        """Create unique document ID for ChromaDB"""
        # Use code if available, otherwise use hash of content
        if 'code' in row and pd.notna(row['code']):
            return f"{brand}_{row['code']}".replace(' ', '_')
        else:
            content = f"{brand}_{row.get('name', '')}_{row.get('serial', '')}"
            return hashlib.md5(content.encode()).hexdigest()
    
    def ingest_excel_file(self, file_path: str, batch_size: int = 100) -> Dict[str, Any]:
        """Ingest a single Excel file into ChromaDB with Stella embeddings"""
        logger.info(f"Ingesting Excel file: {file_path}")
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Normalize columns
            df = self._normalize_column_names(df)
            
            # Extract brand from filename
            brand = self._extract_brand_from_filename(os.path.basename(file_path))
            
            # Prepare documents for ChromaDB
            documents = []
            metadatas = []
            ids = []
            
            for idx, row in df.iterrows():
                # Skip rows with no meaningful data
                if 'name' not in row or pd.isna(row.get('name')):
                    continue
                
                # Create searchable text optimized for Stella
                text = self._create_searchable_text(row, brand)
                
                # Create metadata
                metadata = {
                    'brand': brand,
                    'excel_source': os.path.basename(file_path),
                    'row_index': idx,
                    'stock': self._clean_stock_value(row.get('stock', 0))
                }
                
                # Add optional fields if they exist
                if 'code' in row and pd.notna(row['code']):
                    metadata['trim_code'] = str(row['code']).strip()
                if 'name' in row and pd.notna(row['name']):
                    metadata['trim_name'] = str(row['name']).strip()
                if 'image' in row and pd.notna(row['image']):
                    metadata['has_image'] = True
                    metadata['image_ref'] = str(row['image'])
                else:
                    metadata['has_image'] = False
                
                # Create document ID
                doc_id = self._create_document_id(row, brand)
                
                documents.append(text)
                metadatas.append(metadata)
                ids.append(doc_id)
            
            # Process in batches and add to ChromaDB
            if documents:
                total_added = 0
                for i in range(0, len(documents), batch_size):
                    batch_docs = documents[i:i+batch_size]
                    batch_metas = metadatas[i:i+batch_size]
                    batch_ids = ids[i:i+batch_size]
                    
                    # Generate embeddings using Stella
                    embeddings = self.embeddings_manager.encode_documents(batch_docs)
                    
                    # Add to ChromaDB with custom embeddings
                    self.chroma_client.collection.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids,
                        embeddings=embeddings.tolist()
                    )
                    
                    total_added += len(batch_docs)
                    logger.info(f"Added batch {i//batch_size + 1}, total: {total_added}/{len(documents)}")
                
                logger.info(f"Successfully ingested {len(documents)} items from {file_path}")
                
                return {
                    'status': 'success',
                    'file': file_path,
                    'items_ingested': len(documents),
                    'brand': brand,
                    'embedding_model': self.embeddings_manager.model_name
                }
            else:
                logger.warning(f"No valid items found in {file_path}")
                return {
                    'status': 'warning',
                    'file': file_path,
                    'items_ingested': 0,
                    'brand': brand,
                    'message': 'No valid items found'
                }
                
        except Exception as e:
            logger.error(f"Error ingesting {file_path}: {e}")
            return {
                'status': 'error',
                'file': file_path,
                'error': str(e)
            }
    
    def ingest_inventory_folder(self, folder_path: str) -> List[Dict[str, Any]]:
        """Ingest all Excel files from inventory folder"""
        results = []
        
        # Find all Excel files
        excel_extensions = ['.xlsx', '.xls']
        excel_files = []
        
        for file in os.listdir(folder_path):
            if any(file.lower().endswith(ext) for ext in excel_extensions):
                excel_files.append(os.path.join(folder_path, file))
        
        logger.info(f"Found {len(excel_files)} Excel files to ingest")
        
        # Ingest each file
        for file_path in excel_files:
            result = self.ingest_excel_file(file_path)
            results.append(result)
        
        # Summary
        total_items = sum(r.get('items_ingested', 0) for r in results if r['status'] == 'success')
        logger.info(f"Total items ingested: {total_items}")
        
        return results
    
    def search_inventory(self, query: str, 
                        brand_filter: Optional[str] = None,
                        min_stock: int = 0,
                        limit: int = 10) -> List[Dict[str, Any]]:
        """Search inventory using RAG with Stella embeddings"""
        
        # Generate query embedding using Stella's query mode
        query_embedding = self.embeddings_manager.encode_queries([query])[0]
        
        # Build filter
        where_filter = {}
        if brand_filter:
            where_filter['brand'] = brand_filter
        if min_stock > 0:
            where_filter['stock'] = {'$gte': min_stock}
        
        # Perform search with custom embedding
        results = self.chroma_client.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=limit,
            where=where_filter if where_filter else None,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format results
        formatted_results = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                result = {
                    'id': results['ids'][0][i],
                    'score': 1 - results['distances'][0][i],  # Convert distance to similarity
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i]
                }
                formatted_results.append(result)
        
        return formatted_results
    
    def find_similar_items(self, item_code: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find items similar to a given item code"""
        
        # First, get the item's embedding
        item_result = self.chroma_client.collection.get(
            ids=[item_code],
            include=['documents', 'embeddings']
        )
        
        if not item_result['ids']:
            return []
        
        # Use the item's embedding to find similar items
        item_embedding = item_result['embeddings'][0]
        
        results = self.chroma_client.collection.query(
            query_embeddings=[item_embedding],
            n_results=limit + 1,  # +1 because it will include itself
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format and exclude the original item
        formatted_results = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                if results['ids'][0][i] != item_code:
                    result = {
                        'id': results['ids'][0][i],
                        'score': 1 - results['distances'][0][i],
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i]
                    }
                    formatted_results.append(result)
        
        return formatted_results[:limit]


# Utility function to test the ingestion
def test_excel_ingestion():
    """Test the Excel ingestion with Stella embeddings"""
    ingestion = ExcelInventoryIngestion(embedding_model='stella-400m')
    
    # Test search functionality
    test_queries = [
        "Allen Solly black cotton casual tag",
        "Myntra sustainable tag with thread",
        "Peter England formal blue tag",
        "tags with available stock"
    ]
    
    print("Testing search with Stella-400M embeddings:\n")
    for query in test_queries:
        print(f"Query: {query}")
        results = ingestion.search_inventory(query, min_stock=1, limit=3)
        
        if results:
            for result in results:
                print(f"  - {result['metadata'].get('trim_name', 'N/A')} "
                      f"(Code: {result['metadata'].get('trim_code', 'N/A')}, "
                      f"Stock: {result['metadata'].get('stock', 0)}, "
                      f"Score: {result['score']:.3f})")
        else:
            print("  No results found")
        print()