"""WorklogWidget — scrollable display of worklog entries."""

from __future__ import annotations

from typing import List

from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import VerticalScroll

from wt_board.models.worklog import WorklogEntry


_AUTHOR_BADGE = {
    "agent": "[cyan bold]agent[/]",
    "human": "[green bold]human[/]",
}


def _format_entry(entry: WorklogEntry, index: int) -> str:
    author = _AUTHOR_BADGE.get(entry.author, f"[dim]{entry.author}[/]")
    at = entry.at[:16] if entry.at else ""  # Trim to "YYYY-MM-DDTHH:MM"
    header = f"[dim]{at}[/] {author}"
    body = entry.work_done or "[dim](no description)[/]"
    next_act = ""
    if entry.next_action:
        next_act = f"\n  [dim]next:[/] {entry.next_action}"
    return f"{header}\n  {body}{next_act}"


class WorklogWidget(VerticalScroll):
    """Shows worklog entries, most recent first.

    Parameters
    ----------
    entries:
        List of :class:`WorklogEntry` objects to display.
    """

    DEFAULT_CSS = """
    WorklogWidget {
        height: auto;
        max-height: 20;
        overflow-y: auto;
        padding: 0 1;
    }

    WorklogWidget .wl-entry {
        border-bottom: dashed $surface-lighten-1;
        padding: 0 0 1 0;
        margin-bottom: 1;
        height: auto;
    }

    WorklogWidget .wl-empty {
        color: $text-muted;
        padding: 1;
    }
    """

    def __init__(self, entries: List[WorklogEntry], **kwargs) -> None:
        super().__init__(**kwargs)
        self.entries = list(reversed(entries))  # most recent first

    def compose(self) -> ComposeResult:
        if not self.entries:
            yield Static("[dim]No worklog entries.[/]", classes="wl-empty")
            return
        for idx, entry in enumerate(self.entries):
            yield Static(_format_entry(entry, idx), classes="wl-entry")
