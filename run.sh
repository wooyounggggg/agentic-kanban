#!/bin/bash
# wt-board launcher
cd "$(dirname "$0")/.." || exit 1
PYTHONPATH="wt-board/src" exec python3 -m wt_board.cli.main "$@"
