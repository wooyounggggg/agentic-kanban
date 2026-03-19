"""Dooray tracker plugin — shells out to the Dooray CLI."""

from __future__ import annotations

import json
import os
import subprocess
from typing import List, Optional

from wt_board.trackers.base import TrackerIssue, TrackerPlugin


class DoorayTracker(TrackerPlugin):
    """Tracker plugin that calls the Node-based Dooray CLI.

    The CLI is invoked as::

        node <cli_path> get-post --post <ticket_id>

    JSON output is parsed to extract title, status, and URL.

    Parameters
    ----------
    cli_path:
        Path to the ``dooray-cli.js`` file, e.g.
        ``~/.mcp-global-server/dooray-cli.js``.
    api_key:
        Optional API key passed via the ``DOORAY_API_KEY`` environment
        variable when calling the CLI.
    """

    name: str = "dooray"

    def __init__(self, cli_path: str, api_key: str = "") -> None:
        self._cli_path = os.path.expanduser(cli_path)
        self._api_key = api_key
        self._member_cache: dict = {}  # userCode -> display name

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_member_name(self, user_code: str) -> str:
        """Resolve a Dooray userCode to display name. Results are cached.

        Falls back to the raw ``user_code`` value if the lookup fails.
        """
        if not user_code:
            return user_code
        if user_code in self._member_cache:
            return self._member_cache[user_code]
        data = self._run(["search-members", "--user-code", user_code])
        name = user_code  # fallback
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                name = first.get("name") or user_code
        elif isinstance(data, dict):
            name = data.get("name") or user_code
        self._member_cache[user_code] = name
        return name

    @staticmethod
    def _format_date(iso_date: str) -> str:
        """Format an ISO8601 date string to ``YYYY-MM-DD HH:MM``."""
        if not iso_date:
            return iso_date
        # Trim timezone and seconds: "2026-03-05T17:12:40+09:00" -> "2026-03-05 17:12"
        try:
            # Replace T separator and drop everything after minutes
            normalized = iso_date.replace("T", " ")
            # Keep only YYYY-MM-DD HH:MM (first 16 chars after normalization)
            return normalized[:16]
        except Exception:
            return iso_date

    def _env(self) -> dict:
        env = os.environ.copy()
        if self._api_key:
            env["DOORAY_API_KEY"] = self._api_key
        return env

    def _run(self, args: List[str]) -> Optional[dict]:
        """Run the CLI and return parsed JSON, or ``None`` on any error."""
        try:
            result = subprocess.run(
                ["node", self._cli_path] + args,
                capture_output=True,
                text=True,
                env=self._env(),
                timeout=15,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

        if result.returncode != 0:
            return None

        stdout = result.stdout.strip()
        if not stdout:
            return None

        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return None

    def _parse_issue(self, data: dict) -> Optional[TrackerIssue]:
        """Convert a raw CLI JSON object into a :class:`TrackerIssue`."""
        if not data:
            return None

        ticket_id = str(data.get("id") or data.get("postId") or "")
        title = data.get("subject") or data.get("title") or ""
        status = data.get("workflowClass") or data.get("status") or ""
        url = data.get("url") or ""

        # Extract issue body / description
        body = data.get("body") or {}
        description: str = ""
        if isinstance(body, dict):
            description = body.get("content") or ""
        elif isinstance(body, str):
            description = body

        # Extract assignee — first entry in users.to
        assignee: str = ""
        users = data.get("users") or {}
        if isinstance(users, dict):
            to_list = users.get("to") or []
            if to_list:
                first = to_list[0]
                if isinstance(first, dict):
                    member = first.get("member") or {}
                    assignee = member.get("name") or ""

        if not ticket_id:
            return None

        return TrackerIssue(
            ticket_id=ticket_id,
            title=title,
            status=status,
            url=url,
            description=description,
            assignee=assignee,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_issue(self, ticket_id: str) -> Optional[TrackerIssue]:
        """Return the :class:`TrackerIssue` for *ticket_id*, or ``None``.

        Uses ``get-post-detail`` instead of ``get-post`` so that the response
        includes the ``body`` field (description content).
        """
        data = self._run(["get-post-detail", "--post", ticket_id])
        if data is None:
            return None
        # Some CLI versions wrap the payload in a "result" key
        payload = data.get("result") or data if isinstance(data, dict) else None
        return self._parse_issue(payload or {})

    def list_my_issues(self) -> List[TrackerIssue]:
        """Return issues assigned to the current user."""
        data = self._run(["list-my-posts"])
        if data is None:
            return []

        items = data if isinstance(data, list) else data.get("result", [])
        if not isinstance(items, list):
            return []

        issues: List[TrackerIssue] = []
        for item in items:
            parsed = self._parse_issue(item)
            if parsed is not None:
                issues.append(parsed)
        return issues

    def get_comments(self, ticket_id: str) -> Optional[str]:
        """Fetch comments for *ticket_id* and return formatted markdown.

        Calls ``node {cli_path} get-post-logs --post {ticket_id}``.  The CLI
        returns a JSON list of log/comment entries directly (not wrapped in a
        ``result`` key).  Each entry with ``type == "comment"`` is rendered as::

            ### {author} ({date})
            {content}
            ---

        Returns ``None`` if the call fails or there are no comments.
        """
        data = self._run(["get-post-logs", "--post", ticket_id])
        if data is None:
            return None

        # get-post-logs returns a plain list
        if isinstance(data, dict):
            comments_raw = data.get("result") or []
        elif isinstance(data, list):
            comments_raw = data
        else:
            return None

        if not isinstance(comments_raw, list) or not comments_raw:
            return None

        parts: List[str] = []
        for comment in comments_raw:
            if not isinstance(comment, dict):
                continue

            # Dooray API uses "postLogType" field; fall back to "type" for
            # compatibility with any future CLI changes.
            log_type = (
                comment.get("postLogType")
                or comment.get("type")
                or ""
            ).lower()
            # Only include actual comments (not status-change / assignment logs)
            if log_type and log_type != "comment":
                continue

            # Author — stored under creator.member
            creator = comment.get("creator") or {}
            author: str = ""
            if isinstance(creator, dict):
                member = creator.get("member") or {}
                if isinstance(member, dict):
                    author = member.get("name") or ""
                    if not author:
                        # Try to resolve via userCode -> display name
                        user_code = member.get("userCode") or ""
                        if user_code:
                            author = self._resolve_member_name(user_code)
                        else:
                            # Last resort: raw organizationMemberId
                            author = member.get("organizationMemberId") or ""
            author = author or "Unknown"

            # Date
            raw_date: str = comment.get("createdAt") or ""
            date = self._format_date(raw_date) if raw_date else ""

            # Content
            body = comment.get("body") or {}
            content: str = ""
            if isinstance(body, dict):
                content = body.get("content") or ""
            elif isinstance(body, str):
                content = body
            content = content.strip()

            if content:
                parts.append(f"### {author} ({date})\n{content}\n---")

        if not parts:
            return None

        return "\n\n".join(parts) + "\n"
