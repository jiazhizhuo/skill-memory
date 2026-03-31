"""
Default configuration for skill-memory.
Based on OpenClaw's memory architecture.
"""

from pathlib import Path
import os

# Prefix for skill-memory specific env vars
PREFIX = "SKILL_MEMORY_"

def _env(key: str, default: str) -> str:
    """Get env var with SKILL_MEMORY_ prefix, fallback to global."""
    return os.environ.get(PREFIX + key, os.environ.get(key, default))

def _env_int(key: str, default: str) -> int:
    return int(_env(key, default))

def _env_float(key: str, default: str) -> float:
    return float(_env(key, default))

# Storage paths
SKILL_DIR = Path.home() / ".openclaw" / "skills" / "memory"
MEMORY_DIR = SKILL_DIR / "memory"
LONG_TERM_FILE = SKILL_DIR / "long_term.md"
SQLITE_DB = SKILL_DIR / "memory.db"

# Qdrant configuration
QDRANT_HOST = _env("QDRANT_HOST", "localhost")
QDRANT_PORT = _env_int("QDRANT_PORT", "6333")
QDRANT_COLLECTION = _env("QDRANT_COLLECTION", "skill_memory")

# Search configuration
VECTOR_WEIGHT = _env_float("VECTOR_WEIGHT", "0.7")
KEYWORD_WEIGHT = _env_float("KEYWORD_WEIGHT", "0.3")
DEFAULT_TOP_K = _env_int("DEFAULT_TOP_K", "5")
MMR_LAMBDA = _env_float("MMR_LAMBDA", "0.7")

# Temporal decay (OpenClaw style)
TEMPORAL_DECAY_ENABLED = _env("TEMPORAL_DECAY_ENABLED", "true").lower() == "true"
TEMPORAL_HALF_LIFE_DAYS = _env_int("TEMPORAL_HALF_LIFE_DAYS", "7")

# Memory tier TTL (seconds)
TTL_CONFIG = {
    "working": 0,  # Session only, not persisted
    "mid": 7 * 24 * 3600,  # 7 days
    "long": 0,  # Permanent
}

# Embedding model (configurable)
EMBEDDING_MODEL = _env("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMS = _env_int("EMBEDDING_DIMS", "1536")

# LLM provider (for mem0)
LLM_PROVIDER = _env("LLM_PROVIDER", "openai")
EMBEDDING_PROVIDER = _env("EMBEDDING_PROVIDER", "openai")

# MiniMax configuration (if using MiniMax)
MINIMAX_LLM_BASE_URL = _env("MINIMAX_LLM_BASE_URL", "https://api.minimax.io/v1")
MINIMAX_LLM_MODEL = _env("MINIMAX_LLM_MODEL", "MiniMax-M2.7")
MINIMAX_EMBEDDING_BASE_URL = _env("MINIMAX_EMBEDDING_BASE_URL", "https://api.minimax.chat/v1")
MINIMAX_EMBEDDING_MODEL = _env("MINIMAX_EMBEDDING_MODEL", "embo-01")
