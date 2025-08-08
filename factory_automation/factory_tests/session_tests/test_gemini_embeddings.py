#!/usr/bin/env python3
"""Test Google Gemini embeddings integration"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project to path
sys.path.append(".")

from factory_automation.factory_rag.embeddings_config import EmbeddingsManager
import numpy as np


def test_gemini_embeddings():
    """Test Gemini embeddings functionality"""
    
    print("🚀 Testing Google Gemini Embeddings\n")
    
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        print("❌ Please set GOOGLE_API_KEY or GEMINI_API_KEY in .env file")
        print("   Get your API key from: https://makersuite.google.com/app/apikey")
        return
    
    try:
        # Initialize Gemini embeddings
        print("1. Initializing Gemini embeddings...")
        embeddings = EmbeddingsManager("gemini")
        print(f"   ✅ Model: {embeddings.model_config['name']}")
        print(f"   ✅ Dimensions: {embeddings.get_dimensions()}")
        print(f"   ✅ Max length: {embeddings.get_max_length()}")
        
        # Test documents
        print("\n2. Testing document encoding...")
        test_docs = [
            "ALLEN SOLLY MAIN TAG WORK CASUAL TBAMTAG4507 black cotton formal tag with gold print",
            "MYNTRA INVICTUS ESTILO SWING TAG BLACK GOLD FSC Sustainable premium tag", 
            "PETER ENGLAND formal shirt tag blue polyester with thread PE2024",
        ]
        
        doc_embeddings = embeddings.encode_documents(test_docs)
        print(f"   ✅ Document embeddings shape: {doc_embeddings.shape}")
        print(f"   ✅ First embedding sample: {doc_embeddings[0][:5]}...")
        
        # Test queries
        print("\n3. Testing query encoding...")
        test_queries = [
            "Allen Solly black cotton tag with gold",
            "sustainable black tag for Myntra",
            "Peter England blue formal tag",
        ]
        
        query_embeddings = embeddings.encode_queries(test_queries)
        print(f"   ✅ Query embeddings shape: {query_embeddings.shape}")
        
        # Calculate similarities
        print("\n4. Testing similarity matching...")
        similarities = np.dot(query_embeddings, doc_embeddings.T)
        
        for i, query in enumerate(test_queries):
            print(f"\n   Query: '{query}'")
            for j, doc in enumerate(test_docs):
                score = similarities[i][j]
                print(f"      {doc[:50]}... : {score:.3f}")
            best_match_idx = np.argmax(similarities[i])
            print(f"   ✅ Best match: Item {best_match_idx + 1}")
        
        print("\n✅ Gemini embeddings test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error testing Gemini embeddings: {e}")
        import traceback
        traceback.print_exc()


def compare_with_stella():
    """Compare Gemini with Stella embeddings"""
    
    print("\n" + "="*60)
    print("📊 Comparing Gemini vs Stella Embeddings")
    print("="*60)
    
    test_items = [
        "ALLEN SOLLY black cotton main tag with gold printing TBAMTAG4507",
        "MYNTRA sustainable FSC certified tag black with gold thread",
        "PETER ENGLAND blue polyester formal shirt tag PE2024",
    ]
    
    test_query = "Allen Solly black cotton tag gold print"
    
    results = {}
    
    for model_name in ["gemini", "stella-400m"]:
        try:
            print(f"\n🔍 Testing {model_name}...")
            embeddings = EmbeddingsManager(model_name)
            
            import time
            start = time.time()
            
            doc_emb = embeddings.encode_documents(test_items)
            query_emb = embeddings.encode_queries([test_query])
            
            similarities = np.dot(query_emb, doc_emb.T)[0]
            elapsed = time.time() - start
            
            results[model_name] = {
                "time": elapsed,
                "scores": similarities,
                "best_idx": np.argmax(similarities),
                "best_score": np.max(similarities),
                "dimensions": embeddings.get_dimensions()
            }
            
            print(f"   Time: {elapsed:.3f}s")
            print(f"   Dimensions: {results[model_name]['dimensions']}")
            print(f"   Best match: Item {results[model_name]['best_idx'] + 1}")
            print(f"   Best score: {results[model_name]['best_score']:.3f}")
            
        except Exception as e:
            print(f"   ❌ Error with {model_name}: {e}")
    
    # Summary
    if len(results) == 2:
        print("\n" + "="*60)
        print("📈 Summary Comparison")
        print("="*60)
        
        gemini = results.get("gemini", {})
        stella = results.get("stella-400m", {})
        
        print("\nSpeed:")
        print(f"  Gemini: {gemini.get('time', 0):.3f}s")
        print(f"  Stella: {stella.get('time', 0):.3f}s")
        
        print("\nDimensions:")
        print(f"  Gemini: {gemini.get('dimensions', 0)}")
        print(f"  Stella: {stella.get('dimensions', 0)}")
        
        print("\nBest Score:")
        print(f"  Gemini: {gemini.get('best_score', 0):.3f}")
        print(f"  Stella: {stella.get('best_score', 0):.3f}")
        
        print("\nAccuracy (same best match):")
        if gemini.get('best_idx') == stella.get('best_idx'):
            print("  ✅ Both models selected the same best match!")
        else:
            print(f"  ⚠️ Different matches - Gemini: Item {gemini.get('best_idx', 0) + 1}, Stella: Item {stella.get('best_idx', 0) + 1}")


if __name__ == "__main__":
    # Test Gemini alone
    test_gemini_embeddings()
    
    # Compare with Stella
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        compare_with_stella()