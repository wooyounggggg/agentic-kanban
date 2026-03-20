"""Base types and Protocol for tracker plugins."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TrackerIssue:
    """A lightweight issue representation returned by any tracker plugin."""

    ticket_id: str
    title: str
    status: str
    url: str
    description: str = ""
    assignee: str = ""


class TrackerPlugin:
    """Protocol / base class for tracker integrations.

    Implementations should override :meth:`get_issue` and
    :meth:`list_my_issues`.  The ``name`` class attribute must be set to a
    unique identifier string (e.g. ``"dooray"``).
    """

    name: str = ""

    def get_issue(self, ticket_id: str) -> Optional[TrackerIssue]:
        """Return a :class:`TrackerIssue` for *ticket_id*, or ``None``."""
        raise NotImplementedError

    def list_my_issues(self) -> List[TrackerIssue]:
        """Return all issues assigned to the current user."""
        raise NotImplementedError
