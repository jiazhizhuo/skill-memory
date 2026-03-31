"""
Three-tier memory manager.
Inspired by OpenClaw's memory architecture:
- Working: Session context (in-memory)
- Mid-term: Daily notes (Qdrant + TTL)
- Long-term: MEMORY.md equivalent (permanent)
"""

from enum import Enum
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from config.defaults import (
    TTL_CONFIG,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
)


class MemoryTier(Enum):
    WORKING = "working"
    MID = "mid"
    LONG = "long"


@dataclass
class MemoryEntry:
    id: str
    content: str
    tier: MemoryTier
    created_at: datetime
    metadata: dict


class TierManager:
    """
    Three-tier memory manager based on OpenClaw's architecture.

    Tier lifecycle:
    - Working: Single session, not persisted
    - Mid-term: Daily notes style, with TTL expiration
    - Long-term: Permanent, like MEMORY.md
    """

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.working_memory: list[dict] = []

    def add_working(self, content: str) -> MemoryEntry:
        """Add to working memory (session only)."""
        entry = MemoryEntry(
            id=f"working_{datetime.now().timestamp()}",
            content=content,
            tier=MemoryTier.WORKING,
            created_at=datetime.now(),
            metadata={}
        )
        self.working_memory.append({
            "id": entry.id,
            "content": entry.content,
            "tier": entry.tier.value,
            "created_at": entry.created_at.isoformat()
        })
        return entry

    def add_mid_term(self, content: str, metadata: Optional[dict] = None) -> MemoryEntry:
        """Add to mid-term memory (daily notes style, with TTL)."""
        entry = MemoryEntry(
            id=f"mid_{datetime.now().timestamp()}",
            content=content,
            tier=MemoryTier.MID,
            created_at=datetime.now(),
            metadata={
                "ttl": TTL_CONFIG["mid"],
                "expires_at": datetime.now().timestamp() + TTL_CONFIG["mid"],
                **(metadata or {})
            }
        )
        # In actual implementation, this would store to Qdrant
        return entry

    def add_long_term(self, content: str, metadata: Optional[dict] = None) -> MemoryEntry:
        """Add to long-term memory (permanent, like MEMORY.md)."""
        entry = MemoryEntry(
            id=f"long_{datetime.now().timestamp()}",
            content=content,
            tier=MemoryTier.LONG,
            created_at=datetime.now(),
            metadata={
                "permanent": True,
                **(metadata or {})
            }
        )
        # In actual implementation, this would store to both SQLite and Qdrant
        return entry

    def add(
        self,
        content: str,
        tier: str = "mid",
        importance: float = 0.5,
        metadata: Optional[dict] = None
    ) -> MemoryEntry:
        """
        Add memory with tier auto-detection.

        If importance >= 0.8, auto-promote to long-term.
        """
        if tier == "auto":
            tier = "long" if importance >= 0.8 else "mid"

        tier_enum = MemoryTier(tier)

        if tier_enum == MemoryTier.WORKING:
            return self.add_working(content)
        elif tier_enum == MemoryTier.MID:
            return self.add_mid_term(content, metadata)
        else:
            return self.add_long_term(content, metadata)

    def get_working(self) -> list[dict]:
        """Get all working memory."""
        return self.working_memory

    def get_today_notes(self) -> list[dict]:
        """Get today's daily notes (OpenClaw style: memory/YYYY-MM-DD.md)."""
        today = datetime.now().strftime("%Y-%m-%d")
        # In actual implementation, read from memory/{today}.md
        return []

    def get_long_term(self) -> list[dict]:
        """Get long-term memory (like MEMORY.md)."""
        # In actual implementation, read from long_term.md
        return []

    def get_stats(self) -> dict:
        """Get memory tier statistics."""
        return {
            "working": len(self.working_memory),
            "mid_term": 0,  # Would query Qdrant
            "long_term": 0,  # Would query SQLite
            "total": len(self.working_memory)
        }
