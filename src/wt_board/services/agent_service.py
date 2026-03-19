"""AgentService: launch / stop / focus AI agents via tmux."""

from __future__ import annotations

import os
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from wt_board.models.agent import AgentSession, AgentStatus
from wt_board.models.config import BoardConfig
from wt_board.store.board_store import BoardStore


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _new_wt_key() -> str:
    return uuid.uuid4().hex[:8]


class AgentService:
    def __init__(self, store: BoardStore, config: BoardConfig) -> None:
        self._store = store
        self._config = config

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _tmux_session(self) -> str:
        name = self._config.project.name or "wt-board"
        # tmux session names can't have dots
        return f"wtb-{name}".replace(".", "-")

    def _pane_target(self, ticket: str) -> str:
        return f"{self._tmux_session()}:{ticket}"

    def _run(self, args: List[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.run(args, capture_output=True, text=True, **kwargs)

    def _pid_alive(self, pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def _resolve_worktree_path(self, ticket: str) -> str:
        """Resolve absolute worktree path for a ticket."""
        issue = self._store.read_issue(ticket)
        wt_path = issue.worktree.path
        if wt_path:
            p = Path(wt_path)
            if p.is_absolute() and p.exists():
                return str(p)
            # Try relative to project root
            project_root = self._store.root.parent
            candidate = project_root / wt_path
            if candidate.exists():
                return str(candidate.resolve())
        # Fallback: construct from config
        project_root = self._store.root.parent
        base = self._config.project.worktree_base
        fallback = project_root / base / f"feature-{ticket}"
        return str(fallback.resolve()) if fallback.exists() else str(fallback)

    def _ensure_tmux_session(self) -> None:
        """Ensure the tmux session exists."""
        session = self._tmux_session()
        check = self._run(["tmux", "has-session", "-t", session])
        if check.returncode != 0:
            self._run(["tmux", "new-session", "-d", "-s", session, "-x", "200", "-y", "50"])

    def _window_exists(self, ticket: str) -> bool:
        """Check if a tmux window for this ticket already exists."""
        session = self._tmux_session()
        result = self._run(["tmux", "list-windows", "-t", session, "-F", "#{window_name}"])
        if result.returncode != 0:
            return False
        return ticket in result.stdout.strip().split("\n")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_agent(self, ticket: str) -> AgentSession:
        """Start a claude agent in a tmux window for this ticket.

        If the agent is already active, just return the existing session.
        """
        # Check if already running
        existing = self._store.read_agent(ticket)
        if existing.status == AgentStatus.ACTIVE and self._pid_alive(existing.pid):
            return existing

        wt_path = self._resolve_worktree_path(ticket)
        session = self._tmux_session()
        pane_target = self._pane_target(ticket)
        wt_key = _new_wt_key()

        self._ensure_tmux_session()

        # Create a new window or reuse existing
        if self._window_exists(ticket):
            # Kill the existing window and recreate
            self._run(["tmux", "kill-window", "-t", pane_target])

        self._run(["tmux", "new-window", "-t", session, "-n", ticket])

        # Build and send the claude command
        issue = self._store.read_issue(ticket)
        binary = self._config.agent.binary

        # Read plan.md if exists for context
        plan = self._store.read_plan(ticket)
        plan_hint = ""
        if plan:
            plan_hint = f"\\nImplementation plan is at .board/issues/{ticket}/plan.md"

        prompt = (
            f"You are working on #{ticket}: {issue.title}\\n"
            f"Worktree: {wt_path}{plan_hint}\\n"
            f"Read .board/issues/{ticket}/plan.md for implementation details.\\n"
            f"After meaningful work, append to .board/issues/{ticket}/worklog.jsonl"
        )

        # cd to worktree, then launch claude with --print for initial prompt
        cmd = f"cd '{wt_path}' && {binary} --print '{prompt}'"
        self._run(["tmux", "send-keys", "-t", pane_target, cmd, "Enter"])

        # Get the pane PID
        result = self._run(
            ["tmux", "display-message", "-t", pane_target, "-p", "#{pane_pid}"]
        )
        try:
            pid = int(result.stdout.strip())
        except ValueError:
            pid = 0

        agent = AgentSession(
            status=AgentStatus.ACTIVE,
            pid=pid,
            tmux_pane=pane_target,
            wt_key=wt_key,
            started_at=_now_iso(),
            last_heartbeat=_now_iso(),
        )
        self._store.write_agent(ticket, agent)
        return agent

    def resume_agent(self, ticket: str) -> AgentSession:
        """Resume/reconnect to an agent. If active, return it. Otherwise start fresh."""
        existing = self._store.read_agent(ticket)

        # Already active and alive?
        if existing.status == AgentStatus.ACTIVE:
            if self._pid_alive(existing.pid):
                return existing
            # Window might still exist even if PID changed
            if existing.tmux_pane and self._window_exists(ticket):
                # Re-check PID from tmux
                result = self._run(
                    ["tmux", "display-message", "-t", existing.tmux_pane, "-p", "#{pane_pid}"]
                )
                try:
                    new_pid = int(result.stdout.strip())
                    if new_pid > 0:
                        existing.pid = new_pid
                        existing.last_heartbeat = _now_iso()
                        self._store.write_agent(ticket, existing)
                        return existing
                except ValueError:
                    pass

        # Not active — start fresh
        return self.start_agent(ticket)

    def stop_agent(self, ticket: str) -> None:
        """Kill the agent process and close its tmux window."""
        agent = self._store.read_agent(ticket)

        if agent.tmux_pane:
            self._run(["tmux", "kill-window", "-t", agent.tmux_pane])

        agent.status = AgentStatus.COMPLETED
        agent.pid = 0
        agent.tmux_pane = ""
        self._store.write_agent(ticket, agent)

    def focus_agent(self, ticket: str) -> bool:
        """Switch tmux client focus to the agent's window. Returns True if successful."""
        agent = self._store.read_agent(ticket)
        if not agent.tmux_pane:
            return False

        # Try switch-client first (for attached sessions)
        result = self._run(["tmux", "select-window", "-t", agent.tmux_pane])
        if result.returncode == 0:
            self._run(["tmux", "switch-client", "-t", self._tmux_session()])
            return True
        return False

    def check_alive(self, ticket: str) -> bool:
        """Return True if the agent process for *ticket* is still running."""
        agent = self._store.read_agent(ticket)
        if not self._pid_alive(agent.pid):
            # Also check if tmux window still exists
            if agent.tmux_pane and self._window_exists(ticket):
                return True
            return False
        return True

    def monitor_all(self) -> Dict[str, AgentSession]:
        """Check all agents; mark dead ones as completed."""
        result: Dict[str, AgentSession] = {}
        for ticket in self._store.list_issues():
            agent = self._store.read_agent(ticket)
            if agent.status == AgentStatus.ACTIVE:
                if not self.check_alive(ticket):
                    agent.status = AgentStatus.COMPLETED
                    agent.last_heartbeat = _now_iso()
                    self._store.write_agent(ticket, agent)
            result[ticket] = agent
        return result

    def list_active(self) -> Dict[str, AgentSession]:
        """Return only active agent sessions."""
        all_agents = self.monitor_all()
        return {t: a for t, a in all_agents.items() if a.status == AgentStatus.ACTIVE}
