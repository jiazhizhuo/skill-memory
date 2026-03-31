# skill-memory

OpenClaw-style 3-tier memory system with hybrid search. Cross-workspace shared memory.

## Architecture

### Storage Structure

```
~/.skill-memory/              ← Fixed location, shared across worktrees
├── memory/                   ← Mem0/Qdrant storage
│   └── memory.db
├── knowledge/               ← Organized knowledge
│   ├── MEMORY.md           ← Long-term memory (referenceable)
│   └── domains/           ← Domain knowledge
│       ├── python.md
│       ├── qoder.md
│       └── project-a.md
└── graph.json              ← Knowledge graph (nodes + edges)
```

### Three-tier Memory

| Tier | Storage | Lifecycle |
|------|---------|-----------|
| Working | Session context | Session only |
| Mid-term | Qdrant | 7 days TTL |
| Long-term | MEMORY.md | Permanent |

## Features

- **3-tier memory**: Working → Mid-term → Long-term
- **Hybrid search**: Vector + Keyword + MMR + Temporal decay
- **Cross-workspace**: Shared storage at `~/.skill-memory/`
- **Knowledge organization**: MEMORY.md + domains + graph

## Installation

### Load as Qoder Skill

```bash
# Link to Qoder skills directory
ln -s ~/git/jiazhizhuo/skill-memory ~/.qoder/skills/skill-memory
```

### Prerequisites

**Qdrant** (required for persistent storage):

```bash
# Docker
docker run -d -p 6333:6333 qdrant/qdrant

# Or binary (macOS arm64)
curl -L https://github.com/qdrant/qdrant/releases/latest/download/qdrant-aarch64-apple-darwin.tar.gz | tar -xz
./qdrant &
```

### Python Dependencies

```bash
pip install mem0ai qdrant-client
```

## Usage

### CLI Commands

```bash
memory add "用户偏好简洁代码" --tier long
memory add "项目配置" --tier mid
memory search "代码风格偏好"
memory list --tier mid
memory long                    # View long-term memory
memory stats                  # View statistics
```

### Integration with OpenClaw

```bash
//memory add 用户偏好深色主题
//memory search 用户的视觉偏好
```

### OpenClaw Agent Integration

Period organization can be triggered by OpenClaw agent:

```bash
# Via OpenClaw hooks (SessionStart, UserPromptSubmit)
# Or via cron
openclaw memory organize

# Organization includes:
# - Cluster similar memories
# - Build domain knowledge
# - Update MEMORY.md
# - Generate knowledge graph
```

## Configuration

### .env File

```bash
cp .env.example .env
# Edit with your API keys
```

### Environment Variables

```bash
export SKILL_MEMORY_LLM_PROVIDER=minimax
export SKILL_MEMORY_EMBEDDING_PROVIDER=minimax
export SKILL_MEMORY_MINIMAX_API_KEY=your_key
export SKILL_MEMORY_BACKEND=qdrant
```

## Hybrid Search

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
# skill-memory

OpenClaw-style 3-tier memory system with hybrid search. Cross-workspace shared memory.

## Architecture

### Storage Structure

```
~/.skill-memory/              ← Fixed location, shared across worktrees
├── memory/                   ← Mem0/Qdrant storage
│   └── memory.db
├── knowledge/               ← Organized knowledge
│   ├── MEMORY.md           ← Long-term memory (referenceable)
│   └── domains/           ← Domain knowledge
│       ├── python.md
│       ├── qoder.md
│       └── project-a.md
└── graph.json              ← Knowledge graph (nodes + edges)
```

### Three-tier Memory

| Tier | Storage | Lifecycle |
|------|---------|-----------|
| Working | Session context | Session only |
| Mid-term | Qdrant | 7 days TTL |
| Long-term | MEMORY.md | Permanent |

## Features

- **3-tier memory**: Working → Mid-term → Long-term
- **Hybrid search**: Vector + Keyword + MMR + Temporal decay
- **Cross-workspace**: Shared storage at `~/.skill-memory/`
- **Knowledge organization**: MEMORY.md + domains + graph

## Installation

### Load as Qoder Skill

```bash
# Link to Qoder skills directory
ln -s ~/git/jiazhizhuo/skill-memory ~/.qoder/skills/skill-memory
```

### Prerequisites

**Qdrant** (required for persistent storage):

```bash
# Docker
docker run -d -p 6333:6333 qdrant/qdrant

# Or binary (macOS arm64)
curl -L https://github.com/qdrant/qdrant/releases/latest/download/qdrant-aarch64-apple-darwin.tar.gz | tar -xz
./qdrant &
```

### Python Dependencies

```bash
pip install mem0ai qdrant-client
```

## Usage

### CLI Commands

```bash
memory add "用户偏好简洁代码" --tier long
memory add "项目配置" --tier mid
memory search "代码风格偏好"
memory list --tier mid
memory long                    # View long-term memory
memory stats                  # View statistics
```

### Integration with OpenClaw

```bash
//memory add 用户偏好深色主题
//memory search 用户的视觉偏好
```

### OpenClaw Agent Integration

Period organization can be triggered by OpenClaw agent:

```bash
# Via OpenClaw hooks (SessionStart, UserPromptSubmit)
# Or via cron
openclaw memory organize

# Organization includes:
# - Cluster similar memories
# - Build domain knowledge
# - Update MEMORY.md
# - Generate knowledge graph
```

## Configuration

### .env File

```bash
cp .env.example .env
# Edit with your API keys
```

### Environment Variables

```bash
export SKILL_MEMORY_LLM_PROVIDER=minimax
export SKILL_MEMORY_EMBEDDING_PROVIDER=minimax
export SKILL_MEMORY_MINIMAX_API_KEY=your_key
export SKILL_MEMORY_BACKEND=qdrant
```

## Hybrid Search

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
