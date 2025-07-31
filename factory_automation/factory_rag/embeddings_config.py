"""Embeddings configuration for RAG system"""

import logging
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingsManager:
    """Manages different embedding models for the RAG system"""

    # Model configurations
    MODELS = {
        "stella-400m": {
            "name": "dunzhang/stella_en_400M_v5",
            "dimensions": 1024,
            "max_length": 512,
            "trust_remote_code": True,
            "description": "Top performing, 400M params, best accuracy",
        },
        "e5-large-v2": {
            "name": "intfloat/e5-large-v2",
            "dimensions": 1024,
            "max_length": 512,
            "trust_remote_code": False,
            "description": "Balanced performance, 1.3B params",
        },
        "e5-base-v2": {
            "name": "intfloat/e5-base-v2",
            "dimensions": 768,
            "max_length": 512,
            "trust_remote_code": False,
            "description": "Smaller, faster, 109M params",
        },
        "bge-base-en-v1.5": {
            "name": "BAAI/bge-base-en-v1.5",
            "dimensions": 768,
            "max_length": 512,
            "trust_remote_code": False,
            "description": "Fast, efficient, good for real-time",
        },
        "all-MiniLM-L6-v2": {
            "name": "sentence-transformers/all-MiniLM-L6-v2",
            "dimensions": 384,
            "max_length": 256,
            "trust_remote_code": False,
            "description": "Fastest, smallest, 22M params",
        },
    }

    def __init__(self, model_name: str = "stella-400m", device: str = "cpu"):
        """Initialize embeddings manager

        Args:
            model_name: One of ['stella-400m', 'e5-large-v2', 'e5-base-v2', 'bge-base-en-v1.5', 'all-MiniLM-L6-v2']
            device: 'cpu' or 'cuda'
        """
        if model_name not in self.MODELS:
            raise ValueError(
                f"Model {model_name} not supported. Choose from {list(self.MODELS.keys())}"
            )

        self.model_name = model_name
        self.model_config = self.MODELS[model_name]
        self.device = device

        logger.info(f"Loading {model_name}: {self.model_config['description']}")

        # Special handling for Stella model on CPU
        if model_name == "stella-400m" and device == "cpu":
            self.model = SentenceTransformer(
                self.model_config["name"],
                trust_remote_code=self.model_config["trust_remote_code"],
                device=device,
                config_kwargs={
                    "use_memory_efficient_attention": False,
                    "unpad_inputs": False,
                },
            )
        else:
            self.model = SentenceTransformer(
                self.model_config["name"],
                trust_remote_code=self.model_config["trust_remote_code"],
                device=device,
            )

    def encode_queries(self, queries: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode queries with appropriate prompts"""

        # E5 models need query prefix
        if "e5" in self.model_name:
            queries = [f"query: {q}" for q in queries]

        # Stella model uses specific prompt
        elif self.model_name == "stella-400m":
            return self.model.encode(
                queries,
                prompt_name="s2p_query",
                batch_size=batch_size,
                normalize_embeddings=True,
            )

        # BGE models need instruction prefix for queries
        elif "bge" in self.model_name:
            queries = [
                f"Represent this sentence for searching relevant passages: {q}"
                for q in queries
            ]

        return self.model.encode(
            queries, batch_size=batch_size, normalize_embeddings=True
        )

    def encode_documents(
        self, documents: List[str], batch_size: int = 32
    ) -> np.ndarray:
        """Encode documents (inventory items)"""

        # E5 models need passage prefix
        if "e5" in self.model_name:
            documents = [f"passage: {d}" for d in documents]

        return self.model.encode(
            documents, batch_size=batch_size, normalize_embeddings=True
        )

    def get_dimensions(self) -> int:
        """Get embedding dimensions"""
        return self.model_config["dimensions"]

    def get_max_length(self) -> int:
        """Get maximum input length"""
        return self.model_config["max_length"]


# Example usage for inventory matching
def create_inventory_embeddings():
    """Example of creating embeddings for inventory items"""

    # Initialize with Stella for best accuracy
    embeddings = EmbeddingsManager("stella-400m", device="cpu")

    # Example inventory items
    inventory_items = [
        "ALLEN SOLLY MAIN TAG WORK CASUAL TBAMTAG4507 black cotton formal tag with gold print",
        "MYNTRA INVICTUS ESTILO SWING TAG BLACK GOLD FSC Sustainable premium tag",
        "PETER ENGLAND formal shirt tag blue polyester with thread PE2024",
    ]

    # Example queries
    queries = [
        "Allen Solly casual tag with gold",
        "sustainable black tag for Myntra",
        "Peter England blue tag",
    ]

    # Encode
    doc_embeddings = embeddings.encode_documents(inventory_items)
    query_embeddings = embeddings.encode_queries(queries)

    # Calculate similarities
    similarities = np.dot(query_embeddings, doc_embeddings.T)

    print("Similarity scores:")
    for i, query in enumerate(queries):
        print(f"\nQuery: {query}")
        for j, item in enumerate(inventory_items):
            print(f"  {item[:50]}... : {similarities[i][j]:.3f}")


# Benchmark different models
def benchmark_models():
    """Compare different embedding models for your use case"""

    test_items = [
        "ALLEN SOLLY MAIN TAG WORK CASUAL black cotton",
        "MYNTRA INVICTUS silk tag with thread",
        "PETER ENGLAND formal blue polyester tag",
    ]

    test_query = "Allen Solly black cotton casual tag"

    for model_name in ["all-MiniLM-L6-v2", "e5-base-v2", "stella-400m"]:
        print(f"\n{model_name}:")
        embeddings = EmbeddingsManager(model_name)

        import time

        start = time.time()
        doc_emb = embeddings.encode_documents(test_items)
        query_emb = embeddings.encode_queries([test_query])

        similarities = np.dot(query_emb, doc_emb.T)[0]
        elapsed = time.time() - start

        print(f"Time: {elapsed:.3f}s")
        print(f"Best match: {test_items[np.argmax(similarities)][:50]}...")
        print(f"Score: {np.max(similarities):.3f}")
