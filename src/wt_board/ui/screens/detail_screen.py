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
from wt_board.models.config import BoardConfig


_STATUS_COLOR = {
    "plan": "#e0a050",
    "implement": "#50a0e0",
    "review": "#c070c0",
    "completed": "#50c070",
}


class DetailScreen(Screen):
    """이슈 상세 — 전체 화면, 에이전트는 background tmux window에서 실행."""

    BINDINGS = [
        Binding("escape", "pop_screen", "뒤로"),
        Binding("r", "run_pipeline", "실행"),
        Binding("m", "move_status", "상태이동"),
        Binding("space", "toggle_tc_item", "TC"),
        Binding("p", "toggle_plan", "Plan"),
        Binding("l", "toggle_worklog", "Log"),
        Binding("t", "toggle_ticket", "Ticket"),
        Binding("c", "toggle_comments", "Comments"),
        Binding("a", "agent_status", "Agent"),
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
        import yaml
        ticket = self.issue.ticket
        for attr, method in [
            ("_checklist", "read_checklist"),
            ("_worklog", "read_worklog"),
            ("_plan", "read_plan"),
            ("_agent", "read_agent"),
            ("_description", "read_description"),
            ("_comments", "read_comments"),
        ]:
            try:
                setattr(self, attr, getattr(self._store, method)(ticket))
            except (FileNotFoundError, yaml.YAMLError, KeyError):
                pass

    def _populate_panel(self) -> None:
        from wt_board.ui.widgets.checklist_widget import ChecklistWidget
        from wt_board.ui.widgets.plan_viewer import PlanViewer

        try:
            panel = self.query_one("#detail-panel")
        except Exception:
            return

        # 순서: Plan → TC → Ticket → Comments → Worklog

        # Plan (open by default)
        panel.mount(Static("[bold]Plan[/] (p)", id="plan-section-header"))
        plan_content = self._plan if self._plan else "m키로 Plan 단계를 실행하세요"
        self._plan_viewer = PlanViewer(plan_content, id="plan-viewer")
        self._plan_viewer.display = True
        panel.mount(self._plan_viewer)

        # TC Checklist
        panel.mount(Static(
            f"[bold]TC[/] (Space) [dim]{self._checklist.progress_str}[/]",
            id="cl-section-header",
        ))
        self._checklist_widget = ChecklistWidget(
            checklist=self._checklist,
            id="checklist-widget",
        )
        panel.mount(self._checklist_widget)

        # Ticket (open by default)
        panel.mount(Static("[bold]Ticket[/] (t)", id="desc-section-header"))
        ticket_empty = "Dooray 티켓 본문이 없습니다. f키로 조회할 수 있습니다."
        self._description_viewer = PlanViewer(
            self._description or ticket_empty,
            id="description-viewer",
        )
        self._description_viewer.display = True
        panel.mount(self._description_viewer)

        # Comments (open by default)
        panel.mount(Static("[bold]Comments[/] (c)", id="comments-section-header"))
        comments_empty = "댓글이 없습니다. f키로 Dooray에서 조회할 수 있습니다."
        self._comments_viewer = PlanViewer(
            self._comments or comments_empty,
            id="comments-viewer",
        )
        self._comments_viewer.display = True
        panel.mount(self._comments_viewer)

        # Worklog (하단, PlanViewer로 렌더링)
        panel.mount(Static("[bold]Worklog[/] (l)", id="worklog-section-header"))
        worklog_md = self._build_worklog_markdown()
        self._worklog_viewer = PlanViewer(
            worklog_md or "작업 기록이 없습니다.",
            id="worklog-viewer",
        )
        self._worklog_viewer.display = True
        panel.mount(self._worklog_viewer)

    def _build_worklog_markdown(self) -> str:
        """Worklog 항목을 마크다운으로 변환."""
        if not self._worklog:
            return ""
        from wt_board.utils import format_short_date
        parts = []
        for entry in reversed(self._worklog):  # 최신 먼저
            at = format_short_date(entry.at) if entry.at else ""
            body = entry.work_done or "(내용 없음)"
            section = f"**{at}**\n\n{body}"
            if entry.next_action:
                section += f"\n\n> → {entry.next_action}"
            parts.append(section)
        return "\n\n---\n\n".join(parts)

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
                parts.append(f"[on green black] {step.label} ✅ [/]")
            elif status == "active":
                parts.append(f"[on cyan black] {step.label} ● [/]")
            else:
                parts.append(f"[on #3a3430] {step.label} [/]")
        return " ".join(parts)

    def _status_chip(self) -> str:
        """현재 상태를 chip으로 렌더링."""
        status = self.issue.pipeline_step or self.issue.status
        color = _STATUS_COLOR.get(status, "white")
        return f"[on {color}] [bold white]{status}[/bold white] [/]"

    def _update_pipeline_header(self) -> None:
        from rich.markup import escape
        safe_title = escape(self.issue.title)
        chip = self._status_chip()
        line1 = f"[bold cyan]#{self.issue.ticket}[/]  {chip}  {safe_title}"
        line2 = ""
        markup = f"{line1}\n{line2}" if line2 else line1
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
        safe_title = escape(self.issue.title)
        chip = self._status_chip()
        title_markup = f"[bold cyan]#{self.issue.ticket}[/]  {chip}  {safe_title}"

        with VerticalScroll(id="detail-panel"):
            yield Static(title_markup, id="detail-header")

        yield Footer()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_pop_screen(self) -> None:
        self.app.pop_screen()

    def action_run_pipeline(self) -> None:
        """r키 — 현재 단계에 맞는 실행 다이얼로그 표시."""
        if self._pipeline_service is None:
            self.notify("파이프라인 서비스가 없습니다.", severity="warning")
            return
        current = self._pipeline_service.current_step(self.issue.ticket)

        if current.name == "plan":
            self._show_plan_dialog()
        elif current.name == "implement":
            self._show_implement_confirm()
        elif current.name == "review":
            self._show_review_dialog()
        elif current.name == "completed":
            self.notify("최종 단계입니다.", severity="information")
        else:
            self.notify(f"알 수 없는 단계: {current.name}", severity="warning")

    def _show_plan_dialog(self) -> None:
        from wt_board.ui.screens.create_dialog import PlanPromptDialog

        def on_result(result) -> None:
            if result is None:
                return
            spec = result["spec"]
            context = result.get("context", "")
            tc = result.get("tc", "")
            ticket = self.issue.ticket
            prompt = f"아래 요구사항을 기반으로 .board/issues/{ticket}/plan.md에 구현 계획을 작성하세요.\n{spec}"
            if context:
                prompt += f"\n\n참고 지식:\n{context}"
            if tc:
                prompt += f"\n\n테스트 케이스도 함께 작성하세요.\n{tc}"
            if self._agent_service:
                def _on_agent_done(t, output):
                    self.app.call_from_thread(self._on_agent_complete, t)

                self._agent_service.run_prompt(ticket, prompt, on_complete=_on_agent_done)
                self.notify("Plan 작성을 시작합니다.", severity="information")

        self.app.push_screen(PlanPromptDialog(), callback=on_result)

    def _show_implement_confirm(self) -> None:
        # Gate check: plan.md must exist
        ok, reason = self._pipeline_service.can_advance(self.issue.ticket)
        if not ok:
            self.notify(reason, severity="warning")
            return

        from wt_board.ui.screens.create_dialog import ImplementConfirmDialog

        def on_result(confirmed) -> None:
            if not confirmed:
                return
            ticket = self.issue.ticket
            prompt = (
                f".board/issues/{ticket}/plan.md를 기반으로 구현을 시작하세요.\n"
                f"작업 완료 후 .board/issues/{ticket}/worklog.jsonl에 기록하세요."
            )
            if self._agent_service:
                def _on_agent_done(t, output):
                    self.app.call_from_thread(self._on_agent_complete, t)

                self._agent_service.run_prompt(ticket, prompt, on_complete=_on_agent_done)
            # Advance pipeline step to implement (already checked gate above)
            self._pipeline_service.advance(self.issue.ticket)
            if self._store:
                self.issue = self._store.read_issue(self.issue.ticket)
            self._update_pipeline_header()
            self.notify("구현을 시작합니다.", severity="information")

        self.app.push_screen(ImplementConfirmDialog(), callback=on_result)

    def _show_review_dialog(self) -> None:
        from wt_board.ui.screens.create_dialog import ReviewPromptDialog

        def on_result(result) -> None:
            if result is None:
                return
            review = result["review"]
            ticket = self.issue.ticket
            prompt = (
                f"아래 수정 요청을 반영하세요.\n{review}\n"
                f"작업 완료 후 .board/issues/{ticket}/worklog.jsonl에 기록하세요."
            )
            if self._agent_service:
                def _on_agent_done(t, output):
                    self.app.call_from_thread(self._on_agent_complete, t)

                self._agent_service.run_prompt(ticket, prompt, on_complete=_on_agent_done)
                self.notify("수정 작업을 시작합니다.", severity="information")

        self.app.push_screen(ReviewPromptDialog(), callback=on_result)

    def _on_agent_complete(self, ticket: str) -> None:
        """Called when agent finishes — reload data and notify."""
        self._load_issue_data()
        worklog_md = self._build_worklog_markdown()
        try:
            self._worklog_viewer.update_content(worklog_md or "작업 기록이 없습니다.")
        except Exception:
            pass
        try:
            plan = self._store.read_plan(self.issue.ticket) if self._store else ""
            if plan:
                self._plan_viewer.update_content(plan)
        except Exception:
            pass
        self._update_pipeline_header()
        self.notify(f"#{ticket} 에이전트 작업 완료.", severity="information")

    def action_agent_status(self) -> None:
        """a키 — 에이전트 상태 + 실시간 로그 확인."""
        if not self._agent_service:
            self.notify("에이전트 서비스 없음.", severity="warning")
            return
        status = self._agent_service.get_status_text(self.issue.ticket)
        # agent.log 마지막 몇 줄 표시
        log_path = self._store.issue_dir(self.issue.ticket) / "agent.log" if self._store else None
        log_preview = ""
        if log_path and log_path.exists():
            try:
                lines = log_path.read_text(encoding="utf-8").strip().split("\n")
                last_lines = lines[-3:] if len(lines) > 3 else lines
                log_preview = "\n".join(last_lines)
            except Exception:
                pass
        msg = f"에이전트: {status}"
        if log_preview:
            msg += f"\n\n최근 출력:\n{log_preview}"
        self.notify(msg, severity="information", timeout=5)

    def action_toggle_plan(self) -> None:
        try:
            self._plan_viewer.display = not self._plan_viewer.display
        except AttributeError:
            pass

    def action_toggle_worklog(self) -> None:
        try:
            self._worklog_viewer.display = not self._worklog_viewer.display
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
        try:
            # 순차 호출 (Textual 메인 스레드에서 위젯 업데이트 보장)
            issue = self._sync_service.sync_issue(ticket)
            self.issue = issue
            self._update_pipeline_header()

            if issue.description:
                self._description = issue.description
                self._description_viewer.update_content(issue.description)

            comments = self._sync_service.sync_comments(ticket)
            if comments:
                self._comments = comments
                self._comments_viewer.update_content(comments)

            self.notify("Dooray 조회 완료", severity="information")
        except Exception as exc:
            self.notify(f"조회 실패: {exc}", severity="error")

