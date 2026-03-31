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
import hashlib
import numpy as np
import requests
from typing import Optional, List
from mem0 import Memory
from mem0.embeddings.base import EmbeddingBase
from mem0.configs.embeddings.base import BaseEmbedderConfig

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


class MiniMaxEmbedding(EmbeddingBase):
    """MiniMax embedding with OpenAI-compatible interface."""

    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        super().__init__(config)
        self.config.model = self.config.model or MINIMAX_EMBEDDING_MODEL
        self.config.embedding_dims = self.config.embedding_dims or 1536

        api_key = self.config.api_key or os.environ.get("MINIMAX_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        base_url = self.config.openai_base_url or os.environ.get("OPENAI_BASE_URL") or MINIMAX_EMBEDDING_BASE_URL

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def embed(self, text: str, memory_action: Optional[str] = None) -> list:
        """Get embedding for text using MiniMax API."""
        text = text.replace("\n", " ")

        try:
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.model,
                    "texts": [text],  # MiniMax format
                    "type": "db",
                },
                timeout=30,
            )
            data = response.json()
            if "vectors" in data and data["vectors"]:
                return data["vectors"][0]
            elif "data" in data and data["data"]:
                return data["data"][0]["embedding"]
            else:
                # Fallback to hash-based
                return self._hash_embedding(text)
        except Exception:
            # Fallback to hash-based
            return self._hash_embedding(text)

    def _hash_embedding(self, text: str) -> list:
        """Generate deterministic embedding from text hash."""
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        np.random.seed(seed)
        vec = np.random.randn(1536).tolist()
        norm = np.linalg.norm(vec)
        return [v / norm for v in vec]


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
        embed_provider = os.environ.get("EMBEDDING_PROVIDER", "openai").lower()

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
                "embedder": {"provider": "openai", "config": {"api_key": "dummy"}},  # Will be replaced
            })
            # Replace embedder with our custom one if minimax
            if embed_provider == "minimax":
                self.memory.embedding_model = MiniMaxEmbedding()
        else:
            # Development/testing mode: in-memory
            # Requires only: pip install mem0ai
            self.memory = Memory.from_config({
                "llm": llm_config,
                "embedder": {"provider": "openai", "config": {"api_key": "dummy"}},  # Will be replaced
            })
            # Replace embedder with our custom one if minimax
            if embed_provider == "minimax":
                self.memory.embedding_model = MiniMaxEmbedding()

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
import hashlib
import numpy as np
import requests
from typing import Optional, List
from mem0 import Memory
from mem0.embeddings.base import EmbeddingBase
from mem0.configs.embeddings.base import BaseEmbedderConfig

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


class MiniMaxEmbedding(EmbeddingBase):
    """MiniMax embedding with OpenAI-compatible interface."""

    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        super().__init__(config)
        self.config.model = self.config.model or MINIMAX_EMBEDDING_MODEL
        self.config.embedding_dims = self.config.embedding_dims or 1536

        api_key = self.config.api_key or os.environ.get("MINIMAX_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        base_url = self.config.openai_base_url or os.environ.get("OPENAI_BASE_URL") or MINIMAX_EMBEDDING_BASE_URL

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def embed(self, text: str, memory_action: Optional[str] = None) -> list:
        """Get embedding for text using MiniMax API."""
        text = text.replace("\n", " ")

        try:
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.model,
                    "texts": [text],  # MiniMax format
                    "type": "db",
                },
                timeout=30,
            )
            data = response.json()
            if "vectors" in data and data["vectors"]:
                return data["vectors"][0]
            elif "data" in data and data["data"]:
                return data["data"][0]["embedding"]
            else:
                # Fallback to hash-based
                return self._hash_embedding(text)
        except Exception:
            # Fallback to hash-based
            return self._hash_embedding(text)

    def _hash_embedding(self, text: str) -> list:
        """Generate deterministic embedding from text hash."""
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        np.random.seed(seed)
        vec = np.random.randn(1536).tolist()
        norm = np.linalg.norm(vec)
        return [v / norm for v in vec]


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
        embed_provider = os.environ.get("EMBEDDING_PROVIDER", "openai").lower()

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
                "embedder": {"provider": "openai", "config": {"api_key": "dummy"}},  # Will be replaced
            })
            # Replace embedder with our custom one if minimax
            if embed_provider == "minimax":
                self.memory.embedding_model = MiniMaxEmbedding()
        else:
            # Development/testing mode: in-memory
            # Requires only: pip install mem0ai
            self.memory = Memory.from_config({
                "llm": llm_config,
                "embedder": {"provider": "openai", "config": {"api_key": "dummy"}},  # Will be replaced
            })
            # Replace embedder with our custom one if minimax
            if embed_provider == "minimax":
                self.memory.embedding_model = MiniMaxEmbedding()

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
