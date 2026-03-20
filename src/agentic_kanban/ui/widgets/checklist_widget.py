"""ChecklistWidget — interactive TC checklist with Space-to-toggle."""

from __future__ import annotations

from typing import Callable, List, Optional

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static
from textual.containers import Vertical

from agentic_kanban.models.checklist import Checklist, ChecklistItem


_TYPE_ICON = {
    "verify": "[cyan]V[/]",
    "todo": "[yellow]T[/]",
    "manual": "[magenta]M[/]",
}

_STATUS_BOX = {
    "done": "[green]\u2713[/]",
    "skip": "[dim]\u2014[/]",
    "open": "[ ]",
}


class ChecklistWidget(Vertical):
    """Scrollable, keyboard-navigable checklist.

    Parameters
    ----------
    checklist:
        The :class:`Checklist` model to display.
    on_toggle:
        Optional callback invoked with the toggled :class:`ChecklistItem`
        after its status is flipped.
    """

    DEFAULT_CSS = """
    ChecklistWidget {
        height: auto;
        max-height: 20;
        overflow-y: auto;
    }

    ChecklistWidget .cl-item {
        padding: 0 1;
        height: 1;
    }
    """

    focused_index: reactive[int] = reactive(0)

    def __init__(
        self,
        checklist: Checklist,
        on_toggle: Optional[Callable[[ChecklistItem], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.checklist = checklist
        self._on_toggle = on_toggle

    def compose(self) -> ComposeResult:
        if not self.checklist.items:
            yield Static("[dim]No checklist items.[/]")
            return
        for idx, item in enumerate(self.checklist.items):
            yield self._make_item_widget(idx, item)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_item_widget(self, idx: int, item: ChecklistItem) -> Static:
        box = _STATUS_BOX.get(item.status, "[ ]")
        icon = _TYPE_ICON.get(item.type, "")
        text = f"{box} {icon} {item.target}"
        if item.note:
            text += f" [dim italic]({item.note})[/]"

        classes = "cl-item"
        if idx == self.focused_index:
            classes += " cl-selected"
        if item.is_done:
            classes += " cl-done"

        return Static(text, classes=classes, id=f"cl-{item.id}")

    def _refresh_items(self) -> None:
        """Re-mount all item widgets with fresh state."""
        self.remove_children()
        if not self.checklist.items:
            self.mount(Static("[dim]No checklist items.[/]"))
            return
        for idx, item in enumerate(self.checklist.items):
            self.mount(self._make_item_widget(idx, item))

    # ------------------------------------------------------------------
    # Keyboard navigation (called by parent screen)
    # ------------------------------------------------------------------

    def move_up(self) -> None:
        if self.checklist.items and self.focused_index > 0:
            self.focused_index -= 1
            self._refresh_items()

    def move_down(self) -> None:
        if self.checklist.items and self.focused_index < len(self.checklist.items) - 1:
            self.focused_index += 1
            self._refresh_items()

    def toggle_focused(self) -> None:
        """Toggle the focused item's done/open status."""
        if not self.checklist.items:
            return
        idx = self.focused_index
        if idx < 0 or idx >= len(self.checklist.items):
            return
        item = self.checklist.items[idx]
        item.toggle()
        self._refresh_items()
        if self._on_toggle:
            self._on_toggle(item)
