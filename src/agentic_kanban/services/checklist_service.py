"""ChecklistService: manage checklist items for issues."""

from __future__ import annotations

from agentic_kanban.models.checklist import Checklist, ChecklistItem
from agentic_kanban.store.board_store import BoardStore


class ChecklistService:
    def __init__(self, store: BoardStore) -> None:
        self._store = store

    def toggle_item(self, ticket: str, item_id: int) -> ChecklistItem:
        """Toggle the done/open status of *item_id* on *ticket*'s checklist.

        Returns the updated :class:`ChecklistItem`.

        Raises
        ------
        KeyError
            If *item_id* does not exist in the checklist.
        """
        checklist = self._store.read_checklist(ticket)
        item = checklist.get(item_id)
        if item is None:
            raise KeyError(f"Checklist item {item_id} not found for ticket {ticket}")
        item.toggle()
        self._store.write_checklist(ticket, checklist)
        return item

    def add_item(
        self, ticket: str, target: str, type_: str = "todo"
    ) -> ChecklistItem:
        """Add a new checklist item to *ticket* and return it."""
        checklist = self._store.read_checklist(ticket)
        item = checklist.add(target=target, type_=type_)
        self._store.write_checklist(ticket, checklist)
        return item

    def get_progress(self, ticket: str) -> str:
        """Return a progress string like ``'3/7'`` for *ticket*'s checklist."""
        checklist = self._store.read_checklist(ticket)
        return checklist.progress_str or "0/0"
