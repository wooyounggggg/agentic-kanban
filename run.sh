#!/bin/bash
# agentic-kanban launcher
cd "$(dirname "$0")/.." || exit 1
PYTHONPATH="agentic-kanban/src" exec python3 -m agentic_kanban.cli.main "$@"
