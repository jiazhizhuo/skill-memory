---
name: skill-memory
description: OpenClaw-style 3-tier memory system with hybrid search.记忆分层、语义搜索、混合搜索(MMR+时间衰减)。智能触发、自动回忆、自动保存。跨 worktree 共享。
---

# skill-memory

三层记忆系统，基于 Mem0 + Qdrant 实现，支持跨 worktree 共享。

## 存储架构

```
~/.skill-memory/              ← 固定位置，跨 worktree 共享
├── memory/                   ← 零散记忆（mem0/qdrant）
│   └── memory.db
├── knowledge/               ← 规整后的知识
│   ├── MEMORY.md            ← 长期记忆（可引用）
│   └── domains/             ← 领域知识
│       ├── python.md
│       ├── qoder.md
│       └── project-a.md
└── graph.json               ← 知识图谱（节点+边）
```

## 三层记忆

```
工作记忆 (Working)     → 会话上下文，单次会话
中期记忆 (Mid-term)    → Daily notes 风格，7天过期
长期记忆 (Long-term)  → MEMORY.md 风格，永久存储
```

## 智能触发（自动执行）

### 自动 Search（回忆）

| 触发模式 | 示例 | 行为 |
|---------|------|------|
| 时间参照 | "之前"、"上次"、"记得" | 搜索相关记忆 |
| 偏好询问 | "我之前用什么"、"我的习惯是" | 搜索用户偏好 |
| 会话开始 | 新会话启动 | 加载相关背景 |

### 自动 Save（保存）

| 触发模式 | 示例 | 行为 |
|---------|------|------|
| 明确指令 | "记住"、"以后要记住" | 保存到长期记忆 |
| 偏好表达 | "我喜欢/讨厌"、"通常用" | 保存偏好 |
| 项目配置 | "这个项目用XX" | 保存项目上下文 |

## 命令（显式调用）

```
//memory add <内容> --tier long   添加到长期记忆
//memory search <查询>            混合搜索
//memory list --tier mid          列出中期记忆
//memory long                     查看长期记忆
//memory stats                    查看统计
```

## OpenClaw Agent 集成

定期规整可通过 OpenClaw agent 触发：

```
触发方式：
- OpenClaw Hook: SessionStart/UserPromptSubmit
- 定时任务: cron 或 OpenClaw cron
- 手动触发: //memory organize

规整内容：
- 聚类相似记忆
- 构建领域知识
- 更新 MEMORY.md
- 生成知识图谱
```

## 前置条件

1. Qdrant: `docker run -d -p 6333:6333 qdrant/qdrant`
2. pip install -e .

## 搜索特性

- 向量搜索（语义理解）
- 关键词搜索（精确匹配）
- MMR 重排（多样性）
- 时间衰减（近期优先）

## 触发关键词

**Search：** `之前`、`上次`、`记得`、`我之前`、`我的习惯`
**Save：** `记住`、`以后要`、`我用`、`偏好`、`习惯`
