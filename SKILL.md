---
name: skill-memory
description: Qoder + Mem0 双层记忆系统 - 让 AI Agent 拥有持久记忆
version: 1.0.0
---

# Skill Memory - 双层记忆系统

> **开发规范**: [docs/AGENTS.md](docs/AGENTS.md)

## 概述

Skill Memory 是一个为 AI Agent 设计的外挂记忆系统，采用双层架构：

- **第一层**: Mem0 + Qdrant（高速向量检索）
- **第二层**: MEMORY.md（持久 Markdown 备份）

> 详细架构见 [README.md](README.md)，开发规范见 [docs/AGENTS.md](docs/AGENTS.md)

## 核心功能

### 1. 自动记忆保存
- 在 `/stop` 命令执行时自动触发
- 提取对话中的关键信息
- 自动计算重要性并分类

### 2. 智能检索
- 向量语义搜索
- 关键词精确匹配
- MMR 重排（结果多样性）
- 时间衰减（近期优先）

### 3. 历史导入
支持导入多种格式的对话记录：
- Qoder transcript.jsonl
- OpenClaw transcript.jsonl

## 安装

### 方式一：pip 安装（推荐）

```bash
cd ~/.skill-memory
pip install -e .  # 安装 CLI 命令 memory
```

### 方式二：pip 安装到指定目录

```bash
pip install -e ~/.skill-memory
```

### 方式三：手动安装

1. 确保 Python 3.9+ 已安装
2. 安装依赖：`pip install python-dotenv requests`
3. （可选）启动 Qdrant：
   ```bash
   ~/bin/qdrant &
   ```
4. 配置环境变量（参考 `.env.example`）

## 配置

### CLI 命令

安装后，`memory` 命令全局可用：

```bash
# 搜索记忆
memory search "今天的话题"

# 列出近期记忆
memory list --limit 20

# 查看长期记忆
memory long

# 查看统计
memory stats
```

### 跨平台配置（v1.1 新增）

skill-memory 支持三个平台：

| 平台 | 配置位置 | 触发方式 |
|------|---------|---------|
| **qodercli** | `~/.qoder/hooks.yaml` | stdin JSON |
| **qoder GUI** | `~/Library/Application Support/Qoder/User/settings.json` | Hook 脚本 |
| **openclaw** | 直接调用或 API | Python API / HTTP |

#### qodercli 配置

```yaml
# ~/.qoder/hooks.yaml
hooks:
  user-prompt-submit:
    command: "python3 ~/.skill-memory/hooks/unified_hook.py"
```

#### Qoder GUI 配置

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

#### OpenClaw 集成

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path.home() / ".skill-memory" / "src"))

from platforms import get_adapter, PlatformType
from memory_manager import DualLayerMemoryManager
from config import load_config

# 初始化
config = load_config()
manager = DualLayerMemoryManager(config)

# 添加记忆
manager.smart_add("重要内容", importance=0.8)
```

### 环境变量

```bash
# ~/.skill-memory/.env

# Qdrant
SKILL_MEMORY_QDRANT_HOST=localhost
SKILL_MEMORY_QDRANT_PORT=6333
SKILL_MEMORY_QDRANT_COLLECTION=qoder_memory

# LLM/Embedding
SKILL_MEMORY_LLM_PROVIDER=openai
SKILL_MEMORY_API_KEY=your_key_here

# 搜索参数
SKILL_MEMORY_VECTOR_WEIGHT=0.7
SKILL_MEMORY_KEYWORD_WEIGHT=0.3
SKILL_MEMORY_PROMOTION_THRESHOLD=0.8
```

## 使用

### CLI 命令

```bash
# 添加记忆
memory add "用户偏好深色主题" --importance 0.8

# 搜索记忆
memory search "代码风格偏好"

# 列出记忆
memory list --tier mid --limit 20

# 导入历史对话
memory import --file ~/.qoder/sessions/xxx/transcript.jsonl
memory import --dir ~/old-conversations/

# 查看长期记忆
memory long

# 查看统计
memory stats

# 备份 MEMORY.md
memory backup
```

### 自动记忆

配置 Hook 后，每次执行 `/stop` 命令时：
1. 自动解析对话记录
2. 提取关键信息
3. 计算重要性
4. 保存到双层记忆

## 存储结构

```
~/.skill-memory/
├── memory/                   # Mem0 数据
│   └── memory.db
├── knowledge/                 # 知识文件
│   ├── MEMORY.md             # 长期记忆主文件
│   ├── preferences.md        # 用户偏好
│   ├── projects/             # 项目知识
│   └── domains/              # 领域知识
├── hooks/                    # Hook 脚本
│   ├── unified_hook.py       # 跨平台统一入口（推荐）
│   └── mem0_memory_hook.py   # 旧版（兼容）
└── scripts/                  # 辅助脚本
    └── install.sh
```

## 导入历史对话

### Qoder 格式

```bash
memory import --file ~/.qoder/sessions/session-123/transcript.jsonl --tier long
```

### OpenClaw 格式

```bash
memory import --file ~/openclaw/transcripts/session-456.jsonl --tier long
```

### 批量导入

```bash
memory import --dir ~/.qoder/sessions/ --tier mid
```

## 常见问题

### Q: 记忆没有自动保存？

检查：
1. Qoder Hooks 是否正确配置
2. Hook 脚本是否有执行权限
3. 查看 Qoder 日志

### Q: 搜索结果不准确？

尝试：
1. 调整 `SKILL_MEMORY_VECTOR_WEIGHT`
2. 增加搜索结果的 `limit`
3. 使用更具体的查询词

### Q: Qdrant 启动失败？

1. 检查 Docker 是否运行
2. 确认端口 6333/6334 未被占用
3. 查看 Docker 日志：`docker logs qdrant`

## 许可证

MIT License
