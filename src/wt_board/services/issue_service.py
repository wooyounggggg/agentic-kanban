"""IssueService: business logic for issue lifecycle."""

from __future__ import annotations

from typing import Dict, List, Optional

from wt_board.models.config import BoardConfig
from wt_board.models.issue import Issue, TrackerInfo, WorktreeInfo
from wt_board.store.board_store import BoardStore
from wt_board.utils import now_iso


class IssueService:
    def __init__(self, store: BoardStore, config: BoardConfig) -> None:
        self._store = store
        self._config = config

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _first_status(self) -> str:
        if self._config.statuses:
            return self._config.statuses[0].name
        return "planning"

    def _branch_name(self, ticket: str) -> str:
        return f"{self._config.project.branch_prefix}{ticket}"

    def _worktree_path(self, ticket: str) -> str:
        base = self._config.project.worktree_base
        return f"{base}/feature-{ticket}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_issue(
        self,
        ticket: str,
        title: str = "",
        base_branch: Optional[str] = None,
    ) -> Issue:
        """Create an issue record and its git worktree.

        Sets ``created_at``, ``updated_at``, and ``status`` to the first
        status defined in the board config.
        """
        from wt_board.services.worktree_service import WorktreeService

        effective_base = base_branch or self._config.project.base_branch
        now = now_iso()

        worktree_info = WorktreeInfo(
            path=self._worktree_path(ticket),
            branch=self._branch_name(ticket),
            base_branch=effective_base,
        )

        issue = Issue(
            ticket=ticket,
            title=title,
            status=self._first_status(),
            priority=99,
            created_at=now,
            updated_at=now,
            worktree=worktree_info,
            tracker=TrackerInfo(),
            labels=[],
        )

        self._store.ensure_dirs()
        self._store.write_issue(ticket, issue)

        # Attempt to create the worktree; log but don't raise if git fails
        wt_service = WorktreeService(self._store.root.parent, self._config)
        try:
            wt_service.create_worktree(ticket, base_branch=effective_base)
        except RuntimeError as exc:
            import warnings
            warnings.warn(f"Worktree creation failed for {ticket}: {exc}")

        return issue

    def move_issue(self, ticket: str, new_status: str) -> Issue:
        """Move *ticket* to *new_status* with transition validation."""
        issue = self._store.read_issue(ticket)

        valid_names = self._config.status_names()
        if new_status not in valid_names:
            raise ValueError(
                f"Unknown status '{new_status}'. Valid: {valid_names}"
            )

        if not self._config.is_valid_transition(issue.status, new_status):
            raise ValueError(
                f"Transition '{issue.status}' -> '{new_status}' is not allowed."
            )

        issue.status = new_status
        issue.touch_updated()
        self._store.write_issue(ticket, issue)
        return issue

    def set_priority(self, ticket: str, priority: int) -> Issue:
        """Set the numeric priority of *ticket*."""
        issue = self._store.read_issue(ticket)
        issue.priority = priority
        issue.touch_updated()
        self._store.write_issue(ticket, issue)
        return issue

    def list_issues_by_status(self) -> Dict[str, List[Issue]]:
        """Return issues grouped by status column in config order."""
        tickets = self._store.list_issues()
        by_status: Dict[str, List[Issue]] = {
            s.name: [] for s in self._config.statuses
        }

        for ticket in tickets:
            issue = self._store.read_issue(ticket)
            if issue.status in by_status:
                by_status[issue.status].append(issue)
            else:
                # Status not in config — put in a catch-all bucket
                by_status.setdefault(issue.status, []).append(issue)

        # Sort each column by priority ascending
        for col in by_status.values():
            col.sort(key=lambda i: i.priority)

        return by_status

    def archive_issue(self, ticket: str) -> None:
        """Move *ticket* to the archive directory."""
        self._store.archive_issue(ticket)
