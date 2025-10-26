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

# Copy pre-commit hook
HOOK_SOURCE="scripts/hooks/pre-commit"
HOOK_DEST=".git/hooks/pre-commit"

if [ ! -f "$HOOK_SOURCE" ]; then
    echo -e "${YELLOW}⚠️  Warning: Hook source file not found: $HOOK_SOURCE${NC}"
    exit 1
fi

cp "$HOOK_SOURCE" "$HOOK_DEST"
chmod +x "$HOOK_DEST"

echo -e "${EMERALD}✓ Installed pre-commit hook${NC}"
echo ""
echo -e "${GRAY}The hook will run automatically before each commit and will:${NC}"
echo "  1. 🎨 Format code with ruff"
echo "  2. 🔍 Check linting with ruff"
echo "  3. 🔬 Check types with ty"
echo ""
echo -e "${EMERALD}✅ Git hooks installed successfully!${NC}"
echo ""
echo -e "${YELLOW}💡 To skip hooks for a specific commit, use: git commit --no-verify${NC}"
