# Skill-Memory 开发规范

> 开发 skill-memory 时参考本文档

## 0. 开发与部署分离

**重要**：开发目录和部署目录分开，避免开发时影响正在使用的 skill。

### 目录分离

| 目录 | 用途 | 内容 |
|------|------|------|
| `~/git/skill-memory` | 开发目录 | git 仓库、代码、文档、测试 |
| `~/.skill-memory` | 部署目录 | 运行时代码、配置、数据 |

### 开发流程

```bash
# 1. 在开发目录修改代码
cd ~/git/skill-memory
# ... 修改代码 ...

# 2. 测试（可选）
python3 -m pytest tests/

# 3. 部署到本地
./scripts/deploy.sh

# 4. 提交到 git
git add . && git commit -m "描述"
git push
```

### 部署脚本

```bash
# 从开发目录同步代码到部署目录
./scripts/deploy.sh

# 或指定目录
SKILL_MEMORY_DEV=~/git/skill-memory \
SKILL_MEMORY_DEPLOY=~/.skill-memory \
./scripts/deploy.sh
```

### 部署目录内容

部署目录只包含运行时需要的文件：

```
~/.skill-memory/
├── .env              # 配置（不进入 git）
├── knowledge/        # 知识库（不进入 git）
├── memory/           # Mem0 数据（不进入 git）
├── data/             # 数据文件（不进入 git）
├── src/              # 代码（从开发目录同步）
├── hooks/            # Hook 脚本（从开发目录同步）
├── scripts/          # 脚本（从开发目录同步）
├── config/           # 配置（从开发目录同步）
├── pyproject.toml    # Python 配置（从开发目录同步）
├── SKILL.md          # 技能配置（从开发目录同步）
└── README.md         # 文档（从开发目录同步）
```

**注意**：
- 部署目录不包含 `.git`、`docs/`、`TESTING.md` 等开发文件
- 用户数据目录（`knowledge/`、`memory/`、`data/`、`.env`）**永不覆盖**

### 用户数据保护

**重要**：以下目录是用户数据，部署时不会覆盖：

| 目录/文件 | 内容 | 保护措施 |
|-----------|------|----------|
| `knowledge/*.md` | MEMORY.md 等记忆数据 | 不提交 git，部署不覆盖 |
| `memory/` | Mem0/Qdrant 数据 | 不提交 git，部署不覆盖 |
| `data/` | 其他运行时数据 | 不提交 git，部署不覆盖 |
| `.env` | API Key 等配置 | 不提交 git，部署不覆盖 |

**开发目录不应该包含用户数据**：
```bash
# 清理开发目录中的用户数据
cd ~/git/skill-memory
rm -rf knowledge/*.md memory/ data/ .env
```

## 1. 项目结构

```
skill-memory/
├── SKILL.md          # 技能配置（Qoder/OpenClaw 读取）
├── README.md         # 用户文档（安装、使用、架构）
├── docs/
│   ├── AGENTS.md    # 开发规范（本文件）
│   └── TESTING.md   # 测试规范
├── src/              # Python 代码
│   ├── platforms/   # 平台抽象层（跨平台支持）
│   ├── triggers/    # 触发机制（跨平台支持）
│   ├── config.py
│   ├── memory_manager.py
│   └── cli.py
├── hooks/           # Qoder Hook 脚本
│   ├── unified_hook.py    # 跨平台统一入口（推荐）
│   └── mem0_memory_hook.py # 旧版 hook（兼容）
└── knowledge/        # 知识库文件
```

## 2. 文档规范

### 各文件用途

| 文件 | 用途 | 读者 | 内容 |
|------|------|------|------|
| `SKILL.md` | 技能配置 | Qoder/OpenClaw | frontmatter + 简介 + 安装 + 基本使用 |
| `README.md` | 用户文档 | 用户 | 安装、配置、架构、使用、FAQ |
| `docs/AGENTS.md` | 开发规范 | 开发者 | 项目结构、开发规范、测试清单 |
| `docs/TESTING.md` | 测试规范 | 开发者 | 测试流程、检查清单 |

### 内容分配原则

- **架构图** → `README.md`
- **安装配置** → `README.md` 和 `SKILL.md` 都可（SKILL.md 精简版）
- **开发规范** → `docs/AGENTS.md`
- **API 文档** → `docs/` 或代码注释
- **用户使用指南** → `README.md`

### SKILL.md 规范

SKILL.md 是给 AI 读取的技能配置，应保持精简：

```markdown
---
name: skill-memory
description: 简短描述
version: 1.0.0
---

# 标题

## 概述（2-3 句）

## 安装（精简）

## 基本使用（3-5 个命令）

## 配置（精简）
```

**不要在 SKILL.md 中写**：
- 详细架构图
- 完整 API 文档
- 开发规范
- 测试说明

## 2. pyproject.toml 规范

### Python 版本
```toml
requires-python = ">=3.9"  # 不要写 >=3.10
```

### Entry Points
```toml
[project.scripts]
memory = "src.cli:main"  # 注意：是 src.cli 不是 cli
```

### 包结构
```toml
[tool.hatch.build.targets.wheel]
packages = ["src"]
```

## 3. CLI 开发规范

### cli.py 导入路径

```python
# 添加 src 到路径（支持 pip 安装和直接运行）
_cli_dir = Path(__file__).parent
for _path in [
    _cli_dir,  # pip 安装后
    _cli_dir.parent,  # 直接运行 src/cli.py
]:
    if (_path / "config.py").exists():
        sys.path.insert(0, str(_path))
        break
```

### CLI 命令格式

```bash
memory add <content> [--importance 0.5]
memory search <query> [--limit 5]
memory list [--limit 20]
memory long
memory stats
memory import --file <path>
```

## 4. Hook 脚本规范

### 支持的事件

| 事件名 | 说明 |
|--------|------|
| `UserPromptSubmit` | 用户提交消息时（推荐） |
| `Stop` | /stop 命令时 |

### stdin 数据格式

Qoder Hook 通过 stdin 传递 JSON：
```json
{
  "session_id": "xxx",
  "prompt": "用户消息"
}
```

### 配置位置

**必须配置两个位置**：

1. `~/.qoder/settings.json` (qodercli)
2. `~/Library/Application Support/Qoder/User/settings.json` (Qoder GUI)

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

## 5. 常见错误

### memory 命令找不到

原因：`pip install -e .` 未执行或 entry_points 路径错误

解决：
```bash
cd ~/.skill-memory
python3 -m pip install -e .
```

### Hook 未触发

检查：
1. 配置文件路径是否正确
2. 事件名是否为 `UserPromptSubmit`（不是 `AgentResponseComplete`）

### Mem0 初始化失败

原因：缺少 `OPENAI_API_KEY`

解决：在 `.env` 中添加：
```bash
OPENAI_API_KEY=your_key_here
```

## 6. 测试检查清单

修改后必须验证：

- [ ] `memory --help` 正常工作
- [ ] `memory search <query>` 能返回结果
- [ ] Hook 脚本能通过 stdin 接收数据
- [ ] Qdrant 中有数据写入

## 7. 安装与发布

### 本地安装
```bash
cd ~/.skill-memory
python3 -m pip install -e .
```

### 验证安装
```bash
memory --help
memory stats
```

## 8. 跨平台开发规范（v1.1 新增）

### 平台抽象层

所有平台相关代码都在 `src/platforms/` 目录：

```
src/platforms/
├── __init__.py      # 导出接口
├── base.py          # PlatformAdapter 基类 + MemoryEvent
└── detector.py      # 自动检测平台
```

### 新增平台适配器

1. 在 `src/platform/base.py` 中继承 `PlatformAdapter`：

```python
class NewPlatformAdapter(PlatformAdapter):
    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.NEW_PLATFORM
    
    @property
    def name(self) -> str:
        return "new_platform"
    
    def get_session_id(self) -> Optional[str]:
        # 实现获取 session_id 逻辑
        pass
    
    def get_transcript_path(self) -> Optional[Path]:
        # 实现获取 transcript 路径逻辑
        pass
    
    def parse_input(self, input_data: Any) -> List[MemoryEvent]:
        # 实现解析输入数据逻辑
        pass
```

2. 在 `PlatformType` 枚举中添加新类型

3. 在 `detector.py` 中添加检测逻辑

### 触发机制

所有触发器在 `src/triggers/` 目录：

```
src/triggers/
├── __init__.py
└── base.py    # StdinTrigger, FileWatcherTrigger, APITrigger
```

### 统一 Hook 入口

使用 `hooks/unified_hook.py` 作为统一入口：

```bash
# 自动检测平台
python unified_hook.py --verbose

# 指定平台
python unified_hook.py --platform qodercli
python unified_hook.py --platform openclaw
```

### 平台检测优先级

1. 环境变量 `SKILL_MEMORY_PLATFORM`
2. `QODER_SESSION_ID` 环境变量 → qodercli
3. `OPENCLAW_SESSION_ID` 环境变量 → openclaw
4. stdin 非空 → 默认 qodercli
5. 未知平台
