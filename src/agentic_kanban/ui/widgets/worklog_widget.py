"""WorklogWidget — scrollable display of worklog entries."""

from __future__ import annotations

from typing import List

from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import VerticalScroll

from agentic_kanban.models.worklog import WorklogEntry
from agentic_kanban.utils import format_short_date


_AUTHOR_COLOR = {
    "agent": "cyan",
    "human": "green",
}

def _format_entry(entry: WorklogEntry, index: int) -> str:
    from rich.markup import escape
    color = _AUTHOR_COLOR.get(entry.author, "white")
    at_display = format_short_date(entry.at) if entry.at else ""
    body = escape(entry.work_done) if entry.work_done else "(내용 없음)"

    lines = [f"[{color} bold]{at_display}[/]  [dim]{entry.author}[/]"]
    lines.append(f"  {body}")
    if entry.next_action:
        lines.append(f"  [dim]→ {escape(entry.next_action)}[/]")
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
            yield Static("작업 기록이 없습니다.", classes="wl-empty")
            return
        for idx, entry in enumerate(self.entries):
            yield Static(_format_entry(entry, idx), classes="wl-entry")
