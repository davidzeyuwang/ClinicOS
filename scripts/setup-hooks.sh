#!/bin/bash
# Setup pre-commit hook for ClinicOS
# Run this once after cloning the repository

set -e

echo "🔧 Setting up ClinicOS pre-commit hook..."

HOOK_SRC="scripts/pre-commit.sh"
HOOK_DEST=".git/hooks/pre-commit"

# Check if Git directory exists
if [ ! -d ".git" ]; then
    echo "❌ Error: Not a git repository. Run this from the repo root."
    exit 1
fi

# Copy hook file
if [ -f "$HOOK_SRC" ]; then
    cp "$HOOK_SRC" "$HOOK_DEST"
    chmod +x "$HOOK_DEST"
    echo "✅ Pre-commit hook installed at $HOOK_DEST"
else
    echo "❌ Error: $HOOK_SRC not found"
    exit 1
fi

# Test hook
if [ -x "$HOOK_DEST" ]; then
    echo "✅ Hook is executable"
else
    echo "❌ Error: Hook is not executable"
    exit 1
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "The pre-commit hook will now run tests automatically before each commit:"
echo "  - Backend tests (if backend/ files changed)"
echo "  - Frontend E2E tests (if frontend/ files changed)"
echo ""
echo "To skip the hook for a specific commit, use: git commit --no-verify"
echo ""
