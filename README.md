# Skill Memory

为 AI Agent 提供持久记忆能力的 Skill，支持跨会话记忆检索和自动保存。

## 核心能力

- **记忆检索**：语义搜索历史对话、用户偏好、项目上下文
- **自动保存**：通过 Hook 自动提取并保存有价值的信息
- **双层存储**：Mem0 向量检索 + MEMORY.md 持久备份
- **跨平台**：支持 qodercli、Qoder GUI、OpenClaw

## 快速开始

### 方式一：一键部署（推荐）

```bash
# 克隆到开发目录
git clone https://github.com/jiazhizhuo/skill-memory.git ~/git/skill-memory

# 一键部署
~/git/skill-memory/scripts/deploy.sh
```

部署脚本会自动：
- 同步代码到 `~/.skill-memory`
- 配置 Qoder/QoderCLI Hook
- 创建 Skill 符号链接
- 保护现有用户数据

### 方式二：手动安装

```bash
# 克隆并部署
git clone https://github.com/jiazhizhuo/skill-memory.git ~/.skill-memory
cd ~/.skill-memory

# 安装依赖
pip install -e .

# 配置 .env
cp .env.example .env
# 编辑 .env 填入 API Key
```

## 配置

### 环境变量

```bash
# ~/.skill-memory/.env

# Qdrant 向量数据库
SKILL_MEMORY_QDRANT_HOST=localhost
SKILL_MEMORY_QDRANT_PORT=6333
SKILL_MEMORY_QDRANT_COLLECTION=skill_memory

# LLM/Embedding Provider
SKILL_MEMORY_LLM_PROVIDER=openai
SKILL_MEMORY_API_KEY=your_key_here

# 搜索参数
SKILL_MEMORY_VECTOR_WEIGHT=0.7
SKILL_MEMORY_KEYWORD_WEIGHT=0.3
SKILL_MEMORY_PROMOTION_THRESHOLD=0.8
```

### Hook 配置

部署脚本会自动配置。如需手动配置：

**qodercli** (`~/.qoder/hooks.yaml`):
```yaml
hooks:
  user-prompt-submit:
    command: "python3 ~/.skill-memory/hooks/unified_hook.py"
```

**Qoder GUI** (`~/Library/Application Support/Qoder/User/settings.json`):
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.skill-memory/hooks/unified_hook.py"
          }
        ]
      }
    ]
  }
}
```

## 使用

### CLI 命令

```bash
# 搜索记忆
memory search "用户的代码风格偏好"

# 添加记忆
memory add "重要决策：使用 PostgreSQL 作为主数据库" --importance 0.8

# 查看统计
memory stats

# 查看长期记忆
memory long

# 导入历史对话
memory import --file ~/.qoder/projects/-Users-jzz-git/session.jsonl
```

### 自动记忆

配置 Hook 后，用户发送消息时会自动：
1. 提取对话中的关键信息
2. 计算重要性分数
3. 保存到双层存储

## 架构

### 双层存储

```
┌─────────────────────────────────────────────────────────────┐
│  第一层：Mem0 + Qdrant（高速检索）                          │
│  • 向量语义搜索                                             │
│  • 7 天 TTL 自动过期                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                    [重要性 >= 0.8 自动晋升]
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  第二层：MEMORY.md（持久备份）                               │
│  • Markdown 纯文本，永久存储                                 │
│  • 支持版本控制                                              │
└─────────────────────────────────────────────────────────────┘
```

### 跨平台架构

```
┌─────────────────────────────────────────────────────────────┐
│                    平台适配层 (Adapters)                      │
├──────────────┬──────────────┬───────────────────────────────┤
│   qodercli   │  qoder GUI   │         openclaw              │
│  (hooks.yaml)│ (settings.json)    (API/文件监控)             │
└──────────────┴──────────────┴───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              跨平台记忆核心 (Memory Core)                      │
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
~/.skill-memory/           # 部署目录
├── .env                   # 配置（不提交 git）
├── knowledge/             # 记忆数据（不提交 git）
│   └── MEMORY.md
├── memory/                # Mem0 数据（不提交 git）
├── data/                  # 运行时数据（不提交 git）
├── src/                   # 核心代码
│   ├── platforms/        # 平台适配
│   ├── triggers/         # 触发机制
│   └── ...
├── hooks/                 # Hook 脚本
└── scripts/               # 辅助脚本
```

## 开发

开发规范见 [docs/AGENTS.md](docs/AGENTS.md)

```bash
# 开发目录
~/git/skill-memory

# 部署
./scripts/deploy.sh

# 提交
git add . && git commit -m "描述"
git push
```

## 许可证

MIT
