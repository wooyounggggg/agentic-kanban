"""WorklogWidget — scrollable display of worklog entries."""

from __future__ import annotations

from typing import List

from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import VerticalScroll

from wt_board.models.worklog import WorklogEntry


_AUTHOR_BADGE = {
    "agent": "agent",
    "human": "human",
}

_AUTHOR_COLOR = {
    "agent": "cyan",
    "human": "green",
}

_BOX_WIDTH = 60


def _format_entry(entry: WorklogEntry, index: int) -> str:
    author = _AUTHOR_BADGE.get(entry.author, entry.author)
    color = _AUTHOR_COLOR.get(entry.author, "white")
    at = entry.at[:16] if entry.at else ""
    # Format date portion: YYYY-MM-DDTHH:MM → YYYY-MM-DD HH:MM
    at_display = at.replace("T", " ")

    header_line = f"[dim]┌[/] [{color}]{at_display}[/] [dim]({author})[/]"
    body = entry.work_done or "(no description)"
    body_line = f"[dim]│[/] {body}"

    lines = [header_line, body_line]
    if entry.next_action:
        lines.append(f"[dim]│[/] [dim]→ 다음:[/] {entry.next_action}")
    lines.append(f"[dim]└{'─' * (_BOX_WIDTH - 1)}[/]")
    return "\n".join(lines)


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
        padding: 0 0 1 0;
        height: auto;
    }

    WorklogWidget .wl-empty {
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
