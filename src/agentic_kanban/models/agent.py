"""Agent session data model."""

from __future__ import annotations

import yaml
from dataclasses import dataclass
from pathlib import Path


class AgentStatus:
    IDLE = "idle"
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentSession:
    status: str = AgentStatus.IDLE
    pid: int = 0
    tmux_pane: str = ""
    wt_key: str = ""
    started_at: str = ""
    last_heartbeat: str = ""

    @classmethod
    def from_yaml(cls, path: Path) -> "AgentSession":
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(
            status=data.get("status", AgentStatus.IDLE),
            pid=data.get("pid", 0),
            tmux_pane=data.get("tmux_pane", ""),
            wt_key=data.get("wt_key", ""),
            started_at=data.get("started_at", ""),
            last_heartbeat=data.get("last_heartbeat", ""),
        )

    def to_yaml(self, path: Path) -> None:
        data = {
            "status": self.status,
            "pid": self.pid,
            "tmux_pane": self.tmux_pane,
            "wt_key": self.wt_key,
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    @property
    def is_active(self) -> bool:
        return self.status == AgentStatus.ACTIVE
