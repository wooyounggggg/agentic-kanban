#!/bin/bash
# Install agentic-kanban TUI + Claude Code plugin
set -e

echo "Installing agentic-kanban..."

# Python package
pip install -e .

# Claude Code plugin
if command -v claude &>/dev/null; then
    echo "Installing Claude Code plugin..."
    claude plugin add "$(dirname "$0")/plugin" 2>/dev/null || echo "Plugin install skipped (claude not available)"
fi

echo "Done! Run 'agentic-kanban init' to get started."
