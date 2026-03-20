"""File watcher that emits callbacks when .board/ files change."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

# Map file basenames to their logical type label
_FILE_TYPE_MAP = {
    "issue.yaml": "issue",
    "checklist.yaml": "checklist",
    "worklog.jsonl": "worklog",
    "agent.yaml": "agent",
    "plan.md": "plan",
}


def _parse_event_path(board_path: Path, event_path: str):
    """Return ``(ticket, file_type)`` for *event_path*, or ``(None, None)``."""
    try:
        rel = Path(event_path).relative_to(board_path)
    except ValueError:
        return None, None

    parts = rel.parts
    # Expected layout: issues/<ticket>/<file>
    if len(parts) != 3 or parts[0] != "issues":
        return None, None

    ticket = parts[1]
    file_name = parts[2]
    file_type = _FILE_TYPE_MAP.get(file_name)
    if file_type is None:
        return None, None

    return ticket, file_type


class _BoardEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        board_path: Path,
        on_change: Callable[[str, str], None],
    ) -> None:
        super().__init__()
        self._board_path = board_path
        self._on_change = on_change

    def _dispatch_if_relevant(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        ticket, file_type = _parse_event_path(self._board_path, event.src_path)
        if ticket is not None:
            self._on_change(ticket, file_type)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._dispatch_if_relevant(event)

    def on_created(self, event: FileSystemEvent) -> None:
        self._dispatch_if_relevant(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        # Fire for the destination path so callers see the new location
        if event.is_directory:
            return
        ticket, file_type = _parse_event_path(self._board_path, event.dest_path)
        if ticket is not None:
            self._on_change(ticket, file_type)


class BoardFileWatcher:
    """Watch ``.board/issues/`` and invoke a callback when tracked files change.

    Parameters
    ----------
    board_path:
        Absolute path to the ``.board/`` directory.
    on_change:
        Called with ``(ticket: str, file_type: str)`` whenever a watched file
        is created or modified.  *file_type* is one of
        ``'issue'``, ``'checklist'``, ``'worklog'``, ``'agent'``, ``'plan'``.
    """

    def __init__(
        self,
        board_path: Path,
        on_change: Callable[[str, str], None],
    ) -> None:
        self._board_path = Path(board_path).resolve()
        self._on_change = on_change
        self._handler = _BoardEventHandler(self._board_path, on_change)
        self._observer: Observer = Observer()

    def start(self) -> None:
        """Start watching.  Safe to call multiple times (no-op if already running)."""
        if self._observer.is_alive():
            return
        watch_dir = self._board_path / "issues"
        watch_dir.mkdir(parents=True, exist_ok=True)
        self._observer.schedule(self._handler, str(watch_dir), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        """Stop watching and join the background thread."""
        if self._observer.is_alive():
            self._observer.stop()
            self._observer.join()
