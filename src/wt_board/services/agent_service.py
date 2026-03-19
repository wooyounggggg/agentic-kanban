"""AgentService: launch / stop / focus AI agents via tmux."""

from __future__ import annotations

import os
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
        self._cached_session: Optional[str] = None

    # ------------------------------------------------------------------
    # tmux helpers
    # ------------------------------------------------------------------

    def _run(self, args: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(args, capture_output=True, text=True)

    def _current_tmux_session(self) -> Optional[str]:
        """현재 프로세스가 속한 tmux 세션 이름을 반환. tmux 밖이면 None."""
        tmux_env = os.environ.get("TMUX", "")
        if not tmux_env:
            return None
        # $TMUX = /tmp/tmux-501/default,PID,PANE_INDEX
        # 소켓 경로로 세션 찾기 (display-message는 Textual 터미널과 충돌)
        parts = tmux_env.split(",")
        if len(parts) < 2:
            return None
        socket_path = parts[0]
        # tmux -S <socket> list-sessions 로 세션 이름 획득
        result = self._run(["tmux", "-S", socket_path, "list-sessions", "-F", "#{session_name}"])
        if result.returncode == 0 and result.stdout.strip():
            # 여러 세션이 있을 수 있음 — TMUX_PANE으로 현재 세션 특정
            sessions = result.stdout.strip().split("\n")
            if len(sessions) == 1:
                return sessions[0]
            # 여러 세션이면 pane ID로 찾기
            tmux_pane = os.environ.get("TMUX_PANE", "")
            if tmux_pane:
                for sess in sessions:
                    check = self._run([
                        "tmux", "-S", socket_path, "list-panes",
                        "-t", sess, "-a", "-F", "#{pane_id}"
                    ])
                    if check.returncode == 0 and tmux_pane in check.stdout:
                        return sess
            return sessions[0]
        return None

    def _session_name(self) -> str:
        """에이전트 window를 생성할 tmux 세션. 현재 세션 우선, 없으면 별도 생성."""
        if self._cached_session:
            return self._cached_session
        current = self._current_tmux_session()
        if current:
            self._cached_session = current
            return current
        name = self._config.project.name or "wt-board"
        fallback = f"wtb-{name}".replace(".", "-")
        self._cached_session = fallback
        return fallback

    def _window_target(self, ticket: str) -> str:
        return f"{self._session_name()}:agent-{ticket}"

    def _window_exists(self, ticket: str) -> bool:
        session = self._session_name()
        result = self._run(["tmux", "list-windows", "-t", session, "-F", "#{window_name}"])
        if result.returncode != 0:
            return False
        window_name = f"agent-{ticket}"
        return window_name in result.stdout.strip().split("\n")

    def _ensure_session(self) -> str:
        """tmux 세션이 존재하는지 확인. 현재 세션이면 아무것도 안 함."""
        session = self._session_name()
        current = self._current_tmux_session()
        if current and current == session:
            return session  # 이미 안에 있음
        check = self._run(["tmux", "has-session", "-t", session])
        if check.returncode != 0:
            self._run(["tmux", "new-session", "-d", "-s", session, "-x", "200", "-y", "50"])
        return session

    def _pid_alive(self, pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def _resolve_worktree_path(self, ticket: str) -> str:
        issue = self._store.read_issue(ticket)
        wt_path = issue.worktree.path
        if wt_path:
            p = Path(wt_path)
            if p.is_absolute() and p.exists():
                return str(p)
            project_root = self._store.root.parent
            candidate = project_root / wt_path
            if candidate.exists():
                return str(candidate.resolve())
        project_root = self._store.root.parent
        base = self._config.project.worktree_base
        fallback = project_root / base / f"feature-{ticket}"
        return str(fallback.resolve()) if fallback.exists() else str(fallback)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_agent(self, ticket: str) -> AgentSession:
        """에이전트 시작. 현재 tmux 세션에 window 생성 → claude 실행."""
        existing = self._store.read_agent(ticket)
        if existing.status == AgentStatus.ACTIVE and self._window_exists(ticket):
            return existing

        session = self._ensure_session()
        wt_path = self._resolve_worktree_path(ticket)
        wt_key = _new_wt_key()
        window_name = f"agent-{ticket}"
        target = f"{session}:{window_name}"

        # 기존 window 정리
        if self._window_exists(ticket):
            self._run(["tmux", "kill-window", "-t", target])

        # 새 window 생성
        self._run(["tmux", "new-window", "-t", session, "-n", window_name, "-d"])

        # claude 명령 전송
        issue = self._store.read_issue(ticket)
        binary = self._config.agent.binary
        plan = self._store.read_plan(ticket)
        plan_hint = f" Plan: .board/issues/{ticket}/plan.md" if plan else ""

        prompt = (
            f"#{ticket}: {issue.title}.{plan_hint} "
            f"Worklog: .board/issues/{ticket}/worklog.jsonl"
        )
        safe_prompt = prompt.replace("'", "'\\''")
        cmd = f"cd '{wt_path}' && {binary} --print '{safe_prompt}'"
        self._run(["tmux", "send-keys", "-t", target, cmd, "Enter"])

        # PID 기록
        result = self._run(["tmux", "display-message", "-t", target, "-p", "#{pane_pid}"])
        try:
            pid = int(result.stdout.strip())
        except ValueError:
            pid = 0

        agent = AgentSession(
            status=AgentStatus.ACTIVE,
            pid=pid,
            tmux_pane=target,
            wt_key=wt_key,
            started_at=_now_iso(),
            last_heartbeat=_now_iso(),
        )
        self._store.write_agent(ticket, agent)
        return agent

    def resume_agent(self, ticket: str) -> AgentSession:
        """에이전트 resume. window가 살아있으면 재연결, 아니면 새로 시작."""
        if self._window_exists(ticket):
            # window 존재 → active로 갱신
            agent = self._store.read_agent(ticket)
            target = self._window_target(ticket)
            result = self._run(["tmux", "display-message", "-t", target, "-p", "#{pane_pid}"])
            try:
                pid = int(result.stdout.strip())
            except ValueError:
                pid = agent.pid
            agent.status = AgentStatus.ACTIVE
            agent.pid = pid
            agent.tmux_pane = target
            agent.last_heartbeat = _now_iso()
            self._store.write_agent(ticket, agent)
            return agent
        return self.start_agent(ticket)

    def focus_agent(self, ticket: str) -> Tuple[bool, str]:
        """에이전트 window로 포커스 전환. (성공여부, 사유) 반환."""
        if not self._window_exists(ticket):
            return False, "agent window가 존재하지 않습니다"

        target = self._window_target(ticket)

        # select-window는 항상 시도 (같은 세션이든 아니든)
        result = self._run(["tmux", "select-window", "-t", target])
        if result.returncode == 0:
            return True, "selected"

        # select-window 실패 시 switch-client 시도
        result = self._run(["tmux", "switch-client", "-t", target])
        if result.returncode == 0:
            return True, "switched"

        return False, f"tmux 전환 실패: {result.stderr.strip()}"

    def stop_agent(self, ticket: str) -> None:
        """에이전트 종료."""
        target = self._window_target(ticket)
        if self._window_exists(ticket):
            self._run(["tmux", "kill-window", "-t", target])
        agent = self._store.read_agent(ticket)
        agent.status = AgentStatus.COMPLETED
        agent.pid = 0
        agent.tmux_pane = ""
        self._store.write_agent(ticket, agent)

    def check_alive(self, ticket: str) -> bool:
        return self._window_exists(ticket)

    def monitor_all(self) -> Dict[str, AgentSession]:
        result: Dict[str, AgentSession] = {}
        for ticket in self._store.list_issues():
            agent = self._store.read_agent(ticket)
            if agent.status == AgentStatus.ACTIVE and not self._window_exists(ticket):
                agent.status = AgentStatus.COMPLETED
                agent.last_heartbeat = _now_iso()
                self._store.write_agent(ticket, agent)
            result[ticket] = agent
        return result

    def list_active(self) -> Dict[str, AgentSession]:
        all_agents = self.monitor_all()
        return {t: a for t, a in all_agents.items() if a.status == AgentStatus.ACTIVE}
