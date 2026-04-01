"""
Configuration management module
Supports environment variables and .env file configuration
"""

import os
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from urllib.parse import urlparse


# Storage root (consistent with skill-memory)
DEFAULT_STORAGE_ROOT = Path.home() / ".skill-memory"

# Default environment variable prefix
ENV_PREFIX = "SKILL_MEMORY_"


@dataclass
class Mem0Config:
    """Memory system configuration"""

    # Storage paths
    storage_root: Path = field(default_factory=lambda: DEFAULT_STORAGE_ROOT)
    memory_dir: Path = field(init=False)
    knowledge_dir: Path = field(init=False)
    memory_db_path: Path = field(init=False)
    memory_md_path: Path = field(init=False)

    # Qdrant configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "qoder_memory"
    qdrant_url: str = field(init=False)

    # Search parameters
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    default_top_k: int = 5
    mmr_lambda: float = 0.7
    temporal_half_life_days: int = 7

    # LLM/Embedding providers
    llm_provider: str = "openai"
    embedding_provider: str = "openai"

    # API configuration
    api_key: str = ""
    base_url: Optional[str] = None
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # Memory tier TTL (seconds)
    working_ttl: int = 0  # In-session, not persisted
    mid_ttl_days: int = 7
    long_ttl: int = 0  # Permanent

    # Importance threshold
    promotion_threshold: float = 0.8  # >= this value promotes to long-term memory

    def __post_init__(self):
        """Initialize derived fields"""
        self.memory_dir = self.storage_root / "memory"
        self.knowledge_dir = self.storage_root / "knowledge"
        self.memory_db_path = self.memory_dir / "memory.db"
        self.memory_md_path = self.knowledge_dir / "MEMORY.md"
        self.qdrant_url = f"http://{self.qdrant_host}:{self.qdrant_port}"

        # Ensure directories exist
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "storage_root": str(self.storage_root),
            "qdrant_url": self.qdrant_url,
            "qdrant_collection": self.qdrant_collection,
            "vector_weight": self.vector_weight,
            "keyword_weight": self.keyword_weight,
            "default_top_k": self.default_top_k,
            "llm_provider": self.llm_provider,
            "embedding_provider": self.embedding_provider,
        }


def _camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case"""
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def load_config(config_path: Optional[Path] = None) -> Mem0Config:
    """
    Load configuration
    Priority: environment variables > .env file > defaults

    Supported environment variables:
    - SKILL_MEMORY_* prefix (recommended)
    - MEM0_* prefix (Mem0 standard variables)
    - Unprefixed standard variables (LLM_PROVIDER, BACKEND, etc.)
    """
    # Load .env file
    if config_path and config_path.exists():
        load_dotenv(config_path)
    else:
        # Try loading from storage root
        env_path = DEFAULT_STORAGE_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)

    # Build configuration from environment variables
    config_dict = {}

    # ========== 1. Support Mem0 standard environment variables ==========
    # MEM0_BACKEND -> qdrant_host/collection
    mem0_backend = os.environ.get("MEM0_BACKEND", "") or os.environ.get("BACKEND", "")
    if mem0_backend == "qdrant":
        config_dict["qdrant_host"] = os.environ.get("MEM0_QDRANT_HOST", "localhost")
        config_dict["qdrant_port"] = int(os.environ.get("MEM0_QDRANT_PORT", "6333"))
        collection = os.environ.get("MEM0_QDRANT_COLLECTION", "qoder_memory")
        config_dict["qdrant_collection"] = collection

    # QDRANT_URL -> complete Qdrant URL
    qdrant_url = os.environ.get("QDRANT_URL", "")
    if qdrant_url:
        # Parse URL
        if qdrant_url.startswith("http"):
            parsed = urlparse(qdrant_url)
            config_dict["qdrant_host"] = parsed.hostname or "localhost"
            config_dict["qdrant_port"] = parsed.port or 6333

    # LLM_PROVIDER -> llm_provider
    llm_provider = os.environ.get("LLM_PROVIDER", "")
    if llm_provider:
        config_dict["llm_provider"] = llm_provider

    # EMBEDDING_PROVIDER -> embedding_provider
    embedding_provider = os.environ.get("EMBEDDING_PROVIDER", "")
    if embedding_provider:
        config_dict["embedding_provider"] = embedding_provider

    # ========== 2. MiniMax specific configuration ==========
    minimax_base_url = os.environ.get("SKILL_MEMORY_MINIMAX_LLM_BASE_URL", "")
    if minimax_base_url:
        config_dict["base_url"] = minimax_base_url

    minimax_embedding_model = os.environ.get("SKILL_MEMORY_MINIMAX_EMBEDDING_MODEL", "")
    if minimax_embedding_model:
        config_dict["embedding_model"] = minimax_embedding_model

    minimax_llm_model = os.environ.get("SKILL_MEMORY_MINIMAX_LLM_MODEL", "")
    if minimax_llm_model:
        config_dict["llm_model"] = minimax_llm_model

    # MiniMax base URL (unprefixed)
    minimax_base = os.environ.get("MINIMAX_LLM_BASE_URL", "") or os.environ.get("OPENAI_BASE_URL", "")
    if minimax_base and not config_dict.get("base_url"):
        config_dict["base_url"] = minimax_base

    # ========== 3. SKILL_MEMORY_* prefixed variables ==========
    for key, value in os.environ.items():
        if not key.startswith(ENV_PREFIX):
            continue

        # Remove prefix and convert to camelCase
        attr_name = _camel_to_snake(key[len(ENV_PREFIX):])

        # Skip already processed
        if attr_name in ["minimax_llm_base_url", "minimax_embedding_base_url", "minimax_llm_model"]:
            continue

        # Type conversion
        if attr_name in ["qdrant_port", "default_top_k", "mid_ttl_days",
                          "temporal_half_life_days", "working_ttl", "long_ttl"]:
            config_dict[attr_name] = int(value)
        elif attr_name in ["vector_weight", "keyword_weight", "mmr_lambda",
                            "promotion_threshold"]:
            config_dict[attr_name] = float(value)
        elif attr_name in ["api_key", "llm_model", "embedding_model",
                            "llm_provider", "embedding_provider",
                            "qdrant_host", "qdrant_collection", "base_url"]:
            config_dict[attr_name] = value
        elif attr_name == "storage_root":
            config_dict[attr_name] = Path(value)

    return Mem0Config(**config_dict)


def get_default_config() -> Mem0Config:
    """Get default configuration"""
    return Mem0Config()


def save_config(config: Mem0Config, config_path: Optional[Path] = None) -> None:
    """Save configuration to .env file"""
    if config_path is None:
        config_path = DEFAULT_STORAGE_ROOT / ".env"

    lines = [
        f"# Skill Memory Configuration",
        f"# Generated by skill-memory",
        f"",
        f"# Qdrant",
        f"SKILL_MEMORY_QDRANT_HOST={config.qdrant_host}",
        f"SKILL_MEMORY_QDRANT_PORT={config.qdrant_port}",
        f"SKILL_MEMORY_QDRANT_COLLECTION={config.qdrant_collection}",
        f"",
        f"# LLM",
        f"SKILL_MEMORY_LLM_PROVIDER={config.llm_provider}",
        f"SKILL_MEMORY_LLM_MODEL={config.llm_model}",
        f"SKILL_MEMORY_API_KEY={config.api_key}",
        f"",
        f"# Embedding",
        f"SKILL_MEMORY_EMBEDDING_PROVIDER={config.embedding_provider}",
        f"SKILL_MEMORY_EMBEDDING_MODEL={config.embedding_model}",
        f"",
        f"# Search",
        f"SKILL_MEMORY_VECTOR_WEIGHT={config.vector_weight}",
        f"SKILL_MEMORY_KEYWORD_WEIGHT={config.keyword_weight}",
        f"SKILL_MEMORY_DEFAULT_TOP_K={config.default_top_k}",
    ]

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("\n".join(lines))
