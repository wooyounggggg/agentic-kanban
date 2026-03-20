"""Migrate from legacy ``.wt-state/`` format to the new ``.board/`` format."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from agentic_kanban.models.issue import Issue, WorktreeInfo
from agentic_kanban.models.worklog import WorklogEntry, append_worklog
from agentic_kanban.store.board_store import BoardStore
from agentic_kanban.utils import now_iso

# ---------------------------------------------------------------------------
# Status mapping: old mode → new Issue.status
# ---------------------------------------------------------------------------
# Observed old modes: work, review, idle, done, planning, discussion
# Specification mapping: work→work, review→review, idle→planning, done→done,
# planning→planning.  "discussion" is treated as "planning" (closest equivalent).
_MODE_TO_STATUS: Dict[str, str] = {
    "work": "work",
    "review": "review",
    "idle": "planning",
    "done": "done",
    "planning": "planning",
    "discussion": "planning",
}

_DEFAULT_STATUS = "planning"


def _map_status(mode: str) -> str:
    return _MODE_TO_STATUS.get(mode, _DEFAULT_STATUS)


# ---------------------------------------------------------------------------
# Helpers for reading old formats
# ---------------------------------------------------------------------------

def _read_mode_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _read_wt_titles(project_root: Path) -> Dict[str, str]:
    """Load ``worktrees/.wt-titles.json`` and return a ``{ticket_id: title}`` dict."""
    titles_path = project_root / "worktrees" / ".wt-titles.json"
    if not titles_path.exists():
        return {}
    try:
        with open(titles_path, "r", encoding="utf-8") as f:
            raw = json.load(f) or {}
        # Keys may be ints when loaded from JSON; normalise to str
        return {str(k): str(v) for k, v in raw.items()}
    except (json.JSONDecodeError, OSError):
        return {}


def _read_old_worklog(path: Path) -> List[dict]:
    """Read a legacy ``worklog.json`` (JSON array) and return raw dicts."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _extract_ticket(worktree_dir: Path, branch_prefix: str = "feature-") -> Optional[str]:
    """Extract the ticket ID from a worktree directory name.

    E.g. ``feature-3373`` → ``3373``.
    """
    name = worktree_dir.name
    if name.startswith(branch_prefix):
        return name[len(branch_prefix):]
    return None


# ---------------------------------------------------------------------------
# Public migration entry-point
# ---------------------------------------------------------------------------

def migrate_from_wt_state(
    project_root: Path,
    board_path: Path,
    branch_prefix: str = "feature-",
) -> List[str]:
    """Migrate ``worktrees/feature-*/`` directories to ``.board/``.

    For each ``worktrees/<branch_prefix><ticket>/`` that has a ``.wt-state/``
    subdirectory:

    * Reads ``.wt-state/mode.json`` → creates ``issue.yaml`` (with status
      mapping and priority).
    * Reads ``.wt-state/plan.md``   → copies to ``plan.md``.
    * Reads ``.wt-state/worklog.json`` (JSON array, camelCase fields) →
      converts to ``worklog.jsonl`` (JSONL, snake_case fields).
    * Uses ``worktrees/.wt-titles.json`` to populate the issue title.

    Parameters
    ----------
    project_root:
        Root directory of the project (the directory that contains
        ``worktrees/``).
    board_path:
        Path to the target ``.board/`` directory (will be created if absent).
    branch_prefix:
        Prefix used by worktree directories, default ``"feature-"``.

    Returns
    -------
    List[str]
        Ticket IDs that were successfully migrated.
    """
    project_root = Path(project_root).resolve()
    board_path = Path(board_path).resolve()

    store = BoardStore(board_path)
    store.ensure_dirs()

    titles = _read_wt_titles(project_root)
    worktrees_dir = project_root / "worktrees"

    migrated: List[str] = []

    if not worktrees_dir.is_dir():
        return migrated

    for wt_dir in sorted(worktrees_dir.iterdir()):
        if not wt_dir.is_dir():
            continue

        ticket = _extract_ticket(wt_dir, branch_prefix)
        if ticket is None:
            continue

        wt_state = wt_dir / ".wt-state"
        if not wt_state.is_dir():
            continue

        _migrate_one(
            ticket=ticket,
            wt_dir=wt_dir,
            wt_state=wt_state,
            store=store,
            titles=titles,
        )
        migrated.append(ticket)

    return migrated


def _migrate_one(
    ticket: str,
    wt_dir: Path,
    wt_state: Path,
    store: BoardStore,
    titles: Dict[str, str],
) -> None:
    """Migrate a single worktree's ``.wt-state/`` to the board store."""
    now = now_iso()

    # ------------------------------------------------------------------ issue
    mode_data = _read_mode_json(wt_state / "mode.json")
    old_mode = mode_data.get("mode", "idle")
    status = _map_status(old_mode)
    priority = mode_data.get("priority", 99)
    if priority is None:
        priority = 99

    title = titles.get(ticket, "")
    entered_at = mode_data.get("enteredAt", "") or mode_data.get("updatedAt", "") or now

    issue = Issue(
        ticket=ticket,
        title=title,
        status=status,
        priority=priority,
        created_at=entered_at,
        updated_at=entered_at,
        worktree=WorktreeInfo(
            path=str(wt_dir),
            branch=f"feature-{ticket}",
        ),
    )
    store.write_issue(ticket, issue)

    # ------------------------------------------------------------------- plan
    plan_path = wt_state / "plan.md"
    if plan_path.exists():
        content = plan_path.read_text(encoding="utf-8")
        store.write_plan(ticket, content)

    # ---------------------------------------------------------------- worklog
    raw_entries = _read_old_worklog(wt_state / "worklog.json")
    worklog_path = store.issue_dir(ticket) / "worklog.jsonl"
    for raw in raw_entries:
        entry = WorklogEntry(
            at=raw.get("at", now),
            author=raw.get("author", "human"),
            # Old format uses camelCase; fall back to snake_case just in case
            work_done=raw.get("workDone") or raw.get("work_done", ""),
            next_action=raw.get("nextAction") or raw.get("next_action", ""),
        )
        append_worklog(worklog_path, entry)
