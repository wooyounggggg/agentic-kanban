"""KanbanColumn widget — a vertical column of IssueCards for one status."""

from __future__ import annotations

from typing import List, Optional

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static
from textual.containers import Vertical

from wt_board.models.issue import Issue
from wt_board.models.config import StatusDef
from wt_board.ui.widgets.issue_card import IssueCard


class KanbanColumn(Vertical):
    """A vertical container showing a status column header and its cards.

    Parameters
    ----------
    status_def:
        The :class:`StatusDef` for this column (name, label, icon).
    issues:
        Initial list of :class:`Issue` objects to display.
    tc_map:
        Mapping of ticket -> TC progress string (e.g. "2/5").
    agent_map:
        Mapping of ticket -> agent status string.
    selected_index:
        Which card (0-based) should be highlighted on mount.
    """

    DEFAULT_CSS = """
    KanbanColumn {
        width: 1fr;
        height: 100%;
        margin: 0 1;
    }

    KanbanColumn .col-header {
        padding: 0 1;
        text-align: center;
        height: 1;
    }

    KanbanColumn .col-empty {
        padding: 1;
        text-align: center;
    }
    """

    focused_index: reactive[int] = reactive(-1)

    def __init__(
        self,
        status_def: StatusDef,
        issues: List[Issue],
        tc_map: dict = None,
        agent_map: dict = None,
        selected_index: int = -1,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.status_def = status_def
        self.issues = list(issues)
        self.tc_map = tc_map or {}
        self.agent_map = agent_map or {}
        self.focused_index = selected_index

    def compose(self) -> ComposeResult:
        count = len(self.issues)
        label = self.status_def.icon + " " + self.status_def.label
        yield Static(f"{label} [dim]({count})[/]", classes="col-header")

        if not self.issues:
            yield Static("[dim]— empty —[/]", classes="col-empty")
        else:
            for idx, issue in enumerate(self.issues):
                tc = self.tc_map.get(issue.ticket, "")
                agent_st = self.agent_map.get(issue.ticket, "idle")
                pipeline_step = getattr(issue, "pipeline_step", "")
                from wt_board.models.agent import AgentStatus
                agent_alive = agent_st == AgentStatus.ACTIVE
                card = IssueCard(
                    issue,
                    tc_progress=tc,
                    agent_status=agent_st,
                    status_label=self.status_def.label,
                    pipeline_step=pipeline_step,
                    agent_alive=agent_alive,
                )
                card.selected = idx == self.focused_index
                yield card

    # ------------------------------------------------------------------
    # Navigation helpers (called by BoardScreen)
    # ------------------------------------------------------------------

    def card_count(self) -> int:
        return len(self.issues)

    def set_focused_card(self, index: int) -> None:
        """Highlight the card at *index*, un-highlight all others."""
        cards = self.query(IssueCard)
        for i, card in enumerate(cards):
            card.selected = i == index
        self.focused_index = index

    def focused_issue(self) -> Optional[Issue]:
        if not self.issues or self.focused_index < 0:
            return None
        if self.focused_index >= len(self.issues):
            return None
        return self.issues[self.focused_index]
