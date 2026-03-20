"""AgentService: run claude as background subprocess, capture output."""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
from typing import Callable, Dict, Optional

from wt_board.models.agent import AgentSession, AgentStatus
from wt_board.models.config import BoardConfig
from wt_board.store.board_store import BoardStore
from wt_board.utils import now_iso


class AgentService:
    def __init__(self, store: BoardStore, config: BoardConfig) -> None:
        self._store = store
        self._config = config
        self._running: Dict[str, subprocess.Popen] = {}  # ticket -> process

    def run_prompt(
        self,
        ticket: str,
        prompt: str,
        on_complete: Optional[Callable[[str, str], None]] = None,
        save_as: str = "",
    ) -> bool:
        """Run claude --print with prompt in background.

        Args:
            ticket: issue ticket number
            prompt: the decorated prompt to send
            on_complete: callback(ticket, output) when done

        Returns True if started successfully.
        """
        wt_path = self._resolve_worktree_path(ticket)
        binary = self._config.agent.binary

        agent = AgentSession(status=AgentStatus.ACTIVE, started_at=now_iso())
        self._store.write_agent(ticket, agent)

        def _worker():
            try:
                result = subprocess.run(
                    [binary, "--print", "--dangerously-skip-permissions", prompt],
                    cwd=wt_path,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 min timeout
                )
                output = result.stdout.strip()

                # save_as가 지정되면 출력을 해당 파일에 저장
                if save_as and output:
                    save_path = self._store.issue_dir(ticket) / save_as
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    save_path.write_text(output, encoding="utf-8")

                self._save_worklog(ticket, prompt, output)

                agent_done = AgentSession(
                    status=AgentStatus.COMPLETED,
                    started_at=agent.started_at,
                    last_heartbeat=now_iso(),
                )
                self._store.write_agent(ticket, agent_done)

                if on_complete:
                    on_complete(ticket, output)

            except subprocess.TimeoutExpired:
                agent_err = AgentSession(
                    status=AgentStatus.ERROR, last_heartbeat=now_iso()
                )
                self._store.write_agent(ticket, agent_err)
            except Exception:
                agent_err = AgentSession(
                    status=AgentStatus.ERROR, last_heartbeat=now_iso()
                )
                self._store.write_agent(ticket, agent_err)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return True

    def _save_worklog(self, ticket: str, prompt: str, output: str) -> None:
        """Save a worklog entry summarizing the agent's work."""
        from wt_board.models.worklog import WorklogEntry, append_worklog

        summary = self._summarize_output(output)

        entry = WorklogEntry(
            at=now_iso(),
            author="agent",
            work_done=summary,
            next_action="",
        )
        worklog_path = self._store.issue_dir(ticket) / "worklog.jsonl"
        append_worklog(worklog_path, entry)

    def _summarize_output(self, output: str) -> str:
        """Extract bullet-point summary from claude output."""
        if not output:
            return "(출력 없음)"

        lines = output.strip().split("\n")
        bullets = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("- ") or line.startswith("* ") or line.startswith("• "):
                bullets.append(line)
            elif line.startswith("#"):
                bullets.append(f"- {line.lstrip('#').strip()}")
            elif len(bullets) < 5 and len(line) > 10:
                bullets.append(f"- {line}")

            if len(bullets) >= 7:
                break

        if not bullets:
            return output[:200] + ("..." if len(output) > 200 else "")

        return "\n".join(bullets)

    def _resolve_worktree_path(self, ticket: str) -> str:
        """Resolve absolute worktree path for a ticket."""
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
        return str(fallback.resolve()) if fallback.exists() else str(project_root)

    def is_running(self, ticket: str) -> bool:
        """Check if agent is currently running for this ticket."""
        agent = self._store.read_agent(ticket)
        return agent.status == AgentStatus.ACTIVE

    def check_alive(self, ticket: str) -> bool:
        return self.is_running(ticket)
