"""DetailScreen — 50/50 split: agent terminal + issue details."""

from __future__ import annotations

from typing import List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Static, Collapsible

from wt_board.models.config import BoardConfig, DEFAULT_STATUSES, StatusDef
from wt_board.models.issue import Issue
from wt_board.models.checklist import Checklist
from wt_board.models.worklog import WorklogEntry
from wt_board.models.agent import AgentSession, AgentStatus


_STATUS_COLOR = {
    "planning": "yellow",
    "work": "cyan",
    "review": "magenta",
    "pr": "blue",
    "done": "green",
}


class DetailScreen(Screen):
    """50/50 split: left = agent terminal, right = issue details."""

    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("tab", "focus_next", "Switch Panel"),
        Binding("space", "toggle_tc_item", "Toggle TC"),
        Binding("p", "toggle_plan", "Plan"),
        Binding("l", "toggle_worklog", "Worklog"),
        Binding("d", "toggle_description", "Desc"),
        Binding("c", "toggle_comments", "Comments"),
        Binding("f", "fetch_body", "Fetch"),
        Binding("a", "start_agent", "Agent"),
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
        self._config: BoardConfig = config if config is not None else BoardConfig()
        self._checklist = Checklist()
        self._worklog: list[WorklogEntry] = []
        self._plan: str = ""
        self._agent: AgentSession = AgentSession()
        self._description: str = ""
        self._comments: str = ""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self._load_issue_data()
        self._populate_right_panel()
        # 자동 에이전트 시작/resume
        self._auto_start_agent()

    def _load_issue_data(self) -> None:
        if self._store is None:
            self._load_mock_data()
            return
        try:
            self._checklist = self._store.read_checklist(self.issue.ticket)
            self._worklog = self._store.read_worklog(self.issue.ticket)
            self._plan = self._store.read_plan(self.issue.ticket)
            self._agent = self._store.read_agent(self.issue.ticket)
            self._description = self._store.read_description(self.issue.ticket)
            self._comments = self._store.read_comments(self.issue.ticket)
        except Exception:
            self._load_mock_data()

    def _load_mock_data(self) -> None:
        from wt_board.models.checklist import Checklist, ChecklistItem
        from wt_board.models.worklog import WorklogEntry

        cl = Checklist()
        cl.add("Write unit tests", type_="verify")
        cl.add("Update documentation", type_="todo")
        cl.add("Manual smoke test", type_="manual")
        cl.items[0].status = "done"
        self._checklist = cl

        self._worklog = [
            WorklogEntry(
                at="2026-03-18T10:00:00+09:00",
                author="human",
                work_done="Initial implementation of feature",
                next_action="Run integration tests",
            ),
            WorklogEntry(
                at="2026-03-18T11:30:00+09:00",
                author="agent",
                work_done="Added unit test coverage",
                next_action="Review PR",
            ),
        ]
        self._plan = f"# Plan for #{self.issue.ticket}\n\n## Goal\n{self.issue.title}\n\n## Steps\n1. Implement\n2. Test\n3. Review\n"

    def _populate_right_panel(self) -> None:
        """Mount checklist, plan, worklog into the right panel."""
        from wt_board.ui.widgets.checklist_widget import ChecklistWidget
        from wt_board.ui.widgets.plan_viewer import PlanViewer
        from wt_board.ui.widgets.worklog_widget import WorklogWidget

        try:
            panel = self.query_one("#right-panel")
        except Exception:
            return

        # TC Checklist section
        cl_header = Static(
            f"[bold]TC Checklist[/] [dim]{self._checklist.progress_str}[/]",
            id="cl-section-header",
        )
        panel.mount(cl_header)

        self._checklist_widget = ChecklistWidget(
            checklist=self._checklist,
            on_toggle=self._on_tc_toggle,
            id="checklist-widget",
        )
        panel.mount(self._checklist_widget)

        # Plan section (hidden by default until 'p' pressed)
        plan_header = Static("[bold]Plan [/][dim](press p)[/]", id="plan-section-header")
        panel.mount(plan_header)

        self._plan_viewer = PlanViewer(self._plan, id="plan-viewer")
        self._plan_viewer.display = False
        panel.mount(self._plan_viewer)

        # Worklog section (hidden by default until 'l' pressed)
        wl_header = Static("[bold]Worklog [/][dim](press l)[/]", id="worklog-section-header")
        panel.mount(wl_header)

        self._worklog_widget = WorklogWidget(self._worklog, id="worklog-widget")
        self._worklog_widget.display = False
        panel.mount(self._worklog_widget)

        # Description section (hidden by default until 'd' pressed)
        desc_header = Static("[bold]Description [/][dim](press d)[/]", id="desc-section-header")
        panel.mount(desc_header)

        self._description_viewer = PlanViewer(
            self._description or "_No description fetched yet. Press [bold]f[/] to fetch._",
            id="description-viewer",
        )
        self._description_viewer.display = False
        panel.mount(self._description_viewer)

        # Comments section (hidden by default until 'c' pressed)
        comments_header = Static("[bold]Comments [/][dim](press c)[/]", id="comments-section-header")
        panel.mount(comments_header)

        self._comments_viewer = PlanViewer(
            self._comments or "_No comments fetched yet. Press [bold]f[/] to fetch._",
            id="comments-viewer",
        )
        self._comments_viewer.display = False
        panel.mount(self._comments_viewer)

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

        with Horizontal(id="detail-layout"):
            # Left panel: agent terminal
            with Vertical(id="left-panel"):
                yield Static("[bold]Agent Terminal[/]", id="agent-panel-header")
                yield self._agent_area()
                yield Static(
                    "[bold cyan]f[/] Dooray 조회  [bold cyan]a[/] 에이전트  [bold cyan]m[/] 상태변경",
                    id="left-panel-shortcuts",
                )

            # Right panel: details
            with VerticalScroll(id="right-panel"):
                yield Static(title_markup, id="detail-header")

        yield Footer()

    def _agent_area(self) -> Static:
        if self._agent.is_active:
            return Static(
                f"[green]Agent active[/] (pid {self._agent.pid})\n"
                "[dim]Attach to tmux pane to see output.[/]",
                id="agent-status",
            )
        return Static(
            "[dim]No active agent.\nPress [bold]a[/] to start agent.[/]",
            id="agent-status",
        )

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
            # Persist if store available
            if self._store:
                self._store.write_checklist(self.issue.ticket, self._checklist)
            # Update header
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
        """Fetch issue body and comments from the tracker."""
        if self._sync_service is None:
            self.notify("No sync service configured.", severity="warning")
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

            self.notify(f"Fetched body and comments for #{ticket}.", severity="information")
        except Exception as exc:
            self.notify(f"Fetch failed: {exc}", severity="error")

    def _auto_start_agent(self) -> None:
        """상세 화면 진입 시 에이전트 자동 시작/resume."""
        if self._store is None:
            return
        try:
            from wt_board.services.agent_service import AgentService
            agent_svc = AgentService(self._store, self._config)
            self._agent = agent_svc.resume_agent(self.issue.ticket)
            self._update_agent_status_widget()
        except Exception:
            pass  # tmux 미설치 등 — 조용히 실패

    def _update_agent_status_widget(self) -> None:
        """에이전트 상태 위젯 갱신."""
        try:
            widget = self.query_one("#agent-status", Static)
            if self._agent.is_active:
                session = self._agent.tmux_pane or "unknown"
                widget.update(
                    f"[green]에이전트 실행 중[/] (PID {self._agent.pid})\n"
                    f"[dim]tmux: {session}[/]\n"
                    f"[dim]a키로 포커스 전환[/]"
                )
            else:
                widget.update(
                    "[dim]에이전트 미실행[/]\n"
                    "[dim]a키로 시작[/]"
                )
        except Exception:
            pass

    def action_start_agent(self) -> None:
        if self._store is None:
            self.notify("저장소가 연결되어 있지 않습니다.", severity="error")
            return
        try:
            from wt_board.services.agent_service import AgentService
            agent_svc = AgentService(self._store, self._config)
            if self._agent.status == AgentStatus.ACTIVE and agent_svc.check_alive(self.issue.ticket):
                agent_svc.focus_agent(self.issue.ticket)
                self.notify("에이전트 포커스 전환.", severity="information")
            else:
                self._agent = agent_svc.start_agent(self.issue.ticket)
                self._update_agent_status_widget()
                self.notify("에이전트를 시작합니다.", severity="information")
        except Exception as exc:
            self.notify(f"에이전트 오류: {exc}", severity="error")

    def action_move_status(self) -> None:
        statuses: List[StatusDef] = self._config.statuses or list(DEFAULT_STATUSES)

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
                self.notify("저장소가 연결되어 있지 않습니다.", severity="error")
                return
            try:
                from wt_board.services.issue_service import IssueService
                svc = IssueService(self._store, self._config)
                self.issue = svc.move_issue(self.issue.ticket, new_status)
                # Update the header in the detail view
                try:
                    status_color = _STATUS_COLOR.get(new_status, "white")
                    self.query_one("#detail-header", Static).update(
                        f"[bold cyan]#{self.issue.ticket}[/]  "
                        f"{self.issue.title}  "
                        f"[{status_color}][{new_status}][/{status_color}]"
                    )
                except Exception:
                    pass
                self.notify(
                    f"[cyan]#{self.issue.ticket}[/] → [bold]{new_status}[/] 이동 완료.",
                    severity="information",
                )
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
        """Called by ChecklistWidget after a toggle."""
        pass  # Persistence handled in action_toggle_tc_item
