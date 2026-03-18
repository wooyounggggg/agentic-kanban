"""AgentService: launch / stop / focus AI agents via tmux."""

from __future__ import annotations

import os
import subprocess
import uuid
from datetime import datetime
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
        """Return the tmux session name derived from the project name."""
        name = self._config.project.name or "wt-board"
        return f"wtb-{name}"

    def _pane_target(self, ticket: str) -> str:
        return f"{self._tmux_session()}:{ticket}"

    def _run(self, args: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(args, capture_output=True, text=True)

    def _pid_alive(self, pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def _build_launch_command(self, ticket: str, wt_path: str) -> str:
        """Build the shell command string to launch the agent inside tmux."""
        issue = self._store.read_issue(ticket)
        prompt = self._config.agent.prompt_template.format(
            ticket=ticket,
            title=issue.title,
            worktree_path=wt_path,
        )
        binary = self._config.agent.binary
        # Escape single-quotes in the prompt
        safe_prompt = prompt.replace("'", "'\\''")
        return f"cd '{wt_path}' && {binary} '{safe_prompt}'"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_agent(self, ticket: str) -> AgentSession:
        """Create a tmux pane, launch the agent, and persist the session.

        Returns the updated :class:`AgentSession`.
        """
        issue = self._store.read_issue(ticket)
        wt_path = issue.worktree.path or str(
            self._store.root.parent
            / self._config.project.worktree_base
            / f"feature-{ticket}"
        )

        session = self._tmux_session()
        pane_target = self._pane_target(ticket)
        wt_key = _new_wt_key()

        # Ensure tmux session exists
        check = self._run(["tmux", "has-session", "-t", session])
        if check.returncode != 0:
            self._run(["tmux", "new-session", "-d", "-s", session])

        # Create a new window named after the ticket (idempotent)
        self._run(["tmux", "new-window", "-t", session, "-n", ticket])

        # Run the agent command in the new pane
        cmd = self._build_launch_command(ticket, wt_path)
        self._run(["tmux", "send-keys", "-t", pane_target, cmd, "Enter"])

        # Retrieve the PID of the pane's shell process
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

    def stop_agent(self, ticket: str) -> None:
        """Kill the agent process and close its tmux pane."""
        agent = self._store.read_agent(ticket)

        if agent.pid > 0:
            try:
                import signal
                os.kill(agent.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass

        if agent.tmux_pane:
            self._run(["tmux", "kill-pane", "-t", agent.tmux_pane])

        agent.status = AgentStatus.COMPLETED
        agent.pid = 0
        self._store.write_agent(ticket, agent)

    def focus_agent(self, ticket: str) -> None:
        """Switch tmux focus to the agent pane for *ticket*."""
        agent = self._store.read_agent(ticket)
        if not agent.tmux_pane:
            raise RuntimeError(f"No tmux pane recorded for ticket {ticket}")
        self._run(["tmux", "select-pane", "-t", agent.tmux_pane])
        self._run(["tmux", "switch-client", "-t", agent.tmux_pane])

    def check_alive(self, ticket: str) -> bool:
        """Return True if the agent process for *ticket* is still running."""
        agent = self._store.read_agent(ticket)
        return self._pid_alive(agent.pid)

    def monitor_all(self) -> Dict[str, AgentSession]:
        """Check all agents; mark dead ones as completed.

        Returns the updated ``{ticket: AgentSession}`` map.
        """
        result: Dict[str, AgentSession] = {}
        for ticket in self._store.list_issues():
            agent = self._store.read_agent(ticket)
            if agent.status == AgentStatus.ACTIVE and not self._pid_alive(agent.pid):
                agent.status = AgentStatus.COMPLETED
                agent.last_heartbeat = _now_iso()
                self._store.write_agent(ticket, agent)
            result[ticket] = agent
        return result
