"""
Deduplication Manager for RAG Database
Handles detection, prevention, and removal of duplicates in ChromaDB
"""

import hashlib
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..factory_database.vector_db import ChromaDBClient

logger = logging.getLogger(__name__)


class DeduplicationManager:
    """
    Manages deduplication in ChromaDB collections
    Strategies:
    1. Exact duplicates: Same content/metadata
    2. Near duplicates: High similarity embeddings
    3. Semantic duplicates: Different text but same meaning
    4. Preventive: Check before insertion
    """

    def __init__(self, chromadb_client: Optional[ChromaDBClient] = None):
        """Initialize deduplication manager"""
        self.chromadb_client = chromadb_client or ChromaDBClient()
        self.similarity_threshold = 0.95  # For near-duplicate detection

    def generate_content_hash(
        self, metadata: Dict[str, Any], document: str = ""
    ) -> str:
        """
        Generate a unique hash for content to detect exact duplicates

        Args:
            metadata: Item metadata
            document: Document text

        Returns:
            MD5 hash of content
        """
        # Create a canonical representation
        key_fields = [
            metadata.get("item_code", ""),
            metadata.get("item_name", ""),
            metadata.get("brand", ""),
            metadata.get("source_file", ""),
            str(metadata.get("row_index", "")),
            document[:500] if document else "",  # First 500 chars of document
        ]

        content = "|".join(str(f) for f in key_fields)
        return hashlib.md5(content.encode()).hexdigest()

    def find_duplicates_in_collection(
        self, collection_name: str, strategy: str = "exact"
    ) -> Dict[str, List[str]]:
        """
        Find duplicates in a collection

        Args:
            collection_name: Name of collection to check
            strategy: 'exact', 'near', or 'semantic'

        Returns:
            Dictionary mapping duplicate groups
        """
        try:
            collection = self.chromadb_client.client.get_collection(collection_name)
            all_items = collection.get(include=["metadatas", "documents", "embeddings"])

            duplicates = defaultdict(list)

            if strategy == "exact":
                # Find exact duplicates based on content hash
                hash_to_ids = defaultdict(list)

                for i, (id_, metadata, doc) in enumerate(
                    zip(
                        all_items["ids"], all_items["metadatas"], all_items["documents"]
                    )
                ):
                    content_hash = self.generate_content_hash(metadata, doc)
                    hash_to_ids[content_hash].append(id_)

                # Filter to only show actual duplicates
                for hash_val, ids in hash_to_ids.items():
                    if len(ids) > 1:
                        duplicates[hash_val] = ids

            elif strategy == "near":
                # Find near duplicates based on embedding similarity
                if all_items["embeddings"]:
                    embeddings = np.array(all_items["embeddings"])
                    n_items = len(embeddings)

                    # Calculate pairwise similarities
                    processed = set()

                    for i in range(n_items):
                        if i in processed:
                            continue

                        similar_group = [all_items["ids"][i]]
                        processed.add(i)

                        for j in range(i + 1, n_items):
                            if j in processed:
                                continue

                            # Calculate cosine similarity
                            similarity = np.dot(embeddings[i], embeddings[j]) / (
                                np.linalg.norm(embeddings[i])
                                * np.linalg.norm(embeddings[j])
                            )

                            if similarity >= self.similarity_threshold:
                                similar_group.append(all_items["ids"][j])
                                processed.add(j)

                        if len(similar_group) > 1:
                            group_key = f"near_group_{i}"
                            duplicates[group_key] = similar_group

            elif strategy == "semantic":
                # Find semantic duplicates (same item, different descriptions)
                item_groups = defaultdict(list)

                for i, (id_, metadata) in enumerate(
                    zip(all_items["ids"], all_items["metadatas"])
                ):
                    # Group by item code and brand
                    item_key = f"{metadata.get('brand', 'unknown')}_{metadata.get('item_code', 'unknown')}"
                    if item_key != "unknown_unknown":
                        item_groups[item_key].append(id_)

                # Filter to only show duplicates
                for item_key, ids in item_groups.items():
                    if len(ids) > 1:
                        duplicates[item_key] = ids

            return dict(duplicates)

        except Exception as e:
            logger.error(f"Error finding duplicates: {e}")
            return {}

    def remove_duplicates(
        self,
        collection_name: str,
        strategy: str = "exact",
        keep: str = "first",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Remove duplicates from collection

        Args:
            collection_name: Collection to deduplicate
            strategy: 'exact', 'near', or 'semantic'
            keep: 'first', 'last', or 'best' (based on metadata completeness)
            dry_run: If True, only report what would be deleted

        Returns:
            Deduplication results
        """
        duplicates = self.find_duplicates_in_collection(collection_name, strategy)

        if not duplicates:
            return {"status": "success", "message": "No duplicates found", "removed": 0}

        try:
            collection = self.chromadb_client.client.get_collection(collection_name)
            all_items = collection.get(include=["metadatas"])

            # Create ID to metadata mapping
            id_to_metadata = dict(zip(all_items["ids"], all_items["metadatas"]))

            ids_to_remove = []

            for group_key, duplicate_ids in duplicates.items():
                if keep == "first":
                    # Keep the first, remove the rest
                    ids_to_remove.extend(duplicate_ids[1:])

                elif keep == "last":
                    # Keep the last, remove the rest
                    ids_to_remove.extend(duplicate_ids[:-1])

                elif keep == "best":
                    # Keep the one with most complete metadata
                    best_id = None
                    best_score = -1

                    for id_ in duplicate_ids:
                        metadata = id_to_metadata.get(id_, {})
                        # Score based on metadata completeness
                        score = sum(
                            [
                                (
                                    1
                                    if metadata.get("item_code")
                                    and metadata.get("item_code") != "NILL"
                                    else 0
                                ),
                                (
                                    1
                                    if metadata.get("item_name")
                                    and metadata.get("item_name") != "NILL"
                                    else 0
                                ),
                                1 if metadata.get("brand") else 0,
                                1 if metadata.get("has_image") else 0,
                                1 if metadata.get("tag_name") else 0,
                                1 if metadata.get("quantity") else 0,
                            ]
                        )

                        if score > best_score:
                            best_score = score
                            best_id = id_

                    # Remove all except the best
                    ids_to_remove.extend(
                        [id_ for id_ in duplicate_ids if id_ != best_id]
                    )

            # Remove duplicates from list
            ids_to_remove = list(set(ids_to_remove))

            if dry_run:
                return {
                    "status": "dry_run",
                    "would_remove": len(ids_to_remove),
                    "duplicate_groups": len(duplicates),
                    "sample_ids": ids_to_remove[:10],
                }

            # Actually remove duplicates
            if ids_to_remove:
                collection.delete(ids=ids_to_remove)
                logger.info(
                    f"Removed {len(ids_to_remove)} duplicates from {collection_name}"
                )

            return {
                "status": "success",
                "removed": len(ids_to_remove),
                "duplicate_groups": len(duplicates),
                "collection": collection_name,
            }

        except Exception as e:
            logger.error(f"Error removing duplicates: {e}")
            return {"status": "error", "error": str(e)}

    def check_before_insert(
        self,
        collection_name: str,
        metadata: Dict[str, Any],
        document: str,
        embedding: Optional[List[float]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if item would be a duplicate before inserting

        Args:
            collection_name: Target collection
            metadata: Item metadata
            document: Document text
            embedding: Optional embedding vector

        Returns:
            (is_duplicate, existing_id)
        """
        try:
            collection = self.chromadb_client.client.get_collection(collection_name)

            # First check exact match
            content_hash = self.generate_content_hash(metadata, document)

            # Query by metadata for exact match
            where_clause = {}
            if metadata.get("item_code") and metadata.get("item_code") not in [
                "NILL",
                "Unknown",
            ]:
                where_clause["item_code"] = metadata["item_code"]
            if metadata.get("source_file"):
                where_clause["source_file"] = metadata["source_file"]

            if where_clause:
                results = collection.get(
                    where=where_clause, include=["metadatas", "documents"]
                )

                # Check if exact duplicate exists
                for i, (existing_meta, existing_doc) in enumerate(
                    zip(results["metadatas"], results["documents"])
                ):
                    existing_hash = self.generate_content_hash(
                        existing_meta, existing_doc
                    )
                    if existing_hash == content_hash:
                        return True, results["ids"][i]

            # Check near duplicate by embedding if provided
            if embedding:
                results = collection.query(query_embeddings=[embedding], n_results=1)

                if results["distances"] and results["distances"][0]:
                    # Convert distance to similarity
                    similarity = 1 - results["distances"][0][0]
                    if similarity >= self.similarity_threshold:
                        return True, results["ids"][0][0]

            return False, None

        except Exception as e:
            logger.warning(f"Error checking for duplicates: {e}")
            # If error, allow insertion to avoid blocking
            return False, None

    def deduplicate_all_collections(
        self, strategy: str = "exact", keep: str = "best", dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Deduplicate all collections in the database

        Args:
            strategy: Deduplication strategy
            keep: Which duplicate to keep
            dry_run: If True, only report

        Returns:
            Results for all collections
        """
        results = {}

        try:
            collections = self.chromadb_client.client.list_collections()

            for collection in collections:
                if (
                    "tag_inventory" in collection.name
                    or "tag_images" in collection.name
                ):
                    logger.info(f"Deduplicating {collection.name}...")
                    result = self.remove_duplicates(
                        collection.name, strategy=strategy, keep=keep, dry_run=dry_run
                    )
                    results[collection.name] = result

            # Summary
            total_removed = sum(r.get("removed", 0) for r in results.values())

            return {
                "status": "success",
                "collections_processed": len(results),
                "total_removed": total_removed,
                "details": results,
            }

        except Exception as e:
            logger.error(f"Error in batch deduplication: {e}")
            return {"status": "error", "error": str(e)}

    def get_deduplication_stats(self) -> Dict[str, Any]:
        """
        Get statistics about duplicates across all collections

        Returns:
            Statistics dictionary
        """
        stats = {
            "collections": {},
            "total_items": 0,
            "total_exact_duplicates": 0,
            "total_near_duplicates": 0,
        }

        try:
            collections = self.chromadb_client.client.list_collections()

            for collection in collections:
                if (
                    "tag_inventory" in collection.name
                    or "tag_images" in collection.name
                ):
                    collection_obj = self.chromadb_client.client.get_collection(
                        collection.name
                    )
                    count = collection_obj.count()

                    # Find duplicates
                    exact_dups = self.find_duplicates_in_collection(
                        collection.name, "exact"
                    )
                    near_dups = self.find_duplicates_in_collection(
                        collection.name, "near"
                    )

                    exact_count = sum(len(ids) - 1 for ids in exact_dups.values())
                    near_count = sum(len(ids) - 1 for ids in near_dups.values())

                    stats["collections"][collection.name] = {
                        "total_items": count,
                        "exact_duplicates": exact_count,
                        "near_duplicates": near_count,
                        "duplicate_percentage": (
                            (exact_count / count * 100) if count > 0 else 0
                        ),
                    }

                    stats["total_items"] += count
                    stats["total_exact_duplicates"] += exact_count
                    stats["total_near_duplicates"] += near_count

            stats["overall_duplicate_percentage"] = (
                (stats["total_exact_duplicates"] / stats["total_items"] * 100)
                if stats["total_items"] > 0
                else 0
            )

            return stats

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"status": "error", "error": str(e)}
