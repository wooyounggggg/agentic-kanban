"""Central store for reading and writing the .board/ directory."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional

from wt_board.models.issue import Issue
from wt_board.models.checklist import Checklist
from wt_board.models.worklog import (
    WorklogEntry,
    read_worklog as _read_worklog,
    append_worklog as _append_worklog,
)
from wt_board.models.agent import AgentSession
from wt_board.models.config import BoardConfig

# ---------------------------------------------------------------------------
# File-name constants — single source of truth for all store paths
# ---------------------------------------------------------------------------
_ISSUE_FILE = "issue.yaml"
_CHECKLIST_FILE = "checklist.yaml"
_WORKLOG_FILE = "worklog.jsonl"
_AGENT_FILE = "agent.yaml"
_PLAN_FILE = "plan.md"
_CONFIG_FILE = "config.yaml"
_COMMENTS_FILE = "comments.md"
_DESCRIPTION_FILE = "description.md"


def find_board_root(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from *start* (default: cwd) looking for a ``.board/`` directory.

    Returns the ``.board/`` path if found, or ``None`` if the filesystem root
    is reached without finding one.
    """
    current = (start or Path.cwd()).resolve()
    while True:
        candidate = current / ".board"
        if candidate.is_dir():
            return candidate
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            return None
        current = parent


class BoardStore:
    """Read/write interface to a ``.board/`` directory.

    Parameters
    ----------
    board_path:
        Explicit path to the ``.board/`` directory.  When omitted,
        :func:`find_board_root` walks up from the current working directory.

    Raises
    ------
    FileNotFoundError
        If *board_path* is ``None`` and no ``.board/`` directory can be
        located in the directory hierarchy.
    """

    def __init__(self, board_path: Optional[Path] = None) -> None:
        if board_path is not None:
            self._root = Path(board_path).resolve()
        else:
            found = find_board_root()
            if found is None:
                raise FileNotFoundError(
                    "No .board/ directory found in the current directory or any parent."
                )
            self._root = found

    # ------------------------------------------------------------------
    # Directory helpers
    # ------------------------------------------------------------------

    @property
    def root(self) -> Path:
        """Absolute path to the ``.board/`` directory."""
        return self._root

    def issue_dir(self, ticket: str) -> Path:
        """Return the directory for *ticket* under ``.board/issues/``."""
        return self._root / "issues" / ticket

    def _archive_dir(self, ticket: str) -> Path:
        return self._root / "archive" / ticket

    def ensure_dirs(self) -> None:
        """Create ``.board/issues``, ``.board/archive``, and ``.board/cache`` if absent."""
        for sub in ("issues", "archive", "cache"):
            (self._root / sub).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Issue listing
    # ------------------------------------------------------------------

    def list_issues(self) -> List[str]:
        """Return ticket IDs whose ``issue.yaml`` exists under ``.board/issues/``."""
        issues_dir = self._root / "issues"
        if not issues_dir.is_dir():
            return []
        tickets: List[str] = []
        for entry in sorted(issues_dir.iterdir()):
            if entry.is_dir() and (entry / _ISSUE_FILE).exists():
                tickets.append(entry.name)
        return tickets

    # ------------------------------------------------------------------
    # Issue
    # ------------------------------------------------------------------

    def read_issue(self, ticket: str) -> Issue:
        """Load and return the :class:`~wt_board.models.issue.Issue` for *ticket*."""
        path = self.issue_dir(ticket) / _ISSUE_FILE
        return Issue.from_yaml(path)

    def write_issue(self, ticket: str, issue: Issue) -> None:
        """Persist *issue* to ``.board/issues/<ticket>/issue.yaml``."""
        path = self.issue_dir(ticket) / _ISSUE_FILE
        issue.to_yaml(path)

    # ------------------------------------------------------------------
    # Checklist
    # ------------------------------------------------------------------

    def read_checklist(self, ticket: str) -> Checklist:
        """Load and return the :class:`~wt_board.models.checklist.Checklist` for *ticket*.

        Returns an empty checklist if the file does not exist.
        """
        path = self.issue_dir(ticket) / _CHECKLIST_FILE
        return Checklist.from_yaml(path)

    def write_checklist(self, ticket: str, checklist: Checklist) -> None:
        """Persist *checklist* to ``.board/issues/<ticket>/checklist.yaml``."""
        path = self.issue_dir(ticket) / _CHECKLIST_FILE
        checklist.to_yaml(path)

    # ------------------------------------------------------------------
    # Worklog
    # ------------------------------------------------------------------

    def read_worklog(self, ticket: str) -> List[WorklogEntry]:
        """Return all :class:`~wt_board.models.worklog.WorklogEntry` objects for *ticket*."""
        path = self.issue_dir(ticket) / _WORKLOG_FILE
        return _read_worklog(path)

    def append_worklog(self, ticket: str, entry: WorklogEntry) -> None:
        """Append *entry* to ``.board/issues/<ticket>/worklog.jsonl``."""
        path = self.issue_dir(ticket) / _WORKLOG_FILE
        _append_worklog(path, entry)

    # ------------------------------------------------------------------
    # Agent
    # ------------------------------------------------------------------

    def read_agent(self, ticket: str) -> AgentSession:
        """Load and return the :class:`~wt_board.models.agent.AgentSession` for *ticket*.

        Returns a default session if the file does not exist.
        """
        path = self.issue_dir(ticket) / _AGENT_FILE
        return AgentSession.from_yaml(path)

    def write_agent(self, ticket: str, agent: AgentSession) -> None:
        """Persist *agent* to ``.board/issues/<ticket>/agent.yaml``."""
        path = self.issue_dir(ticket) / _AGENT_FILE
        agent.to_yaml(path)

    # ------------------------------------------------------------------
    # Plan (raw markdown)
    # ------------------------------------------------------------------

    def read_plan(self, ticket: str) -> str:
        """Return the raw markdown content of ``.board/issues/<ticket>/plan.md``.

        Returns an empty string if the file does not exist.
        """
        path = self.issue_dir(ticket) / _PLAN_FILE
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def write_plan(self, ticket: str, content: str) -> None:
        """Write *content* to ``.board/issues/<ticket>/plan.md``."""
        path = self.issue_dir(ticket) / _PLAN_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Description (raw markdown)
    # ------------------------------------------------------------------

    def read_description(self, ticket: str) -> str:
        """Return the raw content of ``.board/issues/<ticket>/description.md``.

        Returns an empty string if the file does not exist.
        """
        path = self.issue_dir(ticket) / _DESCRIPTION_FILE
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def write_description(self, ticket: str, content: str) -> None:
        """Write *content* to ``.board/issues/<ticket>/description.md``."""
        path = self.issue_dir(ticket) / _DESCRIPTION_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Comments (raw markdown)
    # ------------------------------------------------------------------

    def read_comments(self, ticket: str) -> str:
        """Return the raw content of ``.board/issues/<ticket>/comments.md``.

        Returns an empty string if the file does not exist.
        """
        path = self.issue_dir(ticket) / _COMMENTS_FILE
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def write_comments(self, ticket: str, content: str) -> None:
        """Write *content* to ``.board/issues/<ticket>/comments.md``."""
        path = self.issue_dir(ticket) / _COMMENTS_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def read_config(self) -> BoardConfig:
        """Load and return the :class:`~wt_board.models.config.BoardConfig`.

        Returns defaults if ``config.yaml`` does not exist.
        """
        path = self._root / _CONFIG_FILE
        return BoardConfig.from_yaml(path)

    def write_config(self, config: BoardConfig) -> None:
        """Persist *config* to ``.board/config.yaml``."""
        path = self._root / _CONFIG_FILE
        config.to_yaml(path)

    # ------------------------------------------------------------------
    # Archive
    # ------------------------------------------------------------------

    def archive_issue(self, ticket: str) -> None:
        """Move ``.board/issues/<ticket>/`` to ``.board/archive/<ticket>/``."""
        src = self.issue_dir(ticket)
        if not src.exists():
            raise FileNotFoundError(f"Issue directory not found: {src}")
        dst = self._archive_dir(ticket)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
