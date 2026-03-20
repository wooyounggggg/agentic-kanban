from __future__ import annotations
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional

def now_iso() -> str:
    return datetime.now().astimezone().isoformat()

def format_short_date(iso: str) -> str:
    try:
        return iso.replace("T", " ")[:16]
    except Exception:
        return iso

def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def save_yaml(path: Path, data: dict, **kwargs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, **kwargs)

DEFAULT_PRIORITY = 99
