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
    AgentStatus.ACTIVE: "[bold cyan] A [/]",
    AgentStatus.COMPLETED: "[dim green] done [/]",
    AgentStatus.ERROR: "[bold red] ERR [/]",
    AgentStatus.IDLE: "",
}

_MAX_TITLE = 32


class IssueCard(Static):
    """A compact card representing one Issue.

    Attributes
    ----------
    selected:
        Whether this card is the currently focused card.
    """

    DEFAULT_CSS = """
    IssueCard {
        height: auto;
        padding: 0 1;
        margin: 0 0 1 0;
        border: tall $surface-darken-1;
        background: $surface;
    }

    IssueCard:focus {
        border: tall $accent;
        background: $surface-lighten-1;
    }

    IssueCard.selected {
        border: tall $accent;
        background: $surface-lighten-1;
    }
    """

    selected: reactive[bool] = reactive(False)

    def __init__(
        self,
        issue: Issue,
        tc_progress: str = "",
        agent_status: str = AgentStatus.IDLE,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.issue = issue
        self.tc_progress = tc_progress
        self._agent_status = agent_status

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _build_markup(self) -> str:
        from rich.markup import escape
        ticket = self.issue.ticket
        title = escape(self.issue.title)
        if len(title) > _MAX_TITLE:
            title = title[:_MAX_TITLE - 1] + "\u2026"

        badge = _AGENT_BADGE.get(self._agent_status, "")
        tc = f" [dim]{self.tc_progress}[/]" if self.tc_progress else ""

        assignee_line = ""
        if self.issue.assignee:
            assignee_line = f"\n[dim italic]{self.issue.assignee}[/]"

        return f"[bold cyan]#{ticket}[/] {title}{tc}{badge}{assignee_line}"

    def render(self) -> str:
        return self._build_markup()

    # ------------------------------------------------------------------
    # Reactivity
    # ------------------------------------------------------------------

    def watch_selected(self, value: bool) -> None:
        self.set_class(value, "selected")
        if value:
            self.focus()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

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
