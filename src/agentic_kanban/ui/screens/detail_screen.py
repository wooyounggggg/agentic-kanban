"""DetailScreen — issue detail with pipeline-based execution."""

from __future__ import annotations

from typing import List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from agentic_kanban.models.issue import Issue
from agentic_kanban.models.checklist import Checklist
from agentic_kanban.models.worklog import WorklogEntry
from agentic_kanban.models.agent import AgentSession, AgentStatus
from agentic_kanban.models.config import BoardConfig


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
        Binding("a", "toggle_agent", "Agent"),
        Binding("p", "toggle_plan", "Plan"),
        Binding("t", "toggle_ticket", "Ticket"),
        Binding("c", "toggle_comments", "Comments"),
        Binding("l", "toggle_worklog", "Log"),
        Binding("f", "fetch_body", "Fetch"),
        Binding("A", "expand_section('agent')", show=False),
        Binding("P", "expand_section('plan')", show=False),
        Binding("T", "expand_section('ticket')", show=False),
        Binding("C", "expand_section('comments')", show=False),
        Binding("L", "expand_section('worklog')", show=False),
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
        self._agent_refresh_timer = self.set_interval(1, self._refresh_agent_viewer)

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
        from agentic_kanban.ui.widgets.checklist_widget import ChecklistWidget
        from agentic_kanban.ui.widgets.plan_viewer import PlanViewer

        try:
            panel = self.query_one("#detail-panel")
        except Exception:
            return

        # 순서: Agent → Plan → TC → Ticket → Comments → Worklog

        # Agent log (live)
        agent_status = ""
        if self._agent_service and self._agent_service.is_running(self.issue.ticket):
            agent_status = " [bold #8fac6e]⟳ 작업중...[/]"
        panel.mount(Static(f"[bold]Agent[/] (a) [dim]A:확대[/]{agent_status}", id="agent-section-header"))
        agent_log = self._read_agent_log()
        self._agent_viewer = PlanViewer(
            agent_log or "에이전트가 실행되지 않았습니다.",
            id="agent-viewer",
        )
        self._agent_viewer.display = True  # visible by default
        panel.mount(self._agent_viewer)

        # Plan (open by default)
        panel.mount(Static("[bold]Plan[/] (p) [dim]P:확대[/]", id="plan-section-header"))
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
        panel.mount(Static("[bold]Ticket[/] (t) [dim]T:확대[/]", id="desc-section-header"))
        ticket_empty = "Dooray 티켓 본문이 없습니다. f키로 조회할 수 있습니다."
        self._description_viewer = PlanViewer(
            self._description or ticket_empty,
            id="description-viewer",
        )
        self._description_viewer.display = True
        panel.mount(self._description_viewer)

        # Comments (open by default)
        panel.mount(Static("[bold]Comments[/] (c) [dim]C:확대[/]", id="comments-section-header"))
        comments_empty = "댓글이 없습니다. f키로 Dooray에서 조회할 수 있습니다."
        self._comments_viewer = PlanViewer(
            self._comments or comments_empty,
            id="comments-viewer",
        )
        self._comments_viewer.display = True
        panel.mount(self._comments_viewer)

        # Worklog (하단, PlanViewer로 렌더링)
        panel.mount(Static("[bold]Worklog[/] (l) [dim]L:확대[/]", id="worklog-section-header"))
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
        from agentic_kanban.utils import format_short_date
        parts = []
        for entry in reversed(self._worklog):  # 최신 먼저
            at = format_short_date(entry.at) if entry.at else ""
            body = entry.work_done or "(내용 없음)"
            section = f"**{at}**\n\n{body}"
            if entry.next_action:
                section += f"\n\n> → {entry.next_action}"
            parts.append(section)
        return "\n\n---\n\n".join(parts)

    def _read_agent_log(self) -> str:
        if not self._store:
            return ""
        log_path = self._store.issue_dir(self.issue.ticket) / "agent.log"
        if not log_path.exists():
            return ""
        try:
            content = log_path.read_text(encoding="utf-8").strip()
            # Limit to last 2000 chars to keep UI responsive
            if len(content) > 2000:
                content = "...\n" + content[-2000:]
            return content
        except Exception:
            return ""

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
        from agentic_kanban.ui.screens.create_dialog import PlanPromptDialog

        def on_result(result) -> None:
            if result is None:
                return
            spec = result["spec"]
            context = result.get("context", "")
            tc = result.get("tc", "")
            ticket = self.issue.ticket
            issue_dir = str(self._store.issue_dir(ticket)) if self._store else f".board/issues/{ticket}"
            prompt = f"아래 요구사항을 기반으로 {issue_dir}/plan.md에 구현 계획을 작성하세요.\n{spec}"
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

        from agentic_kanban.ui.screens.create_dialog import ImplementConfirmDialog

        def on_result(confirmed) -> None:
            if not confirmed:
                return
            ticket = self.issue.ticket
            issue_dir = str(self._store.issue_dir(ticket)) if self._store else f".board/issues/{ticket}"
            prompt = (
                f"{issue_dir}/plan.md를 기반으로 구현을 시작하세요.\n"
                f"작업 완료 후 {issue_dir}/worklog.jsonl에 기록하세요."
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
        from agentic_kanban.ui.screens.create_dialog import ReviewPromptDialog

        def on_result(result) -> None:
            if result is None:
                return
            review = result["review"]
            ticket = self.issue.ticket
            issue_dir = str(self._store.issue_dir(ticket)) if self._store else f".board/issues/{ticket}"
            prompt = (
                f"아래 수정 요청을 반영하세요.\n{review}\n"
                f"작업 완료 후 {issue_dir}/worklog.jsonl에 기록하세요."
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
        try:
            log = self._read_agent_log()
            if log and hasattr(self, "_agent_viewer"):
                self._agent_viewer.update_content(log)
        except Exception:
            pass
        self._update_pipeline_header()
        self.notify(f"#{ticket} 에이전트 작업 완료.", severity="information")

    def action_toggle_agent(self) -> None:
        try:
            # Refresh content from log file
            log = self._read_agent_log()
            if log:
                self._agent_viewer.update_content(log)
            self._agent_viewer.display = not self._agent_viewer.display
        except AttributeError:
            pass

    def _refresh_agent_viewer(self) -> None:
        """Auto-refresh agent log viewer while agent is running."""
        if not self._agent_service or not self._store:
            return
        try:
            running = self._agent_service.is_running(self.issue.ticket)
            # 헤더 상태 갱신
            try:
                header = self.query_one("#agent-section-header", Static)
                if running:
                    header.update("[bold]Agent[/] (a) [bold #8fac6e]⟳ 작업중...[/]")
                else:
                    header.update("[bold]Agent[/] (a)")
            except Exception:
                pass
            if not running:
                return
            log = self._read_agent_log()
            if log and hasattr(self, "_agent_viewer"):
                self._agent_viewer.update_content(log)
        except Exception:
            pass

    _expanded_section: str = ""  # 현재 확대된 섹션 이름 (빈 문자열이면 없음)

    # 섹션 이름 → (뷰어 속성, 헤더 ID)
    _SECTION_MAP = {
        "agent": ("_agent_viewer", "agent-section-header"),
        "plan": ("_plan_viewer", "plan-section-header"),
        "ticket": ("_description_viewer", "desc-section-header"),
        "comments": ("_comments_viewer", "comments-section-header"),
        "worklog": ("_worklog_viewer", "worklog-section-header"),
    }

    def action_toggle_plan(self) -> None:
        try:
            self._plan_viewer.display = not self._plan_viewer.display
        except AttributeError:
            pass

    def action_expand_section(self, section: str) -> None:
        """대문자키 — 해당 섹션 전체화면 확대/축소."""
        if self._expanded_section == section:
            # 축소 — 모든 섹션 복원
            self._expanded_section = ""
            for name, (viewer_attr, header_id) in self._SECTION_MAP.items():
                v = getattr(self, viewer_attr, None)
                if v:
                    v.display = True
                    v.styles.height = "auto"
                    v.styles.min_height = None
                    v.styles.max_height = 40
                try:
                    self.query_one(f"#{header_id}").display = True
                except Exception:
                    pass
            # checklist도 복원
            if hasattr(self, "_checklist_widget"):
                self._checklist_widget.display = True
            try:
                self.query_one("#cl-section-header").display = True
            except Exception:
                pass
        else:
            # 확대 — 선택한 섹션만 표시
            self._expanded_section = section
            target_attr, target_header = self._SECTION_MAP.get(section, ("", ""))
            for name, (viewer_attr, header_id) in self._SECTION_MAP.items():
                v = getattr(self, viewer_attr, None)
                is_target = (name == section)
                if v:
                    v.display = is_target
                    if is_target:
                        v.styles.height = "1fr"
                        v.styles.min_height = "100%"
                        v.styles.max_height = None
                try:
                    self.query_one(f"#{header_id}").display = is_target
                except Exception:
                    pass
            # checklist 숨기기
            if hasattr(self, "_checklist_widget"):
                self._checklist_widget.display = False
            try:
                self.query_one("#cl-section-header").display = False
            except Exception:
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

