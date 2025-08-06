"""Cross-encoder reranker for improving RAG retrieval accuracy"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Reranks search results using cross-encoder models for better accuracy"""

    # Available reranking models with their characteristics
    RERANKER_MODELS = {
        "bge-reranker-v2-m3": {
            "name": "BAAI/bge-reranker-v2-m3",
            "max_length": 512,
            "description": "Multilingual, best overall performance",
            "size": "568M",
        },
        "bge-reranker-base": {
            "name": "BAAI/bge-reranker-base",
            "max_length": 512,
            "description": "English only, good balance",
            "size": "278M",
        },
        "ms-marco-MiniLM": {
            "name": "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "max_length": 512,
            "description": "Fast, lightweight, good for real-time",
            "size": "80M",
        },
        "mxbai-rerank-base": {
            "name": "mixedbread-ai/mxbai-rerank-base-v1",
            "max_length": 512,
            "description": "Latest model with RL training",
            "size": "278M",
        },
    }

    def __init__(
        self,
        model_name: str = "bge-reranker-base",
        device: Optional[str] = None,
        batch_size: int = 32,
    ):
        """Initialize the cross-encoder reranker

        Args:
            model_name: One of the supported reranker models
            device: 'cuda' or 'cpu' (auto-detected if None)
            batch_size: Batch size for reranking
        """
        if model_name not in self.RERANKER_MODELS:
            raise ValueError(
                f"Model {model_name} not supported. Choose from {list(self.RERANKER_MODELS.keys())}"
            )

        self.model_name = model_name
        self.model_config = self.RERANKER_MODELS[model_name]
        self.batch_size = batch_size

        # Auto-detect device if not specified
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(
            f"Loading reranker {model_name} ({self.model_config['description']}) on {self.device}"
        )

        # Load the cross-encoder model
        self.model = CrossEncoder(
            self.model_config["name"],
            max_length=self.model_config["max_length"],
            device=self.device,
        )

        logger.info(f"Reranker loaded successfully: {self.model_config['size']} model")

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
        return_scores: bool = True,
    ) -> List[Dict[str, Any]]:
        """Rerank documents based on relevance to query

        Args:
            query: The search query
            documents: List of documents with 'text' field (and optional metadata)
            top_k: Return only top K results (None returns all)
            return_scores: Whether to include reranking scores

        Returns:
            Reranked list of documents with scores
        """
        if not documents:
            return []

        start_time = time.time()

        # Extract texts for reranking
        texts = []
        for doc in documents:
            # Handle different document formats
            if isinstance(doc, dict):
                text = doc.get("text", doc.get("content", str(doc)))
            else:
                text = str(doc)
            texts.append(text)

        # Create query-document pairs
        query_doc_pairs = [[query, text] for text in texts]

        # Get reranking scores
        logger.debug(f"Reranking {len(documents)} documents")
        scores = self.model.predict(query_doc_pairs, batch_size=self.batch_size)

        # Combine scores with documents
        scored_docs = []
        for i, (doc, score) in enumerate(zip(documents, scores)):
            result = doc.copy() if isinstance(doc, dict) else {"text": doc}
            if return_scores:
                result["rerank_score"] = float(score)
                # Preserve original score if exists
                if "score" in result:
                    result["original_score"] = result["score"]
            scored_docs.append(result)

        # Sort by reranking score (descending)
        scored_docs.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

        # Limit to top_k if specified
        if top_k is not None and top_k < len(scored_docs):
            scored_docs = scored_docs[:top_k]

        elapsed_time = time.time() - start_time
        logger.info(
            f"Reranked {len(documents)} documents in {elapsed_time:.3f}s, returning top {len(scored_docs)}"
        )

        return scored_docs

    def rerank_search_results(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Rerank ChromaDB search results

        Args:
            query: Original search query
            search_results: Results from ChromaDB search
            top_k: Number of results to return
            score_threshold: Minimum reranking score threshold

        Returns:
            Tuple of (reranked_results, reranking_stats)
        """
        if not search_results:
            return [], {"total_results": 0, "reranked": 0, "time_ms": 0}

        start_time = time.time()

        # Prepare documents for reranking
        documents = []
        for result in search_results:
            # Combine relevant fields for reranking
            text_parts = []

            # Add main text
            if "text" in result:
                text_parts.append(result["text"])

            # Add metadata fields that might be relevant
            metadata = result.get("metadata", {})
            if metadata.get("trim_name"):
                text_parts.append(f"Name: {metadata['trim_name']}")
            if metadata.get("brand"):
                text_parts.append(f"Brand: {metadata['brand']}")
            if metadata.get("trim_code"):
                text_parts.append(f"Code: {metadata['trim_code']}")

            doc = {
                "text": " ".join(text_parts),
                "original_result": result,
            }
            documents.append(doc)

        # Rerank
        reranked = self.rerank(query, documents, top_k=None, return_scores=True)

        # Apply score threshold if specified
        if score_threshold is not None:
            reranked = [
                doc for doc in reranked if doc.get("rerank_score", 0) >= score_threshold
            ]

        # Limit to top_k
        reranked = reranked[:top_k]

        # Extract original results with reranking scores
        final_results = []
        for doc in reranked:
            result = doc["original_result"].copy()
            result["rerank_score"] = doc["rerank_score"]
            final_results.append(result)

        # Calculate statistics
        elapsed_ms = int((time.time() - start_time) * 1000)
        stats = {
            "total_results": len(search_results),
            "reranked": len(final_results),
            "time_ms": elapsed_ms,
            "avg_rerank_score": (
                np.mean([r["rerank_score"] for r in final_results])
                if final_results
                else 0
            ),
            "model": self.model_name,
        }

        return final_results, stats


class HybridReranker:
    """Combines initial retrieval scores with reranking scores"""

    def __init__(
        self,
        reranker: CrossEncoderReranker,
        initial_weight: float = 0.3,
        rerank_weight: float = 0.7,
    ):
        """Initialize hybrid reranker

        Args:
            reranker: CrossEncoderReranker instance
            initial_weight: Weight for initial retrieval score
            rerank_weight: Weight for reranking score
        """
        self.reranker = reranker
        self.initial_weight = initial_weight
        self.rerank_weight = rerank_weight

        if abs(initial_weight + rerank_weight - 1.0) > 0.001:
            raise ValueError("Weights must sum to 1.0")

    def rerank_with_hybrid_scoring(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Rerank using hybrid scoring

        Args:
            query: Search query
            search_results: Initial search results with scores
            top_k: Number of results to return

        Returns:
            Reranked results with hybrid scores
        """
        # First, normalize initial scores to 0-1 range
        initial_scores = [r.get("score", 0) for r in search_results]
        if initial_scores:
            max_score = max(initial_scores)
            min_score = min(initial_scores)
            score_range = max_score - min_score if max_score != min_score else 1.0

            for r in search_results:
                r["normalized_score"] = (
                    (r.get("score", 0) - min_score) / score_range
                    if score_range > 0
                    else 0.5
                )

        # Get reranking scores
        reranked = self.reranker.rerank(query, search_results, return_scores=True)

        # Calculate hybrid scores
        for doc in reranked:
            initial = doc.get("normalized_score", 0)
            rerank = doc.get("rerank_score", 0)

            # Normalize rerank score (cross-encoder outputs can be any range)
            # Using sigmoid to map to 0-1
            normalized_rerank = 1 / (1 + np.exp(-rerank))

            doc["hybrid_score"] = (
                self.initial_weight * initial + self.rerank_weight * normalized_rerank
            )

        # Sort by hybrid score
        reranked.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)

        return reranked[:top_k]


# Integration function for the existing system
def create_reranker_tool(model_name: str = "bge-reranker-base"):
    """Create a reranker tool for the orchestrator"""
    reranker = CrossEncoderReranker(model_name)

    def rerank_inventory_results(
        query: str, search_results: List[Dict[str, Any]], top_k: int = 5
    ) -> Dict[str, Any]:
        """Rerank inventory search results"""
        reranked_results, stats = reranker.rerank_search_results(
            query, search_results, top_k
        )

        return {
            "query": query,
            "reranked_results": reranked_results,
            "statistics": stats,
            "improved_accuracy": len(reranked_results) > 0
            and reranked_results[0].get("rerank_score", 0) > 0.8,
        }

    return rerank_inventory_results