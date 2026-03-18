"""Board configuration model."""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class StatusDef:
    name: str = ""
    label: str = ""
    icon: str = ""
    terminal: bool = False


DEFAULT_STATUSES = [
    StatusDef(name="planning", label="Planning", icon="\U0001f4dd"),
    StatusDef(name="work", label="Work", icon="\U0001f528"),
    StatusDef(name="review", label="Review", icon="\U0001f4cb"),
    StatusDef(name="pr", label="PR", icon="\U0001f500"),
    StatusDef(name="done", label="Done", icon="\u2705", terminal=True),
]


@dataclass
class DoorayConfig:
    cli_path: str = "~/.mcp-global-server/dooray-cli.js"
    project_id: str = ""
    api_key: str = ""


@dataclass
class TrackerConfig:
    type: str = "dooray"
    dooray: DoorayConfig = field(default_factory=DoorayConfig)
    sync_interval: int = 60
    auto_sync: bool = True


@dataclass
class AgentConfig:
    binary: str = "claude"
    max_concurrent: int = 3
    prompt_template: str = (
        "You are working on #{ticket}: {title}\n"
        "Worktree: {worktree_path}\n"
        "Read .board/issues/{ticket}/plan.md for details."
    )


@dataclass
class ProjectConfig:
    name: str = ""
    worktree_base: str = "worktrees"
    branch_prefix: str = "feature-"
    base_branch: str = "develop"


@dataclass
class BoardConfig:
    project: ProjectConfig = field(default_factory=ProjectConfig)
    statuses: List[StatusDef] = field(default_factory=lambda: list(DEFAULT_STATUSES))
    transitions: Dict[str, List[str]] = field(default_factory=dict)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> "BoardConfig":
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        config = cls()

        # Project
        proj = data.get("project", {})
        if proj:
            config.project = ProjectConfig(
                name=proj.get("name", ""),
                worktree_base=proj.get("worktree_base", "worktrees"),
                branch_prefix=proj.get("branch_prefix", "feature-"),
                base_branch=proj.get("base_branch", "develop"),
            )

        # Statuses
        raw_statuses = data.get("statuses")
        if raw_statuses:
            config.statuses = [
                StatusDef(
                    name=s.get("name", ""),
                    label=s.get("label", ""),
                    icon=s.get("icon", ""),
                    terminal=s.get("terminal", False),
                )
                for s in raw_statuses
            ]

        # Transitions
        config.transitions = data.get("transitions", {})

        # Tracker
        tr = data.get("tracker", {})
        if tr:
            dooray_raw = tr.get("dooray", {})
            config.tracker = TrackerConfig(
                type=tr.get("type", "dooray"),
                dooray=DoorayConfig(
                    cli_path=dooray_raw.get("cli_path", "~/.mcp-global-server/dooray-cli.js"),
                    project_id=dooray_raw.get("project_id", ""),
                    api_key=dooray_raw.get("api_key", ""),
                ),
                sync_interval=tr.get("sync_interval", 60),
                auto_sync=tr.get("auto_sync", True),
            )

        # Agent
        ag = data.get("agent", {})
        if ag:
            config.agent = AgentConfig(
                binary=ag.get("binary", "claude"),
                max_concurrent=ag.get("max_concurrent", 3),
                prompt_template=ag.get("prompt_template", config.agent.prompt_template),
            )

        return config

    def to_yaml(self, path: Path) -> None:
        data = {
            "project": {
                "name": self.project.name,
                "worktree_base": self.project.worktree_base,
                "branch_prefix": self.project.branch_prefix,
                "base_branch": self.project.base_branch,
            },
            "statuses": [
                {
                    "name": s.name,
                    "label": s.label,
                    "icon": s.icon,
                    **({"terminal": True} if s.terminal else {}),
                }
                for s in self.statuses
            ],
        }
        if self.transitions:
            data["transitions"] = self.transitions
        data["tracker"] = {
            "type": self.tracker.type,
            "dooray": {
                "cli_path": self.tracker.dooray.cli_path,
                "project_id": self.tracker.dooray.project_id,
            },
            "sync_interval": self.tracker.sync_interval,
            "auto_sync": self.tracker.auto_sync,
        }
        if self.tracker.dooray.api_key:
            data["tracker"]["dooray"]["api_key"] = self.tracker.dooray.api_key
        data["agent"] = {
            "binary": self.agent.binary,
            "max_concurrent": self.agent.max_concurrent,
            "prompt_template": self.agent.prompt_template,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def status_names(self) -> List[str]:
        return [s.name for s in self.statuses]

    def get_status_def(self, name: str) -> Optional[StatusDef]:
        for s in self.statuses:
            if s.name == name:
                return s
        return None

    def is_valid_transition(self, from_status: str, to_status: str) -> bool:
        """Check if transition is valid. If no transitions defined, allow all."""
        if not self.transitions:
            return True
        allowed = self.transitions.get(from_status, [])
        return to_status in allowed
