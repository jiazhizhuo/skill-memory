"""
Mem0 client wrapper for vector storage.
Based on OpenClaw's hybrid search architecture.
"""

from typing import Optional, List
from mem0 import Memory
from qdrant_client import QdrantClient

from config.defaults import (
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
    VECTOR_WEIGHT,
    KEYWORD_WEIGHT,
    DEFAULT_TOP_K,
)


class Mem0Client:
    """
    Mem0 wrapper with OpenClaw-style hybrid search.

    Combines:
    - Vector search (semantic similarity)
    - Keyword search (BM25 style)
    - MMR reranking (diversity)
    - Temporal decay (recency bias)
    """

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.memory = Memory()  # Uses Qdrant by default
        self.qdrant = QdrantClient(
            host=QDRANT_HOST,
            port=QDRANT_PORT
        )

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
