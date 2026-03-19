"""DetailScreen — issue detail with pipeline-based execution."""

from __future__ import annotations

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
    """이슈 상세 — 전체 화면, 에이전트는 background tmux window에서 실행."""

    BINDINGS = [
        Binding("escape", "pop_screen", "뒤로"),
        Binding("m", "advance_pipeline", "다음단계"),
        Binding("r", "rerun_pipeline", "재실행"),
        Binding("a", "focus_agent", "세션보기"),
        Binding("space", "toggle_tc_item", "TC Toggle"),
        Binding("p", "toggle_plan", "Plan"),
        Binding("l", "toggle_worklog", "Worklog"),
        Binding("t", "toggle_ticket", "Ticket"),
        Binding("c", "toggle_comments", "Comments"),
        Binding("f", "fetch_body", "Fetch"),
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
        pipeline_service=None,
        agent_service=None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.issue = issue
        self._store = store
        self._sync_service = sync_service
        self._config = config if config is not None else BoardConfig()
        self._pipeline_service = pipeline_service
        self._agent_service = agent_service
        self._checklist = Checklist()
        self._worklog: list = []
        self._plan: str = ""
        self._agent: AgentSession = AgentSession()
        self._description: str = ""
        self._comments: str = ""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self._load_issue_data()
        self._populate_panel()
        self._update_pipeline_header()

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
            f"[bold]TC[/] (Space) [dim]{self._checklist.progress_str}[/]",
            id="cl-section-header",
        ))
        self._checklist_widget = ChecklistWidget(
            checklist=self._checklist,
            on_toggle=self._on_tc_toggle,
            id="checklist-widget",
        )
        panel.mount(self._checklist_widget)

        # Plan (open by default)
        panel.mount(Static("[bold]Plan[/] (p)", id="plan-section-header"))
        plan_content = self._plan if self._plan else "m키로 Plan 단계를 실행하세요"
        self._plan_viewer = PlanViewer(plan_content, id="plan-viewer")
        self._plan_viewer.display = True
        panel.mount(self._plan_viewer)

        # Worklog (open by default)
        panel.mount(Static("[bold]Worklog[/] (l)", id="worklog-section-header"))
        self._worklog_widget = WorklogWidget(self._worklog, id="worklog-widget")
        self._worklog_widget.display = True
        panel.mount(self._worklog_widget)

        # Ticket (open by default)
        panel.mount(Static("[bold]Ticket[/] (t)", id="desc-section-header"))
        self._description_viewer = PlanViewer(
            self._description or "f키로 Dooray에서 조회",
            id="description-viewer",
        )
        self._description_viewer.display = True
        panel.mount(self._description_viewer)

        # Comments (open by default)
        panel.mount(Static("[bold]Comments[/] (c)", id="comments-section-header"))
        self._comments_viewer = PlanViewer(
            self._comments or "f키로 Dooray에서 조회",
            id="comments-viewer",
        )
        self._comments_viewer.display = True
        panel.mount(self._comments_viewer)

    def _pipeline_bar(self) -> str:
        if self._pipeline_service is None:
            return ""
        try:
            steps = self._pipeline_service.step_statuses(self.issue.ticket)
        except Exception:
            return ""
        parts = []
        for step, status in steps:
            if status == "done":
                parts.append(f"[green]{step.label} ✓[/]")
            elif status == "active":
                parts.append(f"[cyan]{step.label} ●[/]")
            else:
                parts.append(f"[dim]{step.label}[/]")
        return "  ".join(parts)

    def _update_pipeline_header(self) -> None:
        from rich.markup import escape
        status_color = _STATUS_COLOR.get(self.issue.status, "white")
        safe_title = escape(self.issue.title)
        pipeline_bar = self._pipeline_bar()
        pipeline_part = f"  {pipeline_bar}" if pipeline_bar else ""
        markup = (
            f"[bold cyan]#{self.issue.ticket}[/]  "
            f"{safe_title}  "
            f"[{status_color}]{self.issue.status}[/{status_color}]"
            f"{pipeline_part}"
        )
        try:
            self.query_one("#detail-header", Static).update(markup)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Layout
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

    def action_advance_pipeline(self) -> None:
        """m → 다음 파이프라인 단계로 이동."""
        if self._pipeline_service is None:
            self.notify("파이프라인 서비스가 없습니다.", severity="warning")
            return
        try:
            ok, reason = self._pipeline_service.advance(self.issue.ticket)
            if ok:
                # Reload issue to get updated pipeline_step
                if self._store:
                    self.issue = self._store.read_issue(self.issue.ticket)
                self._update_pipeline_header()
                self.notify(reason, severity="information")
            else:
                self.notify(reason, severity="warning")
        except Exception as exc:
            self.notify(f"파이프라인 오류: {exc}", severity="error")

    def action_rerun_pipeline(self) -> None:
        """r → 현재 단계 재실행."""
        if self._pipeline_service is None:
            self.notify("파이프라인 서비스가 없습니다.", severity="warning")
            return
        try:
            self._pipeline_service.rerun(self.issue.ticket)
            if self._pipeline_service:
                current = self._pipeline_service.current_step(self.issue.ticket)
                self.notify(
                    f"{current.label} 단계를 에이전트에 재전송했습니다.",
                    severity="information",
                )
        except Exception as exc:
            self.notify(f"재실행 오류: {exc}", severity="error")

    def action_focus_agent(self) -> None:
        """a → 에이전트 tmux window로 포커스 전환."""
        if self._agent_service is None:
            self.notify("에이전트 서비스가 없습니다.", severity="warning")
            return
        try:
            ok, reason = self._agent_service.focus_agent(self.issue.ticket)
            if not ok:
                self.notify(f"세션 전환 실패: {reason}", severity="warning")
        except Exception as exc:
            self.notify(f"에이전트 오류: {exc}", severity="error")

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
                f"[bold]TC[/] (Space) [dim]{self._checklist.progress_str}[/]"
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

    def action_toggle_ticket(self) -> None:
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
        self.notify("Dooray 조회 중...", severity="information")
        # 비동기 대신 스레드로 병렬 호출
        import concurrent.futures
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                issue_future = pool.submit(self._sync_service.sync_issue, ticket)
                comments_future = pool.submit(self._sync_service.sync_comments, ticket)
                issue = issue_future.result(timeout=30)
                comments = comments_future.result(timeout=30)

            self.issue = issue
            self._update_pipeline_header()

            # 본문은 description 뷰어에 표시
            if issue.description:
                self._description = issue.description
                try:
                    self._description_viewer.update_content(issue.description)
                    self._description_viewer.display = True
                except AttributeError:
                    pass

            # 댓글은 comments 뷰어에 별도 표시
            if comments:
                self._comments = comments
                try:
                    self._comments_viewer.update_content(comments)
                    self._comments_viewer.display = True
                except AttributeError:
                    pass

            self.notify("Dooray 조회 완료", severity="information")
        except Exception as exc:
            self.notify(f"조회 실패: {exc}", severity="error")

    def _on_tc_toggle(self, item) -> None:
        pass
