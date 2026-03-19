"""IssueCard widget — a single card in a Kanban column."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.events import Click
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from wt_board.models.issue import Issue
from wt_board.models.agent import AgentStatus


_AGENT_BADGE = {
    AgentStatus.ACTIVE: " [bold green]●[/]",
    AgentStatus.COMPLETED: " [dim green]✓[/]",
    AgentStatus.ERROR: " [bold red]✗[/]",
    AgentStatus.IDLE: "",
}

_MAX_TITLE = 36


class IssueCard(Static):
    """A compact card representing one Issue."""

    DEFAULT_CSS = """
    IssueCard {
        height: auto;
        padding: 0 1;
        margin: 0 0 1 0;
        border: tall #21262d;
        background: #161b22;
    }
    IssueCard:focus {
        border: tall #58a6ff;
        background: #0d419f;
    }
    IssueCard.selected {
        border: tall #58a6ff;
        background: #0d419f;
    }
    """

    selected: reactive[bool] = reactive(False)

    def __init__(
        self,
        issue: Issue,
        tc_progress: str = "",
        agent_status: str = AgentStatus.IDLE,
        status_label: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.issue = issue
        self.tc_progress = tc_progress
        self._agent_status = agent_status
        self._status_label = status_label

    def _build_markup(self) -> str:
        from rich.markup import escape
        ticket = self.issue.ticket
        title = escape(self.issue.title)
        if len(title) > _MAX_TITLE:
            title = title[:_MAX_TITLE - 1] + "\u2026"

        # Line 1: ticket + title + agent badge
        badge = _AGENT_BADGE.get(self._agent_status, "")
        line1 = f"[bold cyan]#{ticket}[/] {title}{badge}"

        # Line 2: status chip + assignee + TC + tags
        parts = []
        if self._status_label:
            parts.append(f"[on #30363d] {self._status_label} [/]")
        if self.issue.assignee:
            parts.append(f"[dim]@{escape(self.issue.assignee)}[/]")
        if self.tc_progress:
            parts.append(f"[dim]{self.tc_progress} TC[/]")
        if self.issue.labels:
            tags = " ".join(f"[on #30363d dim magenta] {escape(t)} [/]" for t in self.issue.labels[:3])
            parts.append(tags)

        line2 = ""
        if parts:
            line2 = "\n" + " ".join(parts)

        return line1 + line2

    def render(self) -> str:
        return self._build_markup()

    def watch_selected(self, value: bool) -> None:
        self.set_class(value, "selected")
        if value:
            self.focus()

    class Clicked(Message):
        """Emitted when this card is clicked."""
        def __init__(self, card: "IssueCard") -> None:
            super().__init__()
            self.card = card

    def on_click(self, event: Click) -> None:
        self.post_message(self.Clicked(self))

    @property
    def ticket(self) -> str:
        return self.issue.ticket
