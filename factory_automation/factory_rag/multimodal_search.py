"""Multimodal search implementation with Qwen2.5VL and CLIP."""
import os
import base64
import logging
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

import numpy as np
import torch
import clip
from PIL import Image
from sentence_transformers import SentenceTransformer
import litellm
from chromadb import Collection

logger = logging.getLogger(__name__)

class MultimodalSearch:
    """Multimodal search using Qwen2.5VL for analysis and CLIP for embeddings."""
    
    def __init__(self, chroma_client):
        """Initialize multimodal search components."""
        self.chroma_client = chroma_client
        
        # Initialize text encoder
        logger.info("Loading text encoder...")
        self.text_encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize CLIP
        logger.info("Loading CLIP model...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.clip_model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        
        # Configure LiteLLM for Qwen2.5VL
        from factory_config.settings import settings
        litellm.api_key = settings.together_api_key
        
        logger.info("Multimodal search initialized")
    
    def encode_image_base64(self, image_path: Union[str, Path]) -> str:
        """Encode image to base64 string."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    async def analyze_image_with_qwen(self, image_path: Union[str, Path], 
                                    query: str = None) -> Dict[str, Any]:
        """Use Qwen2.5VL72B for detailed image analysis.
        
        Args:
            image_path: Path to the image
            query: Optional specific query about the image
            
        Returns:
            Dictionary with analysis results
        """
        if query is None:
            query = """Analyze this garment tag image and extract:
            1. Tag type/style
            2. Size information
            3. Material/fabric details
            4. Any visible text or codes
            5. Color and design elements
            6. Special features or characteristics"""
        
        try:
            # Encode image
            base64_image = self.encode_image_base64(image_path)
            
            # Call Qwen2.5VL via LiteLLM
            response = await litellm.acompletion(
                model="together_ai/Qwen/Qwen2.5-VL-72B-Instruct",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": query
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=500
            )
            
            analysis = response.choices[0].message.content
            
            return {
                "success": True,
                "analysis": analysis,
                "model": "Qwen2.5-VL-72B"
            }
            
        except Exception as e:
            logger.error(f"Error in Qwen2.5VL analysis: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "analysis": None
            }
    
    def encode_image_clip(self, image_path: Union[str, Path]) -> np.ndarray:
        """Generate CLIP embeddings for an image."""
        image = Image.open(image_path).convert("RGB")
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            image_features = self.clip_model.encode_image(image_tensor)
            image_features = image_features.cpu().numpy().flatten()
            # Normalize
            image_features = image_features / np.linalg.norm(image_features)
            
        return image_features
    
    def encode_text_clip(self, text: str) -> np.ndarray:
        """Generate CLIP embeddings for text."""
        text_tokens = clip.tokenize([text], truncate=True).to(self.device)
        
        with torch.no_grad():
            text_features = self.clip_model.encode_text(text_tokens)
            text_features = text_features.cpu().numpy().flatten()
            # Normalize
            text_features = text_features / np.linalg.norm(text_features)
            
        return text_features
    
    async def search(self, 
                    image_path: Optional[Union[str, Path]] = None,
                    text_query: Optional[str] = None,
                    collection_name: str = "tag_inventory",
                    k: int = 10) -> Dict[str, Any]:
        """Perform multimodal search using both Qwen analysis and CLIP embeddings.
        
        Args:
            image_path: Optional path to query image
            text_query: Optional text query
            collection_name: ChromaDB collection to search
            k: Number of results to return
            
        Returns:
            Search results with matches and analysis
        """
        embeddings = []
        qwen_analysis = None
        
        # Process text query
        if text_query:
            text_emb = self.text_encoder.encode(text_query)
            embeddings.append(text_emb)
            logger.info(f"Encoded text query: {text_query[:50]}...")
        
        # Process image if provided
        if image_path:
            # Get detailed analysis from Qwen2.5VL
            qwen_result = await self.analyze_image_with_qwen(image_path)
            if qwen_result["success"]:
                qwen_analysis = qwen_result["analysis"]
                
                # Add Qwen analysis to text embeddings
                analysis_emb = self.text_encoder.encode(qwen_analysis)
                embeddings.append(analysis_emb)
                logger.info("Added Qwen2.5VL analysis to search")
            
            # Generate CLIP image embeddings
            clip_image_emb = self.encode_image_clip(image_path)
            embeddings.append(clip_image_emb)
            logger.info("Generated CLIP image embeddings")
        
        # Combine all embeddings
        if len(embeddings) == 0:
            raise ValueError("Must provide either image or text query")
        elif len(embeddings) == 1:
            combined_embedding = embeddings[0]
        else:
            # Concatenate and normalize
            combined_embedding = np.concatenate(embeddings)
            combined_embedding = combined_embedding / np.linalg.norm(combined_embedding)
        
        # Search ChromaDB
        try:
            collection = self.chroma_client.get_collection(collection_name)
            results = collection.query(
                query_embeddings=[combined_embedding.tolist()],
                n_results=k,
                include=["metadatas", "distances", "documents"]
            )
            
            # Format results
            matches = []
            for i in range(len(results['ids'][0])):
                match = {
                    "id": results['ids'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i],
                    "similarity_score": 1 - results['distances'][0][i],  # Convert distance to similarity
                }
                if 'documents' in results:
                    match["document"] = results['documents'][0][i]
                matches.append(match)
            
            return {
                "success": True,
                "matches": matches,
                "qwen_analysis": qwen_analysis,
                "query_info": {
                    "had_image": image_path is not None,
                    "had_text": text_query is not None,
                    "embedding_dim": len(combined_embedding)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in ChromaDB search: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "matches": [],
                "qwen_analysis": qwen_analysis
            }
    
    async def add_to_inventory(self,
                             image_path: Union[str, Path],
                             metadata: Dict[str, Any],
                             collection_name: str = "tag_inventory") -> Dict[str, Any]:
        """Add a new tag to inventory with multimodal embeddings.
        
        Args:
            image_path: Path to tag image
            metadata: Tag metadata (code, size, etc.)
            collection_name: Collection to add to
            
        Returns:
            Result of the operation
        """
        try:
            # Analyze image with Qwen
            qwen_result = await self.analyze_image_with_qwen(image_path)
            
            # Generate embeddings
            embeddings = []
            
            # Text embedding from metadata
            text_desc = f"{metadata.get('tag_code', '')} {metadata.get('description', '')} {metadata.get('size', '')}"
            text_emb = self.text_encoder.encode(text_desc)
            embeddings.append(text_emb)
            
            # Add Qwen analysis embedding if available
            if qwen_result["success"]:
                analysis_emb = self.text_encoder.encode(qwen_result["analysis"])
                embeddings.append(analysis_emb)
                metadata["qwen_analysis"] = qwen_result["analysis"]
            
            # CLIP image embedding
            clip_emb = self.encode_image_clip(image_path)
            embeddings.append(clip_emb)
            
            # Combine embeddings
            combined_embedding = np.concatenate(embeddings)
            combined_embedding = combined_embedding / np.linalg.norm(combined_embedding)
            
            # Add to ChromaDB
            collection = self.chroma_client.get_collection(collection_name)
            collection.add(
                embeddings=[combined_embedding.tolist()],
                metadatas=[metadata],
                ids=[metadata.get("tag_code", str(Path(image_path).stem))]
            )
            
            logger.info(f"Added tag to inventory: {metadata.get('tag_code')}")
            
            return {
                "success": True,
                "tag_code": metadata.get("tag_code"),
                "qwen_analysis": qwen_result.get("analysis")
            }
            
        except Exception as e:
            logger.error(f"Error adding to inventory: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }