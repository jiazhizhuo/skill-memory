# Skill Memory

跨 Workspace 的 AI Agent 持久记忆系统。基于 Mem0 + Qdrant 实现语义检索，支持 MiniMax/OpenAI 等 LLM 提供商。

## 工作机制

```
对话发生 → AgentResponseComplete Hook 触发 → 提取关键信息 → 存入 Qdrant
                                              ↓ 重要性 >= 0.8
                                          同步写入 MEMORY.md
```

### 触发方式

- **自动触发**：Qoder `AgentResponseComplete` 事件（每次 AI 回复后）
- **手动导入**：`memory import --file transcript.jsonl`

### 配置 Hook

`~/.qoder/settings.json`:

```json
{
  "hooks": {
    "AgentResponseComplete": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.skill-memory/hooks/mem0_memory_hook.py"
          }
        ]
      }
    ]
  }
}
```

## 快速配置

### 1. 启动 Qdrant

```bash
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### 2. 配置 .env

`~/.skill-memory/.env`:

```bash
# MiniMax (推荐)
SKILL_MEMORY_LLM_PROVIDER=minimax
SKILL_MEMORY_LLM_MODEL=MiniMax-M2.5
SKILL_MEMORY_MINIMAX_LLM_BASE_URL=https://api.minimaxi.com/v1
SKILL_MEMORY_MINIMAX_EMBEDDING_MODEL=embo-01
SKILL_MEMORY_API_KEY=your_key

# 或 OpenAI
# SKILL_MEMORY_LLM_PROVIDER=openai
# SKILL_MEMORY_API_KEY=sk-xxx
```

### 3. Hook 配置

`~/.skill-memory/config/hook.toml`:

```toml
[filter]
min_length = 30           # 最小内容长度
max_per_round = 5          # 每轮最多保存条数
skip_patterns = thanks, /help  # 跳过的模式

[memory]
tier = auto               # auto/short/long
promotion_threshold = 0.75 # 晋升到 MEMORY.md 的阈值
```

## CLI 命令

```bash
# 添加记忆
python3 -m src.cli add "用户偏好深色主题" --importance 0.8

# 搜索记忆
python3 -m src.cli search "代码风格"

# 列出记忆
python3 -m src.cli list --limit 20

# 导入历史对话
python3 -m src.cli import --file transcript.jsonl --tier long

# 查看统计
python3 -m src.cli stats
```

## 支持的提供商

| Provider | LLM Model | Embedding |
|----------|-----------|-----------|
| MiniMax | MiniMax-M2.5 | embo-01 |
| OpenAI | gpt-4o-mini | text-embedding-3-small |
| 其他 | OpenAI compatible | OpenAI compatible |

## 存储结构

```
~/.skill-memory/
├── .env                 # API 配置
├── config/hook.toml   # Hook 行为配置
├── hooks/              # Qoder Hook 脚本
│   └── mem0_memory_hook.py
├── knowledge/          # 长期记忆
│   └── MEMORY.md
└── src/                # 核心代码
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SKILL_MEMORY_API_KEY` | API Key | - |
| `SKILL_MEMORY_LLM_PROVIDER` | LLM 提供商 | minimax |
| `SKILL_MEMORY_QDRANT_HOST` | Qdrant 主机 | localhost |
| `SKILL_MEMORY_QDRANT_PORT` | Qdrant 端口 | 6333 |
| `SKILL_MEMORY_QDRANT_COLLECTION` | Collection 名 | skill_memory |

---

MIT License
