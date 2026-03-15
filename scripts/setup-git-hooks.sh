#!/usr/bin/env bash
# =============================================================================
# setup-git-hooks.sh - Install git hooks for the MES project
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d ".git" ]; then echo "Not a git repository. Run 'git init' first."; exit 1; fi

mkdir -p .git/hooks
cp scripts/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo "Git hooks installed. To bypass: git commit --no-verify"
