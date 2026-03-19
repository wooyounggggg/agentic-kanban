"""Sidebar widget with project list."""

from __future__ import annotations

from typing import List, Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Static


class Sidebar(Vertical):
    """Left sidebar showing project list."""

    DEFAULT_CSS = """
    Sidebar {
        width: 20;
        height: 100%;
        background: #313244;
        border-right: solid #45475a;
        padding: 1;
    }
    Sidebar.focused-mode {
        border-right: solid #89b4fa;
    }
    Sidebar .sb-title {
        color: #89b4fa;
        text-style: bold;
        padding: 0 0 1 0;
    }
    Sidebar .sb-section {
        color: #6c7086;
        text-style: italic;
        height: 1;
        margin-top: 1;
    }
    Sidebar .sb-section-active {
        color: #89b4fa;
        text-style: bold;
        height: 1;
        margin-top: 1;
    }
    Sidebar .sb-item {
        color: #6c7086;
        padding-left: 1;
        height: 1;
    }
    Sidebar .sb-item-current {
        color: #cdd6f4;
        text-style: bold;
        padding-left: 1;
        height: 1;
    }
    Sidebar .sb-item-hover {
        color: #89b4fa;
        text-style: bold;
        padding-left: 1;
        height: 1;
        background: #45475a;
    }
    Sidebar .sb-hint {
        color: #6c7086;
        margin-top: 1;
        height: auto;
    }
    """

    def __init__(
        self,
        projects: List[dict] = None,
        current: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.projects = projects or []
        self.current_project = current
        self._focused_mode = False
        self._hover_index = -1

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]wt-board[/]", classes="sb-title")
        yield Static("Projects", id="sb-section-label", classes="sb-section")
        yield Vertical(id="sb-project-list")
        yield Static("[dim]n 추가  x 삭제[/]", classes="sb-hint")

    def on_mount(self) -> None:
        self._render_projects()

    def _render_projects(self) -> None:
        try:
            container = self.query_one("#sb-project-list", Vertical)
        except Exception:
            return
        container.remove_children()
        if not self.projects:
            container.mount(Static(" [dim](none)[/]", classes="sb-item"))
            return
        for i, proj in enumerate(self.projects):
            name = proj.get("name", "")
            if self._focused_mode and i == self._hover_index:
                container.mount(Static(f" [bold cyan]▶[/] {name}", classes="sb-item-hover"))
            elif name == self.current_project:
                container.mount(Static(f" [green]▶[/] {name}", classes="sb-item-current"))
            else:
                container.mount(Static(f"   {name}", classes="sb-item"))

    def set_focused_mode(self, focused: bool, hover_index: int = -1) -> None:
        """Toggle sidebar focus mode with visual feedback."""
        self._focused_mode = focused
        self._hover_index = hover_index
        self.set_class(focused, "focused-mode")
        # Update section label
        try:
            label = self.query_one("#sb-section-label", Static)
            if focused:
                label.update("[bold cyan]Projects ◀[/]")
                label.set_class(True, "sb-section-active")
                label.set_class(False, "sb-section")
            else:
                label.update("Projects")
                label.set_class(False, "sb-section-active")
                label.set_class(True, "sb-section")
        except Exception:
            pass
        self._render_projects()

    def set_hover(self, index: int) -> None:
        """Update which project is hovered."""
        self._hover_index = index
        self._render_projects()

    def refresh_projects(self, projects: List[dict], current: str) -> None:
        """Rebuild the project list."""
        self.projects = projects
        self.current_project = current
        self._render_projects()
