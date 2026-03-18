"""Worklog data model (JSONL format)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List


@dataclass
class WorklogEntry:
    at: str = ""
    author: str = "human"  # human | agent
    work_done: str = ""
    next_action: str = ""

    def to_json_line(self) -> str:
        return json.dumps(
            {
                "at": self.at,
                "author": self.author,
                "work_done": self.work_done,
                "next_action": self.next_action,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "WorklogEntry":
        return cls(
            at=data.get("at", ""),
            author=data.get("author", "human"),
            work_done=data.get("work_done", ""),
            next_action=data.get("next_action", ""),
        )


def read_worklog(path: Path) -> List[WorklogEntry]:
    """Read all worklog entries from a JSONL file."""
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entries.append(WorklogEntry.from_dict(data))
            except json.JSONDecodeError:
                continue
    return entries


def append_worklog(path: Path, entry: WorklogEntry) -> None:
    """Append a single worklog entry to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry.to_json_line() + "\n")
