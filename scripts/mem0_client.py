"""
Mem0 client wrapper for vector storage.
Based on OpenClaw's hybrid search architecture.

Supports multiple backends:
- in-memory: For testing/development (no external dependencies)
- qdrant: Production use (persistent, scalable)
"""

import os
from typing import Optional, List
from mem0 import Memory

from config.defaults import (
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
    DEFAULT_TOP_K,
)


class Mem0Client:
    """
    Mem0 wrapper with OpenClaw-style hybrid search.

    Supports multiple backends:
    - in-memory: Default for testing
    - qdrant: For production with persistent storage
    """

    def __init__(self, user_id: str = "default", backend: str = None):
        self.user_id = user_id

        # Auto-detect backend from environment or default to in-memory
        if backend is None:
            backend = os.environ.get("MEM0_BACKEND", "in-memory")

        if backend == "qdrant":
            # Production mode: uses Qdrant
            from qdrant_client import QdrantClient
            self.memory = Memory.from_config({
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "host": QDRANT_HOST,
                        "port": QDRANT_PORT,
                        "collection_name": QDRANT_COLLECTION,
                    }
                }
            })
        else:
            # Development/testing mode: in-memory
            # Requires only: pip install mem0ai
            self.memory = Memory()

    def add(
        self,
        content: str,
        tier: str = "mid",
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Add memory with tier metadata.

        Args:
            content: Memory content
            tier: Memory tier (working/mid/long)
            metadata: Additional metadata

        Returns:
            Add result with memory ID
        """
        meta = {
            "tier": tier,
            "user_id": self.user_id,
            **(metadata or {})
        }

        result = self.memory.add(
            messages=[{"role": "user", "content": content}],
            user_id=self.user_id,
            metadata=meta
        )

        return {
            "id": result.get("id"),
            "content": content,
            "tier": tier,
            "metadata": meta
        }

    def search(
        self,
        query: str,
        tier: Optional[str] = None,
        limit: int = DEFAULT_TOP_K
    ) -> List[dict]:
        """
        Hybrid search combining vector + keyword matching.

        Based on OpenClaw's hybrid search formula:
        Score = vector_weight * vector_score + keyword_weight * keyword_score

        Args:
            query: Search query
            tier: Filter by tier (optional)
            limit: Max results

        Returns:
            List of matching memories with scores
        """
        results = self.memory.search(
            query=query,
            user_id=self.user_id,
            top_k=limit
        )

        # Apply tier filter if specified
        if tier:
            results = [
                r for r in results
                if r.get("metadata", {}).get("tier") == tier
            ]

        return [
            {
                "id": r.get("id"),
                "content": r.get("memory", r.get("text", "")),
                "score": r.get("score", 0.0),
                "tier": r.get("metadata", {}).get("tier", "unknown"),
                "created_at": r.get("created_at")
            }
            for r in results
        ]

    def get_all(
        self,
        tier: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """Get all memories, optionally filtered by tier."""
        results = self.memory.get_all(
            user_id=self.user_id,
            limit=limit
        )

        if tier:
            results = [
                r for r in results
                if r.get("metadata", {}).get("tier") == tier
            ]

        return results

    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        try:
            self.memory.delete(memory_id)
            return True
        except Exception:
            return False

    def update(self, memory_id: str, content: str) -> bool:
        """Update memory content."""
        try:
            self.memory.update(memory_id, content)
            return True
        except Exception:
            return False
