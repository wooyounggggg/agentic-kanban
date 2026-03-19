"""DetailScreen — issue detail with tmux split agent."""

from __future__ import annotations

import os
import subprocess
from typing import List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from wt_board.models.issue import Issue
from wt_board.models.checklist import Checklist
from wt_board.models.worklog import WorklogEntry
from wt_board.models.agent import AgentSession, AgentStatus
from wt_board.models.config import BoardConfig, DEFAULT_STATUSES, StatusDef


_STATUS_COLOR = {
    "planning": "yellow",
    "work": "cyan",
    "review": "magenta",
    "pr": "blue",
    "done": "green",
}


class DetailScreen(Screen):
    """이슈 상세 — 전체 화면 + tmux split으로 왼쪽에 에이전트."""

    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("space", "toggle_tc_item", "TC Toggle"),
        Binding("p", "toggle_plan", "Plan"),
        Binding("l", "toggle_worklog", "Worklog"),
        Binding("d", "toggle_description", "Desc"),
        Binding("c", "toggle_comments", "Comments"),
        Binding("f", "fetch_body", "Fetch"),
        Binding("m", "move_status", "Move"),
        Binding("up,k", "tc_up", "Up", show=False),
        Binding("down,j", "tc_down", "Down", show=False),
    ]

    CSS_PATH = "../styles/detail.tcss"

    def __init__(
        self,
        issue: Issue,
        store=None,
        sync_service=None,
        config: Optional[BoardConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.issue = issue
        self._store = store
        self._sync_service = sync_service
        self._config = config if config is not None else BoardConfig()
        self._checklist = Checklist()
        self._worklog: list = []
        self._plan: str = ""
        self._agent: AgentSession = AgentSession()
        self._description: str = ""
        self._comments: str = ""
        self._agent_pane_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self._load_issue_data()
        self._populate_panel()
        self._open_agent_split()

    def _load_issue_data(self) -> None:
        if self._store is None:
            return
        try:
            self._checklist = self._store.read_checklist(self.issue.ticket)
            self._worklog = self._store.read_worklog(self.issue.ticket)
            self._plan = self._store.read_plan(self.issue.ticket)
            self._agent = self._store.read_agent(self.issue.ticket)
            self._description = self._store.read_description(self.issue.ticket)
            self._comments = self._store.read_comments(self.issue.ticket)
        except Exception:
            pass

    def _populate_panel(self) -> None:
        from wt_board.ui.widgets.checklist_widget import ChecklistWidget
        from wt_board.ui.widgets.plan_viewer import PlanViewer
        from wt_board.ui.widgets.worklog_widget import WorklogWidget

        try:
            panel = self.query_one("#detail-panel")
        except Exception:
            return

        # TC Checklist
        panel.mount(Static(
            f"[bold]TC Checklist[/] [dim]{self._checklist.progress_str}[/]",
            id="cl-section-header",
        ))
        self._checklist_widget = ChecklistWidget(
            checklist=self._checklist,
            on_toggle=self._on_tc_toggle,
            id="checklist-widget",
        )
        panel.mount(self._checklist_widget)

        # Plan (hidden)
        panel.mount(Static("[bold]Plan[/] [dim](p)[/]", id="plan-section-header"))
        self._plan_viewer = PlanViewer(self._plan, id="plan-viewer")
        self._plan_viewer.display = False
        panel.mount(self._plan_viewer)

        # Worklog (hidden)
        panel.mount(Static("[bold]Worklog[/] [dim](l)[/]", id="worklog-section-header"))
        self._worklog_widget = WorklogWidget(self._worklog, id="worklog-widget")
        self._worklog_widget.display = False
        panel.mount(self._worklog_widget)

        # Description (hidden)
        panel.mount(Static("[bold]Description[/] [dim](d)[/]", id="desc-section-header"))
        self._description_viewer = PlanViewer(
            self._description or "[dim]f키로 Dooray에서 조회[/]",
            id="description-viewer",
        )
        self._description_viewer.display = False
        panel.mount(self._description_viewer)

        # Comments (hidden)
        panel.mount(Static("[bold]Comments[/] [dim](c)[/]", id="comments-section-header"))
        self._comments_viewer = PlanViewer(
            self._comments or "[dim]f키로 Dooray에서 조회[/]",
            id="comments-viewer",
        )
        self._comments_viewer.display = False
        panel.mount(self._comments_viewer)

    # ------------------------------------------------------------------
    # Agent split
    # ------------------------------------------------------------------

    def _open_agent_split(self) -> None:
        """tmux split-pane으로 왼쪽에 claude 실행."""
        if not os.environ.get("TMUX"):
            return
        if self._store is None:
            return

        try:
            ticket = self.issue.ticket
            issue = self._store.read_issue(ticket)

            # worktree 경로
            wt_path = issue.worktree.path or ""
            if wt_path:
                from pathlib import Path
                p = Path(wt_path)
                if not p.is_absolute():
                    p = Path(self._store.root.parent) / wt_path
                wt_path = str(p)
            if not wt_path or not os.path.isdir(wt_path):
                wt_path = str(self._store.root.parent)

            # claude 실행 명령어 구성
            binary = self._config.agent.binary
            plan = self._store.read_plan(ticket)
            plan_note = f" Implementation plan: .board/issues/{ticket}/plan.md." if plan else ""
            prompt = (
                f"You are working on #{ticket}: {issue.title}.{plan_note} "
                f"After meaningful work, append to .board/issues/{ticket}/worklog.jsonl"
            )
            safe_prompt = prompt.replace("'", "'\\''").replace('"', '\\"')

            # claude "prompt" 형태로 interactive 실행
            cmd = f'cd \\"{wt_path}\\" && {binary} \\"{safe_prompt}\\"'

            # tmux split: 왼쪽으로, 50%
            result = subprocess.run(
                ["tmux", "split-window", "-hb", "-l", "50%", "-c", wt_path,
                 binary, safe_prompt],
                capture_output=True, text=True,
            )

            if result.returncode == 0:
                # pane ID 획득
                pid_r = subprocess.run(
                    ["tmux", "display-message", "-t", "{left}", "-p", "#{pane_id}"],
                    capture_output=True, text=True,
                )
                self._agent_pane_id = pid_r.stdout.strip() if pid_r.returncode == 0 else None

                # agent.yaml 갱신
                from wt_board.models.agent import AgentSession, AgentStatus
                agent = AgentSession(status=AgentStatus.ACTIVE, tmux_pane=self._agent_pane_id or "")
                self._store.write_agent(ticket, agent)
                self._agent = agent

        except Exception:
            pass

    # ------------------------------------------------------------------
    # Layout — 전체 화면 한 패널
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()

        from rich.markup import escape
        status_color = _STATUS_COLOR.get(self.issue.status, "white")
        safe_title = escape(self.issue.title)
        title_markup = (
            f"[bold cyan]#{self.issue.ticket}[/]  "
            f"{safe_title}  "
            f"[{status_color}]{self.issue.status}[/{status_color}]"
        )

        with VerticalScroll(id="detail-panel"):
            yield Static(title_markup, id="detail-header")

        yield Footer()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_pop_screen(self) -> None:
        self.app.pop_screen()

    def action_toggle_plan(self) -> None:
        try:
            self._plan_viewer.display = not self._plan_viewer.display
        except AttributeError:
            pass

    def action_toggle_worklog(self) -> None:
        try:
            self._worklog_widget.display = not self._worklog_widget.display
        except AttributeError:
            pass

    def action_toggle_tc_item(self) -> None:
        try:
            self._checklist_widget.toggle_focused()
            if self._store:
                self._store.write_checklist(self.issue.ticket, self._checklist)
            self.query_one("#cl-section-header", Static).update(
                f"[bold]TC Checklist[/] [dim]{self._checklist.progress_str}[/]"
            )
        except AttributeError:
            pass

    def action_tc_up(self) -> None:
        try:
            self._checklist_widget.move_up()
        except AttributeError:
            pass

    def action_tc_down(self) -> None:
        try:
            self._checklist_widget.move_down()
        except AttributeError:
            pass

    def action_toggle_description(self) -> None:
        try:
            self._description_viewer.display = not self._description_viewer.display
        except AttributeError:
            pass

    def action_toggle_comments(self) -> None:
        try:
            self._comments_viewer.display = not self._comments_viewer.display
        except AttributeError:
            pass

    def action_fetch_body(self) -> None:
        if self._sync_service is None:
            self.notify("Dooray 연동이 설정되지 않았습니다.", severity="warning")
            return
        ticket = self.issue.ticket
        try:
            issue = self._sync_service.sync_issue(ticket)
            self.issue = issue
            if issue.description:
                self._description = issue.description
                try:
                    self._description_viewer.update_content(issue.description)
                    self._description_viewer.display = True
                except AttributeError:
                    pass
            comments = self._sync_service.sync_comments(ticket)
            if comments:
                self._comments = comments
                try:
                    self._comments_viewer.update_content(comments)
                    self._comments_viewer.display = True
                except AttributeError:
                    pass
            self.notify("Dooray 조회 완료.", severity="information")
        except Exception as exc:
            self.notify(f"조회 실패: {exc}", severity="error")

    def action_move_status(self) -> None:
        statuses = self._config.statuses or list(DEFAULT_STATUSES)
        if self._config.transitions:
            allowed_names = self._config.transitions.get(self.issue.status, [])
            targets = [s for s in statuses if s.name in allowed_names]
        else:
            targets = [s for s in statuses if s.name != self.issue.status]
        if not targets:
            self.notify("이동 가능한 상태가 없습니다.", severity="warning")
            return

        from wt_board.ui.screens.create_dialog import MoveDialog

        def on_result(new_status: Optional[str]) -> None:
            if new_status is None:
                return
            if self._store is None:
                return
            try:
                from wt_board.services.issue_service import IssueService
                svc = IssueService(self._store, self._config)
                self.issue = svc.move_issue(self.issue.ticket, new_status)
                from rich.markup import escape
                status_color = _STATUS_COLOR.get(new_status, "white")
                self.query_one("#detail-header", Static).update(
                    f"[bold cyan]#{self.issue.ticket}[/]  "
                    f"{escape(self.issue.title)}  "
                    f"[{status_color}]{new_status}[/{status_color}]"
                )
                self.notify(f"상태 이동: {new_status}", severity="information")
            except Exception as exc:
                self.notify(f"이동 실패: {exc}", severity="error")

        self.app.push_screen(
            MoveDialog(
                ticket=self.issue.ticket,
                current_status=self.issue.status,
                target_statuses=targets,
            ),
            callback=on_result,
        )

    def _on_tc_toggle(self, item) -> None:
        pass
