"""SyncService: pull issue data from an external tracker."""

from __future__ import annotations

from typing import List, Optional

from wt_board.models.config import BoardConfig
from wt_board.models.issue import Issue, TrackerInfo
from wt_board.store.board_store import BoardStore
from wt_board.trackers.base import TrackerPlugin
from wt_board.trackers.dooray import DoorayTracker


class SyncService:
    def __init__(
        self,
        store: BoardStore,
        tracker: TrackerPlugin,
        config: BoardConfig,
    ) -> None:
        self._store = store
        self._tracker = tracker
        self._config = config

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _apply_tracker_data(self, issue: Issue) -> Issue:
        """Fetch fresh data from the tracker and update *issue* in place."""
        remote = self._tracker.get_issue(issue.ticket)
        if remote is None:
            return issue

        if remote.title:
            issue.title = remote.title

        # Map remote status to a local status name if possible; otherwise keep.
        local_names = self._config.status_names()
        if remote.status in local_names:
            issue.status = remote.status

        issue.tracker = TrackerInfo(
            type=self._tracker.name,
            post_id=remote.ticket_id,
            url=remote.url,
            remote_status=remote.status,
        )

        if remote.description:
            issue.description = remote.description
            self._store.write_description(issue.ticket, remote.description)

        if remote.assignee:
            issue.assignee = remote.assignee

        issue.touch_updated()
        return issue

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sync_issue(self, ticket: str) -> Issue:
        """Sync a single issue's title and status from the tracker."""
        issue = self._store.read_issue(ticket)
        issue = self._apply_tracker_data(issue)
        self._store.write_issue(ticket, issue)
        return issue

    def sync_all(self) -> List[Issue]:
        """Sync all active issues and return the updated list."""
        updated: List[Issue] = []
        for ticket in self._store.list_issues():
            issue = self._store.read_issue(ticket)
            issue = self._apply_tracker_data(issue)
            self._store.write_issue(ticket, issue)
            updated.append(issue)
        return updated

    def sync_comments(self, ticket: str) -> str:
        """Fetch comments from the tracker and save them.

        Returns the formatted markdown string (empty string if the tracker
        does not support comments or the call fails).
        """
        if not isinstance(self._tracker, DoorayTracker):
            return ""

        post_id = ""
        try:
            issue = self._store.read_issue(ticket)
            post_id = issue.tracker.post_id or ticket
        except Exception:
            post_id = ticket

        content: Optional[str] = self._tracker.get_comments(post_id)
        if content is None:
            content = ""

        self._store.write_comments(ticket, content)
        return content
