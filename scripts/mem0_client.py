"""
Mem0 client wrapper for vector storage.
Based on OpenClaw's hybrid search architecture.

Supports multiple backends:
- in-memory: For testing/development (no external dependencies)
- qdrant: Production use (persistent, scalable)

Supports multiple embedding providers:
- openai: Default (requires OPENAI_API_KEY)
- minimax: MiniMax embedding (requires MINIMAX_API_KEY)
"""

import os
from typing import Optional, List
from mem0 import Memory

from config.defaults import (
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
    DEFAULT_TOP_K,
    MINIMAX_LLM_BASE_URL,
    MINIMAX_LLM_MODEL,
    MINIMAX_EMBEDDING_BASE_URL,
    MINIMAX_EMBEDDING_MODEL,
)


def _get_llm_config() -> dict:
    """
    Get LLM configuration from environment variables.
    
    Supported providers:
    - MINIMAX: Use MiniMax LLM API
      - LLM_PROVIDER=minimax
      - MINIMAX_API_KEY: MiniMax API key
      - MINIMAX_LLM_MODEL: Model name (default: MiniMax-M2.7)
      - MINIMAX_LLM_BASE_URL: API base URL (default: https://api.minimax.io/v1)
    - OPENAI: Use OpenAI LLM (default fallback)
      - OPENAI_API_KEY: OpenAI API key
    """
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    
    if provider == "minimax":
        api_key = os.environ.get("MINIMAX_API_KEY")
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY", "")
        
        model = os.environ.get("MINIMAX_LLM_MODEL", MINIMAX_LLM_MODEL)
        base_url = os.environ.get("MINIMAX_LLM_BASE_URL", MINIMAX_LLM_BASE_URL)
        
        return {
            "provider": "minimax",
            "config": {
                "api_key": api_key,
                "model": model,
                "minimax_base_url": base_url,
            }
        }
    
    # Default: OpenAI
    return {
        "provider": "openai",
        "config": {
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
        }
    }


def _get_embedding_config() -> dict:
    """
    Get embedding configuration from environment variables.
    
    Supported providers:
    - MINIMAX: Use MiniMax embedding API
      - EMBEDDING_PROVIDER=minimax
      - MINIMAX_API_KEY: MiniMax API key
      - MINIMAX_EMBEDDING_MODEL: Model name (default: emb-o1)
      - MINIMAX_EMBEDDING_BASE_URL: API base URL
    - OPENAI: Use OpenAI embedding (default fallback)
      - OPENAI_API_KEY: OpenAI API key
      - OPENAI_BASE_URL: Custom base URL (optional)
    """
    provider = os.environ.get("EMBEDDING_PROVIDER", "openai").lower()
    
    if provider == "minimax":
        api_key = os.environ.get("MINIMAX_API_KEY")
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY", "")
        
        model = os.environ.get("MINIMAX_EMBEDDING_MODEL", MINIMAX_EMBEDDING_MODEL)
        
        return {
            "provider": "openai",
            "config": {
                "api_key": api_key,
                "model": model,
            }
        }
    
    # Default: OpenAI
    return {
        "provider": "openai",
        "config": {
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
        }
    }


def _setup_embedding_env():
    """Set up environment variables for embedding provider."""
    provider = os.environ.get("EMBEDDING_PROVIDER", "").lower()
    
    if provider == "minimax":
        # mem0 openai embedding reads from OPENAI_BASE_URL
        base_url = os.environ.get(
            "MINIMAX_EMBEDDING_BASE_URL", 
            MINIMAX_EMBEDDING_BASE_URL
        )
        os.environ.setdefault("OPENAI_BASE_URL", base_url)


class Mem0Client:
    """
    Mem0 wrapper with OpenClaw-style hybrid search.

    Supports multiple backends:
    - in-memory: Default for testing
    - qdrant: For production with persistent storage
    
    Supports multiple embedding providers (via EMBEDDING_PROVIDER env):
    - minimax: MiniMax embedding (default if MINIMAX_API_KEY is set)
    - openai: OpenAI embedding (default fallback)
    """

    def __init__(self, user_id: str = "default", backend: str = None):
        self.user_id = user_id

        # Auto-detect backend from environment or default to in-memory
        if backend is None:
            backend = os.environ.get("MEM0_BACKEND", "in-memory")

        # Get LLM and embedding configs
        llm_config = _get_llm_config()
        embed_config = _get_embedding_config()

        if backend == "qdrant":
            # Production mode: uses Qdrant
            from qdrant_client import QdrantClient
            self.memory = Memory.from_config({
                "llm": llm_config,
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "host": QDRANT_HOST,
                        "port": QDRANT_PORT,
                        "collection_name": QDRANT_COLLECTION,
                    }
                },
                "embedder": embed_config,
            })
        else:
            # Development/testing mode: in-memory
            # Requires only: pip install mem0ai
            self.memory = Memory.from_config({
                "llm": llm_config,
                "embedder": embed_config,
            })

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
        raw_results = self.memory.search(
            query=query,
            user_id=self.user_id,
            limit=limit
        )
        # Handle mem0 v1.x format: {'results': [...]}
        results = raw_results.get('results', raw_results) if isinstance(raw_results, dict) else raw_results

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
        raw_results = self.memory.get_all(
            user_id=self.user_id,
            limit=limit
        )
        # Handle mem0 v1.x format: {'results': [...]}
        results = raw_results.get('results', raw_results) if isinstance(raw_results, dict) else raw_results

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
"""
Mem0 client wrapper for vector storage.
Based on OpenClaw's hybrid search architecture.

Supports multiple backends:
- in-memory: For testing/development (no external dependencies)
- qdrant: Production use (persistent, scalable)

Supports multiple embedding providers:
- openai: Default (requires OPENAI_API_KEY)
- minimax: MiniMax embedding (requires MINIMAX_API_KEY)
"""

import os
from typing import Optional, List
from mem0 import Memory

from config.defaults import (
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
    DEFAULT_TOP_K,
    MINIMAX_LLM_BASE_URL,
    MINIMAX_LLM_MODEL,
    MINIMAX_EMBEDDING_BASE_URL,
    MINIMAX_EMBEDDING_MODEL,
)


def _get_llm_config() -> dict:
    """
    Get LLM configuration from environment variables.
    
    Supported providers:
    - MINIMAX: Use MiniMax LLM API
      - LLM_PROVIDER=minimax
      - MINIMAX_API_KEY: MiniMax API key
      - MINIMAX_LLM_MODEL: Model name (default: MiniMax-M2.7)
      - MINIMAX_LLM_BASE_URL: API base URL (default: https://api.minimax.io/v1)
    - OPENAI: Use OpenAI LLM (default fallback)
      - OPENAI_API_KEY: OpenAI API key
    """
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    
    if provider == "minimax":
        api_key = os.environ.get("MINIMAX_API_KEY")
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY", "")
        
        model = os.environ.get("MINIMAX_LLM_MODEL", MINIMAX_LLM_MODEL)
        base_url = os.environ.get("MINIMAX_LLM_BASE_URL", MINIMAX_LLM_BASE_URL)
        
        return {
            "provider": "minimax",
            "config": {
                "api_key": api_key,
                "model": model,
                "minimax_base_url": base_url,
            }
        }
    
    # Default: OpenAI
    return {
        "provider": "openai",
        "config": {
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
        }
    }


def _get_embedding_config() -> dict:
    """
    Get embedding configuration from environment variables.
    
    Supported providers:
    - MINIMAX: Use MiniMax embedding API
      - EMBEDDING_PROVIDER=minimax
      - MINIMAX_API_KEY: MiniMax API key
      - MINIMAX_EMBEDDING_MODEL: Model name (default: emb-o1)
      - MINIMAX_EMBEDDING_BASE_URL: API base URL
    - OPENAI: Use OpenAI embedding (default fallback)
      - OPENAI_API_KEY: OpenAI API key
      - OPENAI_BASE_URL: Custom base URL (optional)
    """
    provider = os.environ.get("EMBEDDING_PROVIDER", "openai").lower()
    
    if provider == "minimax":
        api_key = os.environ.get("MINIMAX_API_KEY")
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY", "")
        
        model = os.environ.get("MINIMAX_EMBEDDING_MODEL", MINIMAX_EMBEDDING_MODEL)
        
        return {
            "provider": "openai",
            "config": {
                "api_key": api_key,
                "model": model,
            }
        }
    
    # Default: OpenAI
    return {
        "provider": "openai",
        "config": {
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
        }
    }


def _setup_embedding_env():
    """Set up environment variables for embedding provider."""
    provider = os.environ.get("EMBEDDING_PROVIDER", "").lower()
    
    if provider == "minimax":
        # mem0 openai embedding reads from OPENAI_BASE_URL
        base_url = os.environ.get(
            "MINIMAX_EMBEDDING_BASE_URL", 
            MINIMAX_EMBEDDING_BASE_URL
        )
        os.environ.setdefault("OPENAI_BASE_URL", base_url)


class Mem0Client:
    """
    Mem0 wrapper with OpenClaw-style hybrid search.

    Supports multiple backends:
    - in-memory: Default for testing
    - qdrant: For production with persistent storage
    
    Supports multiple embedding providers (via EMBEDDING_PROVIDER env):
    - minimax: MiniMax embedding (default if MINIMAX_API_KEY is set)
    - openai: OpenAI embedding (default fallback)
    """

    def __init__(self, user_id: str = "default", backend: str = None):
        self.user_id = user_id

        # Auto-detect backend from environment or default to in-memory
        if backend is None:
            backend = os.environ.get("MEM0_BACKEND", "in-memory")

        # Get LLM and embedding configs
        llm_config = _get_llm_config()
        embed_config = _get_embedding_config()

        if backend == "qdrant":
            # Production mode: uses Qdrant
            from qdrant_client import QdrantClient
            self.memory = Memory.from_config({
                "llm": llm_config,
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "host": QDRANT_HOST,
                        "port": QDRANT_PORT,
                        "collection_name": QDRANT_COLLECTION,
                    }
                },
                "embedder": embed_config,
            })
        else:
            # Development/testing mode: in-memory
            # Requires only: pip install mem0ai
            self.memory = Memory.from_config({
                "llm": llm_config,
                "embedder": embed_config,
            })

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
        raw_results = self.memory.search(
            query=query,
            user_id=self.user_id,
            limit=limit
        )
        # Handle mem0 v1.x format: {'results': [...]}
        results = raw_results.get('results', raw_results) if isinstance(raw_results, dict) else raw_results

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
        raw_results = self.memory.get_all(
            user_id=self.user_id,
            limit=limit
        )
        # Handle mem0 v1.x format: {'results': [...]}
        results = raw_results.get('results', raw_results) if isinstance(raw_results, dict) else raw_results

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
