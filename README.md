# Skill Memory

跨应用的 AI Agent 持久记忆系统。基于 Mem0 + Qdrant 实现语义检索，支持 MiniMax/OpenAI 等 LLM 提供商。

## 功能特性

| 特性 | 说明 |
|------|------|
| **三层记忆** | Working (会话) → Mid (7天) → Long (永久) |
| **向量检索** | 基于嵌入的语义搜索 |
| **自动保存** | Hook 触发后自动提取关键信息 |
| **重要性分级** | 0.0-1.0，自动晋升到长期记忆 |

## 工作机制

```
对话发生 → AgentResponseComplete Hook 触发 → 提取关键信息 → 存入 Qdrant
                                              ↓ 重要性 >= 0.75
                                          同步写入 MEMORY.md
```

## 安装

### 1. 启动 Qdrant

```bash
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### 2. 配置环境变量

创建 `~/.skill-memory/.env`:

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

### 3. 配置 Qoder Hook

编辑 `~/.qoder/settings.json`，添加：

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

### 4. 配置 Hook 行为 (可选)

编辑 `~/.skill-memory/config/hook.toml`:

```toml
[filter]
min_length = 30           # 最小内容长度
max_per_round = 5         # 每轮最多保存条数
skip_patterns = thanks, /help

[memory]
tier = auto               # auto/short/long
promotion_threshold = 0.75  # 晋升到 MEMORY.md 的阈值
```

## CLI 命令

```bash
# 添加记忆
memory add "用户偏好深色主题" --importance 0.8

# 搜索记忆
memory search "代码风格"

# 列出记忆
memory list --tier mid --limit 10

# 导入历史对话
memory import --file transcript.jsonl --tier long

# 查看统计
memory stats
```

## 支持的提供商

| Provider | LLM Model | Embedding |
|----------|-----------|-----------|
| MiniMax | MiniMax-M2.5 | embo-01 |
| OpenAI | gpt-4o-mini | text-embedding-3-small |
| 其他 | OpenAI compatible | OpenAI compatible |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SKILL_MEMORY_API_KEY` | API Key | - |
| `SKILL_MEMORY_LLM_PROVIDER` | LLM 提供商 | minimax |
| `SKILL_MEMORY_QDRANT_HOST` | Qdrant 主机 | localhost |
| `SKILL_MEMORY_QDRANT_PORT` | Qdrant 端口 | 6333 |
| `SKILL_MEMORY_QDRANT_COLLECTION` | Collection 名 | skill_memory |
| `SKILL_MEMORY_DEFAULT_TOP_K` | 搜索返回数量 | 5 |

## 存储结构

```
~/.skill-memory/
├── .env                      # API 配置
├── config/
│   └── hook.toml            # Hook 行为配置
├── hooks/
│   └── mem0_memory_hook.py  # Qoder Hook 脚本
├── knowledge/
│   └── MEMORY.md            # 长期记忆
├── data/                    # 整理状态
└── src/                     # 核心代码
```

## 常见问题

### Q: 记忆没有自动保存？

检查：
1. `~/.qoder/settings.json` 中 Hook 是否配置为 `AgentResponseComplete`
2. Hook 脚本是否有执行权限 (`chmod +x ~/.skill-memory/hooks/mem0_memory_hook.py`)
3. Qdrant 是否运行中

### Q: Qdrant 启动失败？

1. 检查 Docker 是否运行
2. 确认端口 6333 未被占用
3. 或下载 Qdrant 二进制直接运行

---

MIT License
