# Skill Memory

Qoder + Mem0 双层记忆系统 - 让 AI Agent 拥有持久记忆

## 功能特性

- **双层记忆架构**: Mem0 向量检索 + MEMORY.md 持久备份
- **自动保存**: 在 `/stop` 时自动提取关键信息
- **智能分类**: 自动识别偏好、项目、领域等类别
- **历史导入**: 支持 Qoder 和 OpenClaw 格式
- **语义搜索**: 向量 + 关键词混合搜索

## 快速开始

### 1. 安装

```bash
cd ~/.skill-memory
./scripts/install.sh
# 全程按回车即可完成安装
```

### 2. 配置

编辑 `~/.skill-memory/.env` 填入 API Key：

```bash
SKILL_MEMORY_API_KEY=your_key_here
SKILL_MEMORY_QDRANT_HOST=localhost
SKILL_MEMORY_QDRANT_PORT=6333
```

### 3. 使用

```bash
# 添加记忆
memory add "用户偏好深色主题"

# 搜索记忆
memory search "代码风格偏好"

# 导入历史对话
memory import --file transcript.jsonl

# 查看统计
memory stats
```

## 架构

### 双层存储架构

```
┌─────────────────────────────────────────────────────────────┐
│  第一层：Mem0 + Qdrant（高速检索）                          │
│  • 向量语义搜索                                             │
│  • 混合搜索（向量 + 关键词 + MMR + 时间衰减）                 │
│  • 7 天 TTL 自动过期                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                    [重要性 >= 0.8 自动晋升]
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  第二层：MEMORY.md（持久备份）                               │
│  • Markdown 纯文本，永久存储                                 │
│  • 自动分类（preferences/ projects/ domains/）              │
│  • 支持版本控制                                              │
└─────────────────────────────────────────────────────────────┘
```

### 跨平台架构（v1.1）

```
┌─────────────────────────────────────────────────────────────┐
│                    平台适配层 (Adapters)                      │
├──────────────┬──────────────┬───────────────────────────────┤
│   qodercli   │  qoder GUI   │         openclaw              │
│  (hooks.yaml)│ (settings.json)    (transcript.jsonl)        │
└──────────────┴──────────────┴───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              跨平台记忆核心 (Memory Core)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Platform   │  │   Storage   │  │     Triggers        │  │
│  │  Detector   │  │  (Mem0+MD)  │  │  (stdin/file/api)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

支持平台：
- **qodercli**: 通过 `hooks.yaml` 配置，stdin 触发
- **qoder GUI**: 通过 `settings.json` Hook 触发
- **openclaw**: 直接调用 Python API 或 HTTP API

## 目录结构

```
~/.skill-memory/
├── src/                    # 核心代码
│   ├── platforms/         # 平台适配层
│   ├── triggers/          # 触发机制
│   ├── config.py          # 配置管理
│   ├── mem0_client.py     # Mem0 客户端
│   ├── memory_manager.py  # 双层记忆管理器
│   ├── transcript_parser.py
│   └── cli.py
├── hooks/                 # Hook 脚本
│   ├── unified_hook.py    # 跨平台入口（推荐）
│   └── mem0_memory_hook.py # 旧版（兼容）
├── scripts/
│   └── install.sh         # 安装脚本
└── knowledge/
    └── MEMORY.md          # 长期记忆
```

## 许可证

MIT
