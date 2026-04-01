---
name: skill-memory
description: AI Agent 持久记忆系统，支持语义检索和分层存储。当用户提到"记住"、"之前"、"我的偏好"、"项目背景"时使用。
---

# Skill Memory

跨应用的 AI Agent 持久记忆系统，支持向量语义检索和分层存储。

## 使用场景

- 用户说"记住 XXX"或"以后要记住"
- 用户问"之前我们聊过什么"、"我之前说过"
- 需要回忆项目背景、用户偏好、技术栈
- 用户表达喜欢/讨厌、习惯/倾向

## 核心能力

| 能力 | 说明 |
|------|------|
| **自动保存** | Hook 触发后自动提取对话关键信息 |
| **语义检索** | 基于向量嵌入的语义搜索 |
| **分层存储** | Working → Mid → Long 三层记忆 |
| **重要性分级** | 自动计算重要性分数 (0.0-1.0) |
| **多源支持** | Mem0 (向量) + MEMORY.md (文本) |

## 基本用法

```bash
# 添加记忆
memory add "用户偏好深色主题" --importance 0.8

# 搜索记忆
memory search "代码风格"

# 列出记忆
memory list --tier mid --limit 10

# 查看统计
memory stats
```

## 搜索限制

为避免上下文负担：
- 默认返回 **top_k=5** 条最相关结果
- 低于相似度阈值的结果不返回
- 可通过 `--limit` 参数调整

## 安装

详细安装步骤见 [README.md](README.md)。

快速步骤：
1. 启动 Qdrant: `docker run -d -p 6333:6333 qdrant/qdrant`
2. 配置 `~/.skill-memory/.env`
3. 配置 Qoder hooks（见 README.md）
