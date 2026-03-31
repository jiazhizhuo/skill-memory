"""
Default configuration for skill-memory.
Based on OpenClaw's memory architecture.
"""

from pathlib import Path
import os

# Storage paths
SKILL_DIR = Path.home() / ".openclaw" / "skills" / "memory"
MEMORY_DIR = SKILL_DIR / "memory"
LONG_TERM_FILE = SKILL_DIR / "long_term.md"
SQLITE_DB = SKILL_DIR / "memory.db"

# Qdrant configuration
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "skill_memory")

# Search configuration
VECTOR_WEIGHT = float(os.environ.get("VECTOR_WEIGHT", "0.7"))
KEYWORD_WEIGHT = float(os.environ.get("KEYWORD_WEIGHT", "0.3"))
DEFAULT_TOP_K = int(os.environ.get("DEFAULT_TOP_K", "5"))
MMR_LAMBDA = float(os.environ.get("MMR_LAMBDA", "0.7"))

# Temporal decay (OpenClaw style)
TEMPORAL_DECAY_ENABLED = os.environ.get("TEMPORAL_DECAY_ENABLED", "true").lower() == "true"
TEMPORAL_HALF_LIFE_DAYS = int(os.environ.get("TEMPORAL_HALF_LIFE_DAYS", "7"))

# Memory tier TTL (seconds)
TTL_CONFIG = {
    "working": 0,  # Session only, not persisted
    "mid": 7 * 24 * 3600,  # 7 days
    "long": 0,  # Permanent
}

# Embedding model (configurable)
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMS = int(os.environ.get("EMBEDDING_DIMS", "1536"))

# LLM provider (for mem0)
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")
EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "openai")

# MiniMax configuration (if using MiniMax)
MINIMAX_LLM_BASE_URL = os.environ.get("MINIMAX_LLM_BASE_URL", "https://api.minimax.io/v1")
MINIMAX_LLM_MODEL = os.environ.get("MINIMAX_LLM_MODEL", "MiniMax-M2.7")
MINIMAX_EMBEDDING_BASE_URL = os.environ.get("MINIMAX_EMBEDDING_BASE_URL", "https://api.minimax.chat/v1")
MINIMAX_EMBEDDING_MODEL = os.environ.get("MINIMAX_EMBEDDING_MODEL", "embo-01")
