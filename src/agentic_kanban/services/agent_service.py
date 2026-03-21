"""AgentService: run claude as background subprocess, capture output."""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
from typing import Callable, Dict, Optional

from agentic_kanban.models.agent import AgentSession, AgentStatus
from agentic_kanban.models.config import BoardConfig
from agentic_kanban.store.board_store import BoardStore
from agentic_kanban.utils import now_iso


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

        # stdout을 실시간 로그 파일에 기록
        log_path = self._store.issue_dir(ticket) / "agent.log"
        log_file = open(log_path, "w", encoding="utf-8")
        # 프롬프트를 로그 상단에 기록
        log_file.write(f"**프롬프트:**\n{prompt}\n\n---\n\n")
        log_file.flush()

        # PTY로 실시간 stdout (파이프 버퍼링 우회)
        import pty
        master_fd, slave_fd = pty.openpty()

        cmd = [binary, "--print", "--dangerously-skip-permissions",
               "--verbose", "--output-format", "stream-json", prompt]

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=wt_path,
                stdout=slave_fd,
                stderr=subprocess.PIPE,
                text=False,
            )
        except Exception:
            try:
                os.close(slave_fd)
            except OSError:
                pass
            try:
                os.close(master_fd)
            except OSError:
                pass
            try:
                log_file.close()
            except Exception:
                pass
            raise
        os.close(slave_fd)  # 부모는 slave 닫음

        agent = AgentSession(
            status=AgentStatus.ACTIVE,
            pid=proc.pid,
            started_at=now_iso(),
        )
        self._store.write_agent(ticket, agent)

        def _worker():
            try:
                import json as _json
                import select
                output_parts = []
                buf = b""

                while True:
                    # master_fd에서 읽기 (프로세스 종료 시 EOF)
                    try:
                        ready, _, _ = select.select([master_fd], [], [], 1.0)
                        if ready:
                            chunk = os.read(master_fd, 4096)
                            if not chunk:
                                break
                            buf += chunk
                            # 줄 단위 파싱
                            while b"\n" in buf:
                                line_bytes, buf = buf.split(b"\n", 1)
                                line = line_bytes.decode("utf-8", errors="replace").strip()
                                if not line:
                                    continue
                                try:
                                    obj = _json.loads(line)
                                    msg_type = obj.get("type", "")
                                    if msg_type == "assistant":
                                        content = obj.get("message", {}).get("content", [])
                                        for block in content:
                                            if block.get("type") == "text":
                                                text = block.get("text", "")
                                                if text:
                                                    output_parts.append(text)
                                                    log_file.write(text)
                                                    log_file.flush()
                                    elif msg_type == "result":
                                        result_text = obj.get("result", "")
                                        if result_text:
                                            output_parts.append(result_text)
                                            log_file.write(result_text)
                                            log_file.flush()
                                except _json.JSONDecodeError:
                                    continue
                        # 프로세스 종료 확인
                        if proc.poll() is not None and not ready:
                            break
                    except OSError:
                        break

                proc.wait()
                output = "\n".join(output_parts).strip()

                self._save_worklog(ticket, prompt, output)

                agent_done = AgentSession(
                    status=AgentStatus.COMPLETED,
                    pid=0,
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
            finally:
                try:
                    os.close(master_fd)
                except OSError:
                    pass
                try:
                    log_file.close()
                except Exception:
                    pass

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return True

    def _save_worklog(self, ticket: str, prompt: str, output: str) -> None:
        """Save a worklog entry summarizing the agent's work."""
        from agentic_kanban.models.worklog import WorklogEntry, append_worklog

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
        base_path = Path(base).expanduser()
        if base_path.is_absolute():
            fallback = base_path / f"feature-{ticket}"
        else:
            fallback = project_root / base / f"feature-{ticket}"
        return str(fallback.resolve()) if fallback.exists() else str(project_root)

    def is_running(self, ticket: str) -> bool:
        """Check if agent process is actually alive."""
        agent = self._store.read_agent(ticket)
        if agent.status != AgentStatus.ACTIVE:
            return False
        if agent.pid > 0:
            try:
                os.kill(agent.pid, 0)
                return True
            except (ProcessLookupError, PermissionError):
                # PID dead but status still active → fix it
                agent.status = AgentStatus.COMPLETED
                agent.last_heartbeat = now_iso()
                self._store.write_agent(ticket, agent)
                return False
        return False

    def get_status_text(self, ticket: str) -> str:
        """사람이 읽을 수 있는 에이전트 상태."""
        agent = self._store.read_agent(ticket)
        if agent.status == AgentStatus.ACTIVE and agent.pid > 0:
            try:
                os.kill(agent.pid, 0)
                # 실행 시간 계산
                from datetime import datetime
                started = datetime.fromisoformat(agent.started_at) if agent.started_at else None
                if started:
                    elapsed = datetime.now().astimezone() - started
                    mins = int(elapsed.total_seconds() // 60)
                    return f"실행중 ({mins}분 경과, PID {agent.pid})"
                return f"실행중 (PID {agent.pid})"
            except (ProcessLookupError, PermissionError):
                return "완료"
        if agent.status == AgentStatus.COMPLETED:
            return "완료"
        if agent.status == AgentStatus.ERROR:
            return "오류"
        return "대기"

