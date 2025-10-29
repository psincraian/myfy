#!/bin/bash
#
# Install git hooks for myfy project
#
# This script copies the pre-commit hook to .git/hooks/
# Run this script after cloning the repository
#

set -e

# Colors for output
# Brand colors for myfy
EMERALD='\033[38;2;16;185;129m'  # #10B981 - Primary
GRAY='\033[38;2;17;24;39m'        # #111827 - Accent
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GRAY}📦 Installing git hooks for myfy...${NC}"
echo ""

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}⚠️  Warning: Not in a git repository root${NC}"
    echo "Please run this script from the repository root"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Install pre-commit hook
PRECOMMIT_SOURCE="scripts/hooks/pre-commit"
PRECOMMIT_DEST=".git/hooks/pre-commit"

if [ ! -f "$PRECOMMIT_SOURCE" ]; then
    echo -e "${YELLOW}⚠️  Warning: Hook source file not found: $PRECOMMIT_SOURCE${NC}"
    exit 1
fi

cp "$PRECOMMIT_SOURCE" "$PRECOMMIT_DEST"
chmod +x "$PRECOMMIT_DEST"
echo -e "${EMERALD}✓ Installed pre-commit hook${NC}"

# Install commit-msg hook
COMMITMSG_SOURCE="scripts/hooks/commit-msg"
COMMITMSG_DEST=".git/hooks/commit-msg"

if [ ! -f "$COMMITMSG_SOURCE" ]; then
    echo -e "${YELLOW}⚠️  Warning: Hook source file not found: $COMMITMSG_SOURCE${NC}"
    exit 1
fi

cp "$COMMITMSG_SOURCE" "$COMMITMSG_DEST"
chmod +x "$COMMITMSG_DEST"
echo -e "${EMERALD}✓ Installed commit-msg hook${NC}"

echo ""
echo -e "${GRAY}Git hooks installed:${NC}"
echo ""
echo -e "${GRAY}Pre-commit hook will:${NC}"
echo "  1. 🎨 Format code with ruff"
echo "  2. 🔍 Check linting with ruff"
echo "  3. 🔬 Check types with ty"
echo ""
echo -e "${GRAY}Commit-msg hook will:${NC}"
echo "  1. ✅ Validate conventional commit format"
echo "  2. 📏 Check message length"
echo ""
echo -e "${EMERALD}✅ Git hooks installed successfully!${NC}"
echo ""
echo -e "${YELLOW}💡 To skip hooks for a specific commit, use: git commit --no-verify${NC}"
echo -e "${YELLOW}💡 Use 'cz commit' for interactive conventional commits${NC}"
