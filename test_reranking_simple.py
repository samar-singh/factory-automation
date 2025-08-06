#!/usr/bin/env python3
"""Simple test to verify reranking is working"""

import logging

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.enhanced_search import EnhancedRAGSearch

# Set up logging
logging.basicConfig(level=logging.INFO)


def test_reranking():
    """Test basic reranking functionality"""
    print("🚀 Testing Reranking Implementation\n")

    # Initialize ChromaDB
    print("1. Initializing ChromaDB...")
    chromadb_client = ChromaDBClient()

    # Initialize enhanced search
    print("2. Initializing Enhanced Search with Reranking...")
    enhanced_search = EnhancedRAGSearch(
        chromadb_client=chromadb_client,
        reranker_model="ms-marco-MiniLM",  # Use lightweight model for testing
        enable_reranking=True,
        enable_hybrid_search=True,
    )

    # Test query
    test_query = "Allen Solly black cotton tags for formal shirts"
    print(f"\n3. Testing search with query: '{test_query}'")

    # Perform search
    results, stats = enhanced_search.search(
        query=test_query, n_results=5, n_candidates=10
    )

    # Display results
    print("\n📊 Search Statistics:")
    print(f"   • Semantic candidates: {stats['semantic_candidates']}")
    print(f"   • BM25 candidates: {stats['bm25_candidates']}")
    print(f"   • After reranking: {stats['after_reranking']}")
    print(f"   • Final results: {stats['final_results']}")

    if "rerank_stats" in stats:
        print(f"   • Reranking time: {stats['rerank_stats']['time_ms']}ms")
        print(f"   • Reranker model: {stats['rerank_stats']['model']}")

    print("\n🎯 Top Results:")
    for i, result in enumerate(results[:5], 1):
        print(f"\n{i}. Item: {result['metadata'].get('trim_name', 'Unknown')}")
        print(f"   Code: {result['metadata'].get('trim_code', 'N/A')}")
        print(f"   Brand: {result['metadata'].get('brand', 'Unknown')}")
        print(f"   Stock: {result['metadata'].get('stock', 0)}")
        print(
            f"   Confidence: {result.get('confidence_percentage', 0)}% ({result.get('confidence_level', 'unknown')})"
        )

        if "rerank_score" in result:
            print(f"   Rerank Score: {result['rerank_score']:.3f}")
        if "source" in result:
            print(f"   Found by: {result['source']} search")

    # Test explanation
    if results:
        print("\n🔍 Explaining top match:")
        explanation = enhanced_search.explain_search_result(test_query, results[0])
        print(f"   Matching features: {', '.join(explanation['matching_features'])}")
        print(f"   Confidence factors: {', '.join(explanation['confidence_factors'])}")
        print(f"   Scores: {explanation['scores']}")

    print("\n✅ Reranking test completed successfully!")


if __name__ == "__main__":
    test_reranking()
