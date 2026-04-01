---
name: skill-memory
description: Qoder + Mem0 双层记忆系统 - 跨 Workspace AI Agent 持久记忆
version: 2.0.0
---

# Skill Memory

跨 Workspace 的 AI Agent 持久记忆系统。基于 Mem0 + Qdrant 实现语义检索，支持 MiniMax/OpenAI 等 LLM 提供商。

## 工作机制

```
对话发生 → AgentResponseComplete Hook → 提取关键信息 → 存入 Qdrant
                                              ↓ 重要性 >= 0.75
                                          同步写入 MEMORY.md
```

### 触发方式

- **自动触发**：`AgentResponseComplete` 事件（每次 AI 回复后自动触发）
- **手动导入**：`memory import --file transcript.jsonl`

## 核心功能

### 1. 自动记忆保存
- Hook 触发后自动提取对话关键信息
- 计算重要性分数（0.0-1.0）
- 自动分类（preference/project/domain/general）

### 2. 智能检索
- 向量语义搜索（基于文本嵌入）
- 支持 MiniMax/OpenAI Embedding

### 3. 历史导入
- 支持 Qoder transcript.jsonl 格式
- 支持批量导入目录

## 安装

### 1. 启动 Qdrant

```bash
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### 2. 配置环境变量

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

### 3. 配置 Qoder Hook

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

### 4. 配置 Hook 行为

`~/.skill-memory/config/hook.toml`:

```toml
[filter]
min_length = 30           # 最小内容长度
max_per_round = 5        # 每轮最多保存条数
skip_patterns = thanks, /help

[memory]
tier = auto
promotion_threshold = 0.75  # 晋升到 MEMORY.md 的阈值
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

## 存储结构

```
~/.skill-memory/
├── .env                      # API 配置
├── config/hook.toml       # Hook 行为配置
├── hooks/                    # Qoder Hook 脚本
│   └── mem0_memory_hook.py
├── knowledge/               # 长期记忆
│   └── MEMORY.md
└── src/                     # 核心代码
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SKILL_MEMORY_API_KEY` | API Key | - |
| `SKILL_MEMORY_LLM_PROVIDER` | LLM 提供商 | minimax |
| `SKILL_MEMORY_QDRANT_HOST` | Qdrant 主机 | localhost |
| `SKILL_MEMORY_QDRANT_PORT` | Qdrant 端口 | 6333 |
| `SKILL_MEMORY_QDRANT_COLLECTION` | Collection 名 | skill_memory |

## 常见问题

### Q: 记忆没有自动保存？

检查：
1. `~/.qoder/settings.json` 中 Hook 是否配置为 `AgentResponseComplete`
2. `~/.skill-memory/config/hook.toml` 是否有重复 section
3. Hook 脚本是否有执行权限

### Q: Hook 报错 "section 'hook' already exists"？

删除 `~/.skill-memory/config/hook.toml` 并重新创建（确保无重复内容）

### Q: Qdrant 启动失败？

1. 检查 Docker 是否运行
2. 确认端口 6333 未被占用
3. 或下载 Qdrant 二进制直接运行

---

MIT License
