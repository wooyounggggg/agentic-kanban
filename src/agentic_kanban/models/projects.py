"""Multi-project registry stored at ~/.config/agentic-kanban/projects.yaml."""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ProjectEntry:
    name: str = ""
    path: str = ""  # absolute path to project root (where .kanban/ lives)


@dataclass
class ProjectRegistry:
    projects: List[ProjectEntry] = field(default_factory=list)
    current: str = ""  # name of the active project

    @classmethod
    def config_path(cls) -> Path:
        return Path.home() / ".config" / "agentic-kanban" / "projects.yaml"

    @classmethod
    def load(cls) -> "ProjectRegistry":
        path = cls.config_path()
        if not path.exists():
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError):
            return cls()
        projects = [
            ProjectEntry(name=p.get("name", ""), path=p.get("path", ""))
            for p in data.get("projects", [])
        ]
        return cls(projects=projects, current=data.get("current", ""))

    def save(self) -> None:
        path = self.config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "projects": [{"name": p.name, "path": p.path} for p in self.projects],
            "current": self.current,
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def add(self, name: str, path: str) -> ProjectEntry:
        """Add a project. If name exists, update path."""
        for p in self.projects:
            if p.name == name:
                p.path = path
                self.save()
                return p
        entry = ProjectEntry(name=name, path=str(Path(path).resolve()))
        self.projects.append(entry)
        if not self.current:
            self.current = name
        self.save()
        return entry

    def switch(self, name: str) -> Optional[ProjectEntry]:
        """Switch to a project by name. Returns the entry or None."""
        for p in self.projects:
            if p.name == name:
                self.current = name
                self.save()
                return p
        return None

    def get_current(self) -> Optional[ProjectEntry]:
        for p in self.projects:
            if p.name == self.current:
                return p
        return None

    def names(self) -> List[str]:
        return [p.name for p in self.projects]

    def remove(self, name: str) -> bool:
        before = len(self.projects)
        self.projects = [p for p in self.projects if p.name != name]
        if self.current == name:
            self.current = self.projects[0].name if self.projects else ""
        if len(self.projects) < before:
            self.save()
            return True
        return False
