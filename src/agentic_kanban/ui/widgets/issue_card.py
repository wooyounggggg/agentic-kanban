"""IssueCard widget — a single card in a Kanban column."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.events import Click
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from agentic_kanban.models.issue import Issue
from agentic_kanban.models.agent import AgentStatus


_STATUS_PALETTE = [
    "#6a8c5a", "#5a7a8c", "#8c6a7a", "#7a8c5a",
    "#5a6a8c", "#8c7a5a", "#6a5a8c", "#5a8c7a",
]


def _status_color(status: str) -> str:
    """문자열 해싱으로 muted 배경색 반환."""
    h = sum(ord(c) for c in status)
    return _STATUS_PALETTE[h % len(_STATUS_PALETTE)]


_AGENT_BADGE = {
    AgentStatus.ACTIVE: " [bold #8fac6e]●[/]",
    AgentStatus.COMPLETED: " [dim #8fac6e]✓[/]",
    AgentStatus.ERROR: " [bold #c47070]✗[/]",
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
    }
    """

    selected: reactive[bool] = reactive(False)

    def __init__(
        self,
        issue: Issue,
        tc_progress: str = "",
        agent_status: str = AgentStatus.IDLE,
        status_label: str = "",
        pipeline_step: str = "",
        agent_alive: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.issue = issue
        self.tc_progress = tc_progress
        self._agent_status = agent_status
        self._status_label = status_label
        self._pipeline_step = pipeline_step
        self._agent_alive = agent_alive

    def _build_markup(self) -> str:
        from rich.markup import escape
        ticket = self.issue.ticket
        title = escape(self.issue.title)
        if len(title) > _MAX_TITLE:
            title = title[:_MAX_TITLE - 1] + "\u2026"

        # Line 1: ticket + title + agent running indicator
        alive_badge = " [bold #8fac6e]⟳ 실행중[/]" if self._agent_alive else ""
        line1 = f"[bold #d4a57a]#{ticket}[/] {title}{alive_badge}"

        # Line 2: Dooray status chip + assignee + TC + tags
        parts = []
        if self._status_label:
            bg = _status_color(self._status_label)
            parts.append(f"[on {bg}] [bold white]{escape(self._status_label)}[/bold white] [/]")
        if self.issue.assignee:
            parts.append(f"[dim]@{escape(self.issue.assignee)}[/]")
        if self.tc_progress:
            parts.append(f"[dim]{self.tc_progress} TC[/]")
        if self.issue.labels:
            tags = " ".join(f"[on #3a3430 dim #c4b06a] {escape(t)} [/]" for t in self.issue.labels[:3])
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
