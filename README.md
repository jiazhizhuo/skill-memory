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

1. **Qdrant** (vector database):
   ```bash
   docker run -d -p 6333:6333 qdrant/qdrant
   ```

2. **Mem0** (installed automatically via pip)

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
