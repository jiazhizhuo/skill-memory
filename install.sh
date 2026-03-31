#!/bin/bash
# skill-memory one-click install
# Usage: curl -fsSL https://raw.githubusercontent.com/jiazhizhuo/skill-memory/main/install.sh | bash

set -e

SKILL_DIR="${HOME}/.openclaw/skills/memory"
REPO_URL="https://github.com/jiazhizhuo/skill-memory.git"

echo "Installing skill-memory..."
echo "Location: ${SKILL_DIR}"

# Check prerequisites
if ! command -v git &> /dev/null; then
    echo "Error: git is required but not installed."
    exit 1
fi

# Clone or update repo
if [ -d "${SKILL_DIR}" ]; then
    echo "Updating existing installation..."
    cd "${SKILL_DIR}"
    git pull
else
    echo "Cloning repository..."
    mkdir -p "$(dirname "${SKILL_DIR}")"
    git clone "${REPO_URL}" "${SKILL_DIR}"
fi

# Install Python package
cd "${SKILL_DIR}"
echo "Installing Python package..."
pip install -e .

echo ""
echo "✅ skill-memory installed successfully!"
echo ""
echo "Next steps:"
echo "  1. Start Qdrant: docker run -d -p 6333:6333 qdrant/qdrant"
echo "  2. Use: memory add <content>"
echo ""
