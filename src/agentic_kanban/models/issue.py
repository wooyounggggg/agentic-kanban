"""Issue data model."""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List

from agentic_kanban.utils import now_iso


@dataclass
class WorktreeInfo:
    path: str = ""
    branch: str = ""
    base_branch: str = "develop"


@dataclass
class TrackerInfo:
    type: str = "dooray"
    post_id: str = ""
    url: str = ""
    remote_status: str = ""


@dataclass
class Issue:
    ticket: str = ""
    title: str = ""
    status: str = "planning"
    priority: int = 99
    created_at: str = ""
    updated_at: str = ""
    worktree: WorktreeInfo = field(default_factory=WorktreeInfo)
    tracker: TrackerInfo = field(default_factory=TrackerInfo)
    labels: List[str] = field(default_factory=list)
    description: str = ""
    assignee: str = ""
    pipeline_step: str = "plan"

    @classmethod
    def from_yaml(cls, path: Path) -> "Issue":
        """Load issue from a YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        wt = data.pop("worktree", {}) or {}
        tr = data.pop("tracker", {}) or {}

        return cls(
            ticket=str(data.get("ticket", "")),
            title=data.get("title", ""),
            status=data.get("status", "planning"),
            priority=data.get("priority", 99),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            worktree=WorktreeInfo(**wt),
            tracker=TrackerInfo(**tr),
            labels=data.get("labels", []),
            description=data.get("description", ""),
            assignee=data.get("assignee", ""),
            pipeline_step=data.get("pipeline_step", "plan"),
        )

    def to_yaml(self, path: Path) -> None:
        """Save issue to a YAML file."""
        data = {
            "ticket": self.ticket,
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "worktree": asdict(self.worktree),
            "tracker": asdict(self.tracker),
            "labels": self.labels,
            "description": self.description,
            "assignee": self.assignee,
            "pipeline_step": self.pipeline_step,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def touch_updated(self) -> None:
        self.updated_at = now_iso()
