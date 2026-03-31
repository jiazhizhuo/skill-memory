# skill-memory

OpenClaw-style 3-tier memory system with hybrid search.

## Architecture

Based on OpenClaw's memory architecture:

| Tier | OpenClaw | Storage | Lifecycle |
|------|----------|---------|-----------|
| Working | Session context | Memory | Session only |
| Mid-term | memory/YYYY-MM-DD.md | Qdrant | 7 days TTL |
| Long-term | MEMORY.md | Qdrant + SQLite | Permanent |

## Features

- **3-tier memory**: Working → Mid-term → Long-term
- **Hybrid search**: Vector + Keyword + MMR + Temporal decay
- **OpenClaw compatible**: Similar to MEMORY.md and daily notes
- **SQLite + Qdrant**: Reliable storage backend

## Installation

### One-click install

```bash
curl -fsSL https://raw.githubusercontent.com/jiazhizhuo/skill-memory/main/install.sh | bash
```

### Manual install

```bash
git clone https://github.com/jiazhizhuo/skill-memory.git ~/.openclaw/skills/memory
cd ~/.openclaw/skills/memory
pip install -e .
```

## Prerequisites

### Option A: In-Memory Mode (Default, No Setup)

```bash
# Just install, no external dependencies needed
pip install mem0ai
```

### Option B: Qdrant Mode (Production, Persistent)

```bash
# Start Qdrant via Docker
docker run -d -p 6333:6333 qdrant/qdrant

# Or via Homebrew (macOS)
brew install qdrant
qdrant

# Set environment variable
export MEM0_BACKEND=qdrant
```

### Option C: Other Vector Databases

Mem0 also supports Chroma, PGVector, Pinecone, Redis, etc. See [Mem0 docs](https://docs.mem0.ai/components/vectordbs/overview).

## Usage

### CLI Commands

```bash
# Add memory
memory add "用户喜欢简洁的代码风格"
memory add "重要项目信息" --tier long
memory add "临时笔记" --importance 0.3

# Search (hybrid search with MMR)
memory search "代码风格偏好"
memory search "项目配置" --limit 10

# List
memory list --tier mid
memory today
memory long

# Stats
memory stats

# Delete
memory delete abc123
```

### Integration with OpenClaw

The skill can be used as a tool by OpenClaw agents:

```bash
//memory add 用户偏好深色主题
//memory search 用户的视觉偏好
```

## Configuration

### Quick Setup with .env File (Recommended)

```bash
# Copy example config
cp .env.example .env

# Edit with your API keys
nano .env

# CLI automatically loads .env
memory add "test"
```

### Manual Environment Variables

```bash
# MiniMax Configuration
export LLM_PROVIDER=minimax
export EMBEDDING_PROVIDER=minimax
export MINIMAX_API_KEY=your_api_key
export MEM0_BACKEND=qdrant
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `MEM0_BACKEND` | `in-memory` | `in-memory` or `qdrant` |
| `LLM_PROVIDER` | `openai` | `openai` or `minimax` |
| `EMBEDDING_PROVIDER` | `openai` | `openai` or `minimax` |
| `MINIMAX_API_KEY` | - | MiniMax API key |
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `QDRANT_PORT` | `6333` | Qdrant server port |

## Hybrid Search

Based on OpenClaw's search architecture:

```
Combined Score = 0.7 * Vector + 0.3 * Keyword
                        ↓
                 MMR Reranking
                 (diversity)
                        ↓
                Temporal Decay
                (recency bias)
```

## License

MIT
