"""PlanViewer — thin wrapper around Textual's Markdown widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Markdown
from textual.containers import VerticalScroll


_EMPTY_PLAN = "_No plan file found. Create `.kanban/issues/<ticket>/plan.md`._"


class PlanViewer(VerticalScroll):
    """Renders plan markdown content.

    Parameters
    ----------
    content:
        Raw markdown string to display.  Falls back to a hint if empty.
    """

    DEFAULT_CSS = """
    PlanViewer {
        height: auto;
        max-height: 24;
        overflow-y: auto;
        padding: 0 1;
    }
    """

    def __init__(self, content: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._content = content or _EMPTY_PLAN

    def compose(self) -> ComposeResult:
        yield Markdown(self._content)

    def update_content(self, content: str) -> None:
        """Replace the displayed markdown."""
        self._content = content or _EMPTY_PLAN
        try:
            md = self.query_one(Markdown)
            md.update(self._content)
        except Exception:
            pass
