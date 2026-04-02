# Skill-Memory 开发与测试规范

## 概述

本文档定义了 skill-memory 项目的开发流程、测试规范和质量标准。

## 1. 测试流程规范 (Test Harness)

### 1.1 单元测试清单

每次代码变更后，必须执行以下测试：

```bash
cd ~/.skill-memory

# 1. 环境检查
echo "=== 环境检查 ==="
python3 -c "import os; print('OPENAI_API_KEY:', 'SET' if os.environ.get('OPENAI_API_KEY') else 'NOT SET')"
python3 -c "from qdrant_client import QdrantClient; c = QdrantClient(); print('Qdrant:', c.get_collections())"

# 2. 配置加载测试
echo "=== 配置加载测试 ==="
python3 -c "from src.config import load_config; c = load_config(); print(f'llm: {c.llm_provider}, collection: {c.qdrant_collection}')"

# 3. Mem0 初始化测试
echo "=== Mem0 初始化测试 ==="
python3 -c "from src.mem0_client import Mem0Client; m = Mem0Client(); print('Mem0 init:', m._init_memory())"

# 4. 记忆写入测试
echo "=== 记忆写入测试 ==="
python3 -c "
from src.memory_manager import DualLayerMemoryManager
mm = DualLayerMemoryManager()
r = mm.add_to_mem0('测试记忆', importance=0.8)
print(f'Saved: {r.id}')
"
```

### 1.2 Hook 集成测试

验证 Qoder Hook 端到端流程：

```bash
cd ~/.skill-memory

# 测试 stdin 输入
echo '{"session_id": "test-001", "prompt": "测试 Qoder Hook 功能是否正常工作"}' | \
  python3 hooks/mem0_memory_hook.py --verbose

# 验证数据写入
python3 -c "
from qdrant_client import QdrantClient
client = QdrantClient(host='localhost', port=6333)
info = client.get_collection('skill_memory')
print(f'Points: {info.points_count}')
"
```

### 1.3 测试检查清单

| 检查项 | 预期结果 | 验证方法 |
|--------|----------|----------|
| Qdrant 服务 | 运行中 | `curl http://localhost:6333/` |
| Mem0 初始化 | True | `client._init_memory()` |
| Hook 脚本执行 | Exit 0 | `echo '{"prompt":"test"}' \| python3 hooks/mem0_memory_hook.py` |
| 数据写入 Qdrant | Points > 0 | `client.get_collection('skill_memory').points_count` |
| 数据可检索 | 结果 > 0 | `client.search()` |

## 2. Qoder Hook 配置规范

### 2.1 配置文件位置

| 组件 | 配置文件位置 |
|------|-------------|
| Qoder GUI | `~/Library/Application Support/Qoder/User/settings.json` |
| qodercli | `~/.qoder/settings.json` |

### 2.2 支持的 Hook 事件

| 事件名 | 触发时机 | 推荐用途 |
|--------|----------|----------|
| `UserPromptSubmit` | 用户提交消息时 | 记忆保存 |
| `PreToolUse` | 工具执行前 | 权限检查 |
| `PostToolUse` | 工具执行后 | 结果处理 |
| `Stop` | /stop 命令时 | 会话总结 |

### 2.3 正确配置示例

```json
{
  "hooks": {
    "UserPromptSubmit": [
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

## 3. 环境变量规范

### 3.1 必需的环境变量

| 变量名 | 用途 | 来源 |
|--------|------|------|
| `OPENAI_API_KEY` | Mem0 内部认证 | `.env` |
| `SKILL_MEMORY_API_KEY` | MiniMax API | `.env` |
| `SKILL_MEMORY_QDRANT_HOST` | Qdrant 地址 | `.env` |

### 3.2 .env 文件模板

```bash
# skill-memory Configuration

# API Keys
OPENAI_API_KEY=your_key_here
SKILL_MEMORY_API_KEY=your_key_here
MINIMAX_API_KEY=your_key_here

# Provider
LLM_PROVIDER=minimax
EMBEDDING_PROVIDER=minimax

# MiniMax
MINIMAX_LLM_BASE_URL=https://api.minimaxi.com/v1
SKILL_MEMORY_MINIMAX_LLM_MODEL=MiniMax-M2.5
SKILL_MEMORY_MINIMAX_EMBEDDING_MODEL=embo-01

# Qdrant
SKILL_MEMORY_QDRANT_HOST=localhost
SKILL_MEMORY_QDRANT_PORT=6333
SKILL_MEMORY_QDRANT_COLLECTION=skill_memory
```

## 4. 故障排查指南

### 4.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| Hook 未触发 | 配置位置错误 | 检查 `User/settings.json` |
| 事件名无效 | 使用了错误的事件名 | 使用 `UserPromptSubmit` |
| Mem0 初始化失败 | 缺少 `OPENAI_API_KEY` | 添加到 `.env` |
| Qdrant 无数据 | 集合未创建 | 重启 Qdrant + 重新添加数据 |

### 4.2 诊断命令

```bash
# 检查 Qdrant 状态
curl http://localhost:6333/

# 检查集合
curl http://localhost:6333/collections

# 检查 Qdrant 进程
ps aux | grep qdrant

# 重启 Qdrant
pkill -f qdrant && ~/bin/qdrant &
```

## 5. CI/CD 集成

### 5.1 Pre-commit Hook

```bash
#!/bin/bash
# ~/.git/hooks/pre-commit

cd ~/.skill-memory

# 运行测试
python3 -c "from src.mem0_client import Mem0Client; assert Mem0Client()._init_memory()"

echo "Tests passed"
```

### 5.2 验证脚本

```bash
#!/bin/bash
# verify.sh - 发布前验证

set -e

cd ~/.skill-memory

echo "Running verification..."

# 1. 环境检查
python3 -c "from src.config import load_config; print('Config OK')"

# 2. Mem0 测试
python3 -c "from src.mem0_client import Mem0Client; m = Mem0Client(); assert m._init_memory(), 'Mem0 init failed'"

# 3. Hook 测试
echo '{"prompt": "test"}' | python3 hooks/mem0_memory_hook.py > /dev/null

echo "All checks passed!"
```

## 6. 版本发布检查清单

- [ ] 所有单元测试通过
- [ ] Hook 集成测试通过
- [ ] Qdrant 数据持久化验证
- [ ] 跨工作区共享验证
- [ ] 文档更新完成
- [ ] CHANGELOG.md 更新

---

本文档遵循 [Harness 最佳实践](./HARNESS_PRACTICE.md)
