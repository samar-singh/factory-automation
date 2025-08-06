"""Enhanced RAG search with reranking and hybrid search capabilities"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from rank_bm25 import BM25Okapi

from ..factory_database.vector_db import ChromaDBClient
from .embeddings_config import EmbeddingsManager
from .reranker import CrossEncoderReranker, HybridReranker

logger = logging.getLogger(__name__)


class EnhancedRAGSearch:
    """Enhanced search with reranking, hybrid search, and better relevance scoring"""

    def __init__(
        self,
        chromadb_client: ChromaDBClient,
        embeddings_manager: Optional[EmbeddingsManager] = None,
        reranker_model: str = "bge-reranker-base",
        enable_reranking: bool = True,
        enable_hybrid_search: bool = True,
    ):
        """Initialize enhanced search

        Args:
            chromadb_client: ChromaDB client instance
            embeddings_manager: Embeddings manager (creates default if None)
            reranker_model: Which reranker model to use
            enable_reranking: Whether to use reranking
            enable_hybrid_search: Whether to use BM25 + semantic search
        """
        self.chromadb_client = chromadb_client
        self.embeddings_manager = embeddings_manager or EmbeddingsManager("stella-400m")
        self.enable_reranking = enable_reranking
        self.enable_hybrid_search = enable_hybrid_search

        # Initialize reranker if enabled
        if enable_reranking:
            logger.info(f"Initializing reranker with {reranker_model}")
            self.reranker = CrossEncoderReranker(reranker_model)
            self.hybrid_reranker = HybridReranker(self.reranker)
        else:
            self.reranker = None
            self.hybrid_reranker = None

        # Initialize BM25 if hybrid search is enabled
        self.bm25 = None
        self.bm25_corpus = None
        self.bm25_ids = None
        if enable_hybrid_search:
            self._initialize_bm25()

    def _initialize_bm25(self):
        """Initialize BM25 index from ChromaDB collection"""
        try:
            # Get all documents from ChromaDB
            results = self.chromadb_client.collection.get(include=["documents", "metadatas"])

            if results and results["documents"]:
                # Tokenize documents for BM25
                corpus = []
                self.bm25_ids = results["ids"]

                for i, doc in enumerate(results["documents"]):
                    # Combine document with metadata for better keyword matching
                    metadata = results["metadatas"][i] if results["metadatas"] else {}
                    text_parts = [doc]

                    # Add searchable metadata fields
                    if metadata.get("trim_code"):
                        text_parts.append(metadata["trim_code"])
                    if metadata.get("trim_name"):
                        text_parts.append(metadata["trim_name"])
                    if metadata.get("brand"):
                        text_parts.append(metadata["brand"])

                    # Simple tokenization
                    combined_text = " ".join(text_parts).lower()
                    tokens = combined_text.split()
                    corpus.append(tokens)

                self.bm25_corpus = corpus
                self.bm25 = BM25Okapi(corpus)
                logger.info(f"Initialized BM25 index with {len(corpus)} documents")
            else:
                logger.warning("No documents found for BM25 initialization")

        except Exception as e:
            logger.error(f"Error initializing BM25: {e}")
            self.enable_hybrid_search = False

    def search(
        self,
        query: str,
        n_results: int = 10,
        n_candidates: int = 30,
        rerank_top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Enhanced search with optional reranking and hybrid search

        Args:
            query: Search query
            n_results: Final number of results to return
            n_candidates: Number of candidates to retrieve before reranking
            rerank_top_k: Number of results after reranking (defaults to n_results)
            filters: Metadata filters for ChromaDB
            score_threshold: Minimum score threshold

        Returns:
            Tuple of (results, search_stats)
        """
        search_stats = {
            "query": query,
            "semantic_candidates": 0,
            "bm25_candidates": 0,
            "after_reranking": 0,
            "final_results": 0,
        }

        # Set defaults
        if rerank_top_k is None:
            rerank_top_k = n_results

        # Get more candidates if reranking is enabled
        semantic_n = n_candidates if self.enable_reranking else n_results

        # 1. Semantic search using ChromaDB
        semantic_results = self._semantic_search(query, semantic_n, filters)
        search_stats["semantic_candidates"] = len(semantic_results)

        # 2. BM25 search if enabled
        bm25_results = []
        if self.enable_hybrid_search and self.bm25:
            bm25_results = self._bm25_search(query, semantic_n)
            search_stats["bm25_candidates"] = len(bm25_results)

        # 3. Merge results
        merged_results = self._merge_results(
            semantic_results, bm25_results, semantic_weight=0.7, bm25_weight=0.3
        )

        # 4. Rerank if enabled
        if self.enable_reranking and self.reranker and len(merged_results) > 0:
            final_results, rerank_stats = self.reranker.rerank_search_results(
                query, merged_results, top_k=rerank_top_k, score_threshold=score_threshold
            )
            search_stats["after_reranking"] = len(final_results)
            search_stats["rerank_stats"] = rerank_stats
        else:
            final_results = merged_results[:n_results]

        # 5. Apply final score threshold if not done in reranking
        if score_threshold and not self.enable_reranking:
            final_results = [
                r for r in final_results
                if r.get("score", 0) >= score_threshold
                or r.get("rerank_score", 0) >= score_threshold
            ]

        search_stats["final_results"] = len(final_results)

        # 6. Enhance results with confidence levels
        final_results = self._add_confidence_levels(final_results)

        return final_results, search_stats

    def _semantic_search(
        self, query: str, n_results: int, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using ChromaDB"""
        # Encode query
        query_embedding = self.embeddings_manager.encode_queries([query])[0]

        # Search ChromaDB
        results = self.chromadb_client.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=filters,
            include=["metadatas", "distances", "documents"],
        )

        # Format results
        formatted_results = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            for i in range(len(results["ids"][0])):
                result = {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i],
                    "score": 1 - results["distances"][0][i],  # Convert distance to similarity
                    "source": "semantic",
                }
                formatted_results.append(result)

        return formatted_results

    def _bm25_search(self, query: str, n_results: int) -> List[Dict[str, Any]]:
        """Perform BM25 keyword search"""
        if not self.bm25 or not self.bm25_corpus:
            return []

        # Tokenize query
        query_tokens = query.lower().split()

        # Get BM25 scores
        scores = self.bm25.get_scores(query_tokens)

        # Get top results
        top_indices = np.argsort(scores)[::-1][:n_results]

        # Format results
        bm25_results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include results with positive scores
                # Fetch full document from ChromaDB
                doc_id = self.bm25_ids[idx]
                chrome_result = self.chromadb_client.collection.get(
                    ids=[doc_id], include=["documents", "metadatas"]
                )

                if chrome_result and chrome_result["documents"]:
                    result = {
                        "id": doc_id,
                        "text": chrome_result["documents"][0],
                        "metadata": (
                            chrome_result["metadatas"][0]
                            if chrome_result["metadatas"]
                            else {}
                        ),
                        "score": float(scores[idx]) / 10,  # Normalize BM25 scores
                        "source": "bm25",
                    }
                    bm25_results.append(result)

        return bm25_results

    def _merge_results(
        self,
        semantic_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        semantic_weight: float = 0.7,
        bm25_weight: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Merge semantic and BM25 results with weighted scoring"""
        # Create a dictionary to track merged results
        merged_dict = {}

        # Add semantic results
        for result in semantic_results:
            doc_id = result["id"]
            merged_dict[doc_id] = result.copy()
            merged_dict[doc_id]["semantic_score"] = result["score"]
            merged_dict[doc_id]["final_score"] = semantic_weight * result["score"]

        # Add/update with BM25 results
        for result in bm25_results:
            doc_id = result["id"]
            if doc_id in merged_dict:
                # Document appears in both - combine scores
                merged_dict[doc_id]["bm25_score"] = result["score"]
                merged_dict[doc_id]["final_score"] = (
                    semantic_weight * merged_dict[doc_id].get("semantic_score", 0)
                    + bm25_weight * result["score"]
                )
                merged_dict[doc_id]["source"] = "hybrid"
            else:
                # Only in BM25
                merged_dict[doc_id] = result.copy()
                merged_dict[doc_id]["bm25_score"] = result["score"]
                merged_dict[doc_id]["final_score"] = bm25_weight * result["score"]

        # Convert back to list and sort by final score
        merged_results = list(merged_dict.values())
        merged_results.sort(key=lambda x: x.get("final_score", 0), reverse=True)

        # Update score field to final_score
        for result in merged_results:
            result["score"] = result["final_score"]

        return merged_results

    def _add_confidence_levels(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add confidence levels to results based on scores"""
        for result in results:
            # Use rerank score if available, otherwise use regular score
            score = result.get("rerank_score", result.get("score", 0))

            if score >= 0.9:
                confidence = "very_high"
                confidence_pct = 95
            elif score >= 0.8:
                confidence = "high"
                confidence_pct = 85
            elif score >= 0.7:
                confidence = "medium"
                confidence_pct = 70
            elif score >= 0.6:
                confidence = "low"
                confidence_pct = 60
            else:
                confidence = "very_low"
                confidence_pct = 40

            result["confidence_level"] = confidence
            result["confidence_percentage"] = confidence_pct

        return results

    def explain_search_result(
        self, query: str, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Explain why a result was returned for a query"""
        explanation = {
            "query": query,
            "result_id": result.get("id"),
            "result_text": result.get("text", "")[:200] + "...",
            "scores": {},
            "matching_features": [],
            "confidence_factors": [],
        }

        # Add all available scores
        if "semantic_score" in result:
            explanation["scores"]["semantic"] = result["semantic_score"]
            explanation["matching_features"].append("Semantic similarity")

        if "bm25_score" in result:
            explanation["scores"]["bm25"] = result["bm25_score"]
            explanation["matching_features"].append("Keyword match")

        if "rerank_score" in result:
            explanation["scores"]["rerank"] = result["rerank_score"]
            explanation["matching_features"].append("Cross-encoder relevance")

        # Analyze matching keywords
        query_terms = set(query.lower().split())
        metadata = result.get("metadata", {})

        # Check metadata matches
        for key, value in metadata.items():
            if isinstance(value, str):
                value_terms = set(value.lower().split())
                matching_terms = query_terms & value_terms
                if matching_terms:
                    explanation["matching_features"].append(
                        f"{key}: {', '.join(matching_terms)}"
                    )

        # Add confidence factors
        if result.get("confidence_percentage", 0) >= 80:
            explanation["confidence_factors"].append("High relevance score")
        if result.get("source") == "hybrid":
            explanation["confidence_factors"].append("Found by multiple search methods")
        if "rerank_score" in result:
            explanation["confidence_factors"].append("Verified by reranker model")

        return explanation