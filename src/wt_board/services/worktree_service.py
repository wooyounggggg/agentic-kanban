"""WorktreeService: git worktree management via subprocess."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional

from wt_board.models.config import BoardConfig


class WorktreeService:
    def __init__(self, project_root: Path, config: BoardConfig) -> None:
        self._root = Path(project_root).resolve()
        self._config = config

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _worktree_path(self, ticket: str) -> Path:
        base = self._config.project.worktree_base
        return self._root / base / f"feature-{ticket}"

    def _branch_name(self, ticket: str) -> str:
        return f"{self._config.project.branch_prefix}{ticket}"

    def _run(self, args: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=str(self._root),
            capture_output=True,
            text=True,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_worktree(
        self, ticket: str, base_branch: Optional[str] = None
    ) -> str:
        """Create a git worktree for *ticket* and return the worktree path.

        Creates a new branch ``<branch_prefix><ticket>`` off *base_branch*
        (default: ``config.project.base_branch``).

        Raises
        ------
        RuntimeError
            If ``git worktree add`` exits non-zero.
        """
        wt_path = self._worktree_path(ticket)
        branch = self._branch_name(ticket)
        base = base_branch or self._config.project.base_branch

        wt_path.parent.mkdir(parents=True, exist_ok=True)

        result = self._run(
            ["git", "worktree", "add", "-b", branch, str(wt_path), base]
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git worktree add failed for {ticket}:\n{result.stderr.strip()}"
            )
        return str(wt_path)

    def remove_worktree(self, ticket: str) -> None:
        """Remove the git worktree for *ticket*.

        Raises
        ------
        RuntimeError
            If ``git worktree remove`` exits non-zero.
        """
        wt_path = self._worktree_path(ticket)
        result = self._run(
            ["git", "worktree", "remove", "--force", str(wt_path)]
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git worktree remove failed for {ticket}:\n{result.stderr.strip()}"
            )

    def list_worktrees(self) -> List[str]:
        """Return a list of existing worktree paths reported by git."""
        result = self._run(["git", "worktree", "list", "--porcelain"])
        if result.returncode != 0:
            return []

        paths: List[str] = []
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                paths.append(line[len("worktree "):].strip())
        return paths

    def worktree_exists(self, ticket: str) -> bool:
        """Return True if the worktree path for *ticket* exists on disk."""
        wt_path = self._worktree_path(ticket)
        return wt_path.exists()
