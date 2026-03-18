"""Sidebar widget with project list and actions."""

from __future__ import annotations

from typing import List, Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Static


class ProjectSelected(Message):
    """Emitted when the user selects a different project."""

    def __init__(self, name: str, path: str) -> None:
        super().__init__()
        self.name = name
        self.path = path


class Sidebar(Vertical):
    """Left sidebar showing project list."""

    DEFAULT_CSS = """
    Sidebar {
        width: 20;
        height: 100%;
        background: #161b22;
        border-right: solid #30363d;
        padding: 1;
    }
    Sidebar .sb-title {
        color: #58a6ff;
        text-style: bold;
        padding: 0 0 1 0;
    }
    Sidebar .sb-section {
        color: #6e7681;
        text-style: italic;
        height: 1;
        margin-top: 1;
    }
    Sidebar .sb-item {
        color: #c9d1d9;
        padding-left: 1;
        height: 1;
    }
    Sidebar .sb-item-active {
        color: #58a6ff;
        text-style: bold;
        padding-left: 1;
        height: 1;
    }
    Sidebar .sb-hint {
        color: #6e7681;
        margin-top: 1;
        height: 1;
    }
    """

    def __init__(
        self,
        projects: List[dict] = None,
        current: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.projects = projects or []  # [{"name": ..., "path": ...}]
        self.current_project = current

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]wt-board[/]", classes="sb-title")
        yield Static("Projects", classes="sb-section")

        if not self.projects:
            yield Static(" [dim](none)[/]", classes="sb-item")
        else:
            for proj in self.projects:
                name = proj.get("name", "")
                if name == self.current_project:
                    yield Static(f" [green]▶[/] {name}", classes="sb-item-active", id=f"proj-{name}")
                else:
                    yield Static(f"   {name}", classes="sb-item", id=f"proj-{name}")

        yield Static("[dim]P add  S switch[/]", classes="sb-hint")

    def refresh_projects(self, projects: List[dict], current: str) -> None:
        """Rebuild the project list."""
        self.projects = projects
        self.current_project = current
        self.remove_children()
        for widget in self.compose():
            self.mount(widget)
