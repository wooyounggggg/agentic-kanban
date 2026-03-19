"""Checklist (TC) data model."""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from wt_board.utils import now_iso


@dataclass
class ChecklistItem:
    id: int = 0
    type: str = "todo"  # verify | todo | manual
    target: str = ""
    note: str = ""
    status: str = "open"  # open | done | skip
    updated_at: str = ""

    @property
    def is_done(self) -> bool:
        return self.status == "done"

    def toggle(self) -> None:
        self.status = "done" if self.status == "open" else "open"
        self.updated_at = now_iso()


@dataclass
class Checklist:
    items: List[ChecklistItem] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> "Checklist":
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        raw_items = data.get("items", [])
        items = [ChecklistItem(**item) for item in raw_items]
        return cls(items=items)

    def to_yaml(self, path: Path) -> None:
        data = {
            "items": [
                {
                    "id": item.id,
                    "type": item.type,
                    "target": item.target,
                    "note": item.note,
                    "status": item.status,
                    "updated_at": item.updated_at,
                }
                for item in self.items
            ]
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    @property
    def done_count(self) -> int:
        return sum(1 for item in self.items if item.is_done)

    @property
    def total_count(self) -> int:
        return len(self.items)

    @property
    def progress_str(self) -> str:
        if not self.items:
            return ""
        return f"{self.done_count}/{self.total_count}"

    def next_id(self) -> int:
        if not self.items:
            return 1
        return max(item.id for item in self.items) + 1

    def add(self, target: str, type_: str = "todo", note: str = "") -> ChecklistItem:
        item = ChecklistItem(
            id=self.next_id(),
            type=type_,
            target=target,
            note=note,
            status="open",
            updated_at=now_iso(),
        )
        self.items.append(item)
        return item

    def get(self, item_id: int) -> Optional[ChecklistItem]:
        for item in self.items:
            if item.id == item_id:
                return item
        return None
