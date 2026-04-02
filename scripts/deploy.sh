#!/bin/bash
# Skill Memory 部署脚本
# 从开发目录同步代码到部署目录，并配置 Qoder/QoderCLI 集成
#
# 重要：用户数据保护
# - knowledge/  (MEMORY.md 等) - 不覆盖
# - memory/     (Mem0 数据)    - 不覆盖
# - data/       (其他数据)     - 不覆盖
# - .env        (配置文件)     - 不覆盖

set -e

# 目录配置
DEV_DIR="${SKILL_MEMORY_DEV:-$HOME/git/skill-memory}"
DEPLOY_DIR="${SKILL_MEMORY_DEPLOY:-$HOME/.skill-memory}"
QODER_CLI_SETTINGS="$HOME/.qoder/settings.json"
QODER_GUI_SETTINGS="$HOME/Library/Application Support/Qoder/User/settings.json"
QODER_SKILLS_DIR="$HOME/.qoder/skills"

# 用户数据目录（永不覆盖）
USER_DATA_DIRS=(
    "knowledge"
    "memory"
    "data"
)
USER_DATA_FILES=(
    ".env"
)

echo "=== Skill Memory 部署 ==="
echo "开发目录: $DEV_DIR"
echo "部署目录: $DEPLOY_DIR"
echo ""

# ============================================
# 步骤 1: 检查用户数据
# ============================================

echo "[1/6] 检查用户数据..."
for dir in "${USER_DATA_DIRS[@]}"; do
    if [ -d "$DEPLOY_DIR/$dir" ]; then
        file_count=$(find "$DEPLOY_DIR/$dir" -type f 2>/dev/null | wc -l | tr -d ' ')
        if [ "$file_count" -gt 0 ]; then
            echo "  保护: $dir/ ($file_count 文件)"
        fi
    fi
done
for file in "${USER_DATA_FILES[@]}"; do
    if [ -f "$DEPLOY_DIR/$file" ]; then
        echo "  保护: $file"
    fi
done

# ============================================
# 步骤 2: 同步代码
# ============================================

# 检查开发目录
if [ ! -d "$DEV_DIR/.git" ]; then
    echo "错误: 开发目录不存在或不是 git 仓库: $DEV_DIR"
    exit 1
fi

# 创建部署目录（如果不存在）
mkdir -p "$DEPLOY_DIR"

# 需要同步的目录/文件（仅功能代码，不包含用户数据）
SYNC_ITEMS=(
    "src"
    "hooks"
    "scripts"
    "config"
    "pyproject.toml"
    "install.sh"
    "SKILL.md"
    "README.md"
)

# 需要排除的文件
EXCLUDE_PATTERNS=(
    ".git"
    ".env"
    "__pycache__"
    "*.pyc"
    ".pytest_cache"
    "*.egg-info"
    "docs"
    "tests"
    "TESTING.md"
    "knowledge"
    "memory"
    "data"
)

# 构建 rsync 排除参数
EXCLUDE_ARGS=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude=$pattern"
done

echo ""
echo "[2/6] 同步代码..."
for item in "${SYNC_ITEMS[@]}"; do
    if [ -e "$DEV_DIR/$item" ]; then
        echo "  $item"
        rsync -av --delete $EXCLUDE_ARGS "$DEV_DIR/$item" "$DEPLOY_DIR/" 2>/dev/null | grep -v "/$" | tail -1
    fi
done

# 复制 .env.example（如果部署目录没有 .env）
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    if [ -f "$DEV_DIR/.env.example" ]; then
        echo "  创建 .env (从 .env.example)"
        cp "$DEV_DIR/.env.example" "$DEPLOY_DIR/.env"
    fi
fi

# 创建必要的运行时目录（不覆盖现有数据）
echo ""
echo "[3/6] 创建运行时目录..."
for dir in "${USER_DATA_DIRS[@]}"; do
    if [ ! -d "$DEPLOY_DIR/$dir" ]; then
        mkdir -p "$DEPLOY_DIR/$dir"
        echo "  创建: $dir/"
    fi
done

# ============================================
# 步骤 4: 安装 Python 包
# ============================================

echo ""
echo "[4/6] 安装 Python 包..."
if command -v pip3 &> /dev/null; then
    cd "$DEPLOY_DIR"
    pip3 install -e . --quiet 2>/dev/null || echo "  警告: pip install 失败，请手动安装"
    echo "  完成"
else
    echo "  跳过 (pip3 不可用)"
fi

# ============================================
# 步骤 5: 配置 Qoder CLI Hook
# ============================================

echo ""
echo "[5/6] 配置 Qoder CLI Hook..."

configure_hook() {
    local settings_file="$1"
    local platform_name="$2"
    
    if [ ! -f "$settings_file" ]; then
        echo "  $platform_name: 配置文件不存在，创建新文件"
        mkdir -p "$(dirname "$settings_file")"
        echo '{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"~/.skill-memory/hooks/unified_hook.py"}]}]}}' > "$settings_file"
        return
    fi
    
    # 使用 Python 更新配置
    python3 << PYTHON_SCRIPT
import json
import sys

settings_file = "$settings_file"
hook_command = "$DEPLOY_DIR/hooks/unified_hook.py"

try:
    with open(settings_file, 'r') as f:
        data = json.load(f)
except:
    data = {}

# 确保 hooks 结构存在
if 'hooks' not in data:
    data['hooks'] = {}
if 'UserPromptSubmit' not in data['hooks']:
    data['hooks']['UserPromptSubmit'] = [{'hooks': []}]

# 更新 hook 命令
hook_found = False
for hook_group in data['hooks']['UserPromptSubmit']:
    if 'hooks' in hook_group:
        for hook in hook_group['hooks']:
            if 'command' in hook and 'skill-memory' in hook.get('command', ''):
                hook['command'] = hook_command
                hook_found = True
                break

if not hook_found:
    # 添加新的 hook
    if not data['hooks']['UserPromptSubmit']:
        data['hooks']['UserPromptSubmit'] = [{'hooks': []}]
    data['hooks']['UserPromptSubmit'][0]['hooks'].append({
        'type': 'command',
        'command': hook_command
    })

with open(settings_file, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"  {settings_file}")
PYTHON_SCRIPT
}

configure_hook "$QODER_CLI_SETTINGS" "qodercli"

# ============================================
# 步骤 6: 配置 Qoder GUI Hook
# ============================================

echo ""
echo "[6/6] 配置 Qoder GUI Hook..."
configure_hook "$QODER_GUI_SETTINGS" "qoder GUI"

# ============================================
# 步骤 7: 配置 Skill 符号链接
# ============================================

echo ""
echo "配置 Skill 符号链接..."

mkdir -p "$QODER_SKILLS_DIR"
SKILL_LINK="$QODER_SKILLS_DIR/skill-memory"

if [ -L "$SKILL_LINK" ]; then
    rm "$SKILL_LINK"
elif [ -d "$SKILL_LINK" ]; then
    rm -rf "$SKILL_LINK"
fi

ln -s "$DEPLOY_DIR" "$SKILL_LINK"
echo "  $SKILL_LINK -> $DEPLOY_DIR"

# ============================================
# 完成
# ============================================

echo ""
echo "=========================================="
echo "       部署完成"
echo "=========================================="
echo ""
echo "已配置:"
echo "  ✓ 代码同步到 $DEPLOY_DIR"
echo "  ✓ Qoder CLI Hook: unified_hook.py"
echo "  ✓ Qoder GUI Hook: unified_hook.py"
echo "  ✓ Skill 符号链接: skill-memory"
echo ""
echo "用户数据保护（未覆盖）:"
echo "  ✓ knowledge/ - 记忆数据"
echo "  ✓ memory/    - Mem0 数据"
echo "  ✓ data/      - 其他数据"
echo "  ✓ .env       - 配置文件"
echo ""
echo "验证部署:"
echo "  memory stats"
echo ""
echo "手动配置（如需要）:"
echo "  编辑 $DEPLOY_DIR/.env 配置 API Key"
