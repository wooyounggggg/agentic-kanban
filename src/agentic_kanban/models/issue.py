"""Issue data model."""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List

from agentic_kanban.utils import now_iso
from agentic_kanban.models.config import StepName


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
    status: str = StepName.PLAN  # 칸반 상태 = pipeline_step (단일 소스)
    priority: int = 99
    created_at: str = ""
    updated_at: str = ""
    worktree: WorktreeInfo = field(default_factory=WorktreeInfo)
    tracker: TrackerInfo = field(default_factory=TrackerInfo)
    labels: List[str] = field(default_factory=list)
    description: str = ""
    assignee: str = ""

    @property
    def pipeline_step(self) -> str:
        return self.status

    @pipeline_step.setter
    def pipeline_step(self, value: str) -> None:
        self.status = value

    @classmethod
    def from_yaml(cls, path: Path) -> "Issue":
        """Load issue from a YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        wt = data.pop("worktree", {}) or {}
        tr = data.pop("tracker", {}) or {}

        # pipeline_step 우선, 없으면 status, 없으면 기본값
        status = data.get("pipeline_step") or data.get("status") or StepName.PLAN

        return cls(
            ticket=str(data.get("ticket", "")),
            title=data.get("title", ""),
            status=status,
            priority=data.get("priority", 99),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            worktree=WorktreeInfo(**wt),
            tracker=TrackerInfo(**tr),
            labels=data.get("labels", []),
            description=data.get("description", ""),
            assignee=data.get("assignee", ""),
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
