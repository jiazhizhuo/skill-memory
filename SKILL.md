---
name: skill-memory
description: OpenClaw-style 3-tier memory system with hybrid search.记忆分层、工作记忆、中期记忆、长期记忆、语义搜索、混合搜索(MMR+时间衰减)。
---

# skill-memory

OpenClaw 风格的三层记忆系统，基于 Mem0 + Qdrant 实现。

## 架构

```
工作记忆 (Working)     → 会话上下文，单次会话
中期记忆 (Mid-term)    → Daily notes 风格，7天过期
长期记忆 (Long-term)  → MEMORY.md 风格，永久存储
```

## 命令

| 命令 | 说明 |
|------|------|
| `//memory add <内容>` | 添加记忆（默认中期） |
| `//memory add <内容> --tier long` | 添加到长期记忆 |
| `//memory search <查询>` | 混合搜索 |
| `//memory list` | 列出所有记忆 |
| `//memory today` | 查看今日记忆 |
| `//memory long` | 查看长期记忆 |
| `//memory stats` | 查看统计 |
| `//memory delete <id>` | 删除记忆 |

## 前置条件

1. Qdrant: `docker run -d -p 6333:6333 qdrant/qdrant`
2. pip install -e .

## 搜索特性

- 向量搜索（语义理解）
- 关键词搜索（精确匹配）
- MMR 重排（多样性）
- 时间衰减（近期优先）
