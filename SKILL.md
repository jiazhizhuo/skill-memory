---
name: skill-memory
description: 为 Agent 提供持久记忆能力。当需要查询历史对话信息、用户偏好、项目上下文时调用。支持记忆搜索、添加、导入历史对话。
---

# Skill Memory

为 Agent 提供跨会话的持久记忆能力，解决"每次对话都要重新了解用户"的问题。

## 适用场景

- 用户问"之前讨论过什么..."、"记得我们说过..."
- 需要 了解用户偏好、习惯、项目背景
- 用户要求"记住这个"、"下次记得"
- 需要查询历史对话中的决策、配置、约定

## 使用方法

### 1. 搜索记忆

```bash
memory search "关键词或自然语言描述"
```

示例：
```bash
memory search "用户的代码风格偏好"
memory search "上次讨论的数据库配置"
memory search "用户对测试的态度"
```

### 2. 查看记忆统计

```bash
memory stats
```

### 3. 添加记忆

```bash
memory add "内容" --importance 0.8
```

### 4. 查看长期记忆

```bash
memory long
```

### 5. 导入历史对话

```bash
memory import --file /path/to/transcript.jsonl
```

## 自动记忆

当用户发送消息时，系统会自动保存有价值的信息（决策、偏好、项目信息等），无需手动操作。

## 注意事项

- 记忆是跨会话共享的，添加有价值的信息会帮助未来的对话
- 使用自然语言搜索即可，系统会进行语义匹配
- 敏感信息（密码、密钥等）不应添加到记忆中

## 技术细节

- 存储位置：`~/.skill-memory/`
- 向量搜索：Mem0 + Qdrant
- 持久备份：`knowledge/MEMORY.md`
- 开发规范：`docs/AGENTS.md`
