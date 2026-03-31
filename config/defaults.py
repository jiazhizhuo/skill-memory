"""
Default configuration for skill-memory.
Based on OpenClaw's memory architecture.
"""

from pathlib import Path

# Storage paths
SKILL_DIR = Path.home() / ".openclaw" / "skills" / "memory"
MEMORY_DIR = SKILL_DIR / "memory"
LONG_TERM_FILE = SKILL_DIR / "long_term.md"
SQLITE_DB = SKILL_DIR / "memory.db"

# Qdrant configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "skill_memory"

# Search configuration
VECTOR_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3
DEFAULT_TOP_K = 5
MMR_LAMBDA = 0.7  # Diversity vs relevance balance

# Temporal decay (OpenClaw style)
TEMPORAL_DECAY_ENABLED = True
TEMPORAL_HALF_LIFE_DAYS = 7

# Memory tier TTL (seconds)
TTL_CONFIG = {
    "working": 0,  # Session only, not persisted
    "mid": 7 * 24 * 3600,  # 7 days
    "long": 0,  # Permanent
}

# Embedding model (configurable)
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536
