#!/bin/bash
# Skill Memory 部署脚本
# 从开发目录同步代码到部署目录

set -e

# 目录配置
DEV_DIR="${SKILL_MEMORY_DEV:-$HOME/git/skill-memory}"
DEPLOY_DIR="${SKILL_MEMORY_DEPLOY:-$HOME/.skill-memory}"

echo "=== Skill Memory 部署 ==="
echo "开发目录: $DEV_DIR"
echo "部署目录: $DEPLOY_DIR"
echo ""

# 检查开发目录
if [ ! -d "$DEV_DIR/.git" ]; then
    echo "错误: 开发目录不存在或不是 git 仓库: $DEV_DIR"
    exit 1
fi

# 创建部署目录（如果不存在）
mkdir -p "$DEPLOY_DIR"

# 需要同步的目录/文件
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
)

# 构建 rsync 排除参数
EXCLUDE_ARGS=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude=$pattern"
done

echo "同步文件..."
for item in "${SYNC_ITEMS[@]}"; do
    if [ -e "$DEV_DIR/$item" ]; then
        echo "  $item"
        rsync -av --delete $EXCLUDE_ARGS "$DEV_DIR/$item" "$DEPLOY_DIR/"
    fi
done

# 复制 .env.example（如果部署目录没有 .env）
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    if [ -f "$DEV_DIR/.env.example" ]; then
        echo "  创建 .env (从 .env.example)"
        cp "$DEV_DIR/.env.example" "$DEPLOY_DIR/.env"
    fi
fi

# 创建必要的运行时目录
mkdir -p "$DEPLOY_DIR/knowledge"
mkdir -p "$DEPLOY_DIR/memory"
mkdir -p "$DEPLOY_DIR/data"

# 重新安装（如果有 pip）
if command -v pip3 &> /dev/null; then
    echo ""
    echo "重新安装 Python 包..."
    cd "$DEPLOY_DIR"
    pip3 install -e . --quiet 2>/dev/null || echo "警告: pip install 失败，请手动安装"
fi

echo ""
echo "=== 部署完成 ==="
echo ""
echo "下一步："
echo "  1. 编辑 $DEPLOY_DIR/.env 配置 API Key"
echo "  2. 运行 'memory stats' 验证安装"
