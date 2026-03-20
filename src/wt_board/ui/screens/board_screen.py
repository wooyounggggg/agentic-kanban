"""BoardScreen — main Kanban board screen."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Static

from wt_board.models.config import DEFAULT_STATUSES, BoardConfig, StatusDef
from wt_board.models.issue import Issue
from wt_board.models.projects import ProjectRegistry
from wt_board.ui.widgets.issue_card import IssueCard
from wt_board.ui.widgets.kanban_column import KanbanColumn
from wt_board.ui.widgets.sidebar import Sidebar


# ---------------------------------------------------------------------------
# Mock data (used when no .board/ directory is found)
# ---------------------------------------------------------------------------

def _mock_issues() -> List[Issue]:
    from wt_board.models.issue import Issue, WorktreeInfo, TrackerInfo
    return [
        Issue(ticket="3373", title="Add user auth flow", status="work", priority=1),
        Issue(ticket="3482", title="Fix DB connection pool leak", status="work", priority=2),
        Issue(ticket="3545", title="Refactor payment module", status="planning", priority=3),
        Issue(ticket="3553", title="Add metrics endpoint", status="review", priority=4),
        Issue(ticket="3557", title="Update README docs", status="pr", priority=5),
        Issue(ticket="3677", title="Migrate to PostgreSQL 16", status="planning", priority=6),
        Issue(ticket="3678", title="Done feature example", status="done", priority=7),
    ]


class BoardScreen(Screen):
    """Main kanban board: sidebar + columns + footer."""

    BINDINGS = [
        Binding("n", "new_issue", "New"),
        Binding("enter", "open_detail", "Open"),
        Binding("m", "move_card", "Move"),
        Binding("s", "sync", "Sync"),
        Binding("T", "theme", "Theme"),
        Binding("v", "toggle_completed", "완료토글"),
        Binding("x", "delete_item", "Delete"),
        Binding("/", "search", "Search"),
        Binding("left,h", "col_left", "Left", show=False),
        Binding("right,l", "col_right", "Right", show=False),
        Binding("up,k", "card_up", "Up", show=False),
        Binding("down,j", "card_down", "Down", show=False),
    ]

    def _build_agent_service(self):
        """AgentService 인스턴스 생성."""
        if self._store is None:
            return None
        try:
            from wt_board.services.agent_service import AgentService
            return AgentService(self._store, self._config)
        except Exception:
            return None

    def _build_pipeline_service(self, agent_service=None):
        """PipelineService 인스턴스 생성."""
        if self._store is None:
            return None
        try:
            from wt_board.services.pipeline_service import PipelineService
            from wt_board.services.agent_service import AgentService
            if agent_service is None:
                agent_service = AgentService(self._store, self._config)
            return PipelineService(self._store, self._config, agent_service)
        except Exception:
            return None

    CSS_PATH = "../styles/board.tcss"

    # Current column index (reactive so we can track it)
    col_index: reactive[int] = reactive(0)
    card_index: reactive[int] = reactive(0)
    _sidebar_focused: bool = False
    _sidebar_index: int = 0
    _show_completed: bool = False

    def __init__(self, board_path: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.board_path = board_path
        self._store = None
        self._config: BoardConfig = BoardConfig()
        self._registry = ProjectRegistry.load()
        # Auto-register current project if .board/ exists
        self._auto_register_project()
        # {status_name: [Issue]}
        self._issues_by_status: Dict[str, List[Issue]] = {}
        # {ticket: tc_progress_str}
        self._tc_map: Dict[str, str] = {}
        # {ticket: agent_status_str}
        self._agent_map: Dict[str, str] = {}
        self._statuses: List[StatusDef] = list(DEFAULT_STATUSES)
        self._sync_service_cache = None

    def _auto_register_project(self) -> None:
        """Auto-register the current directory as a project if .board/ exists."""
        cwd = Path.cwd()
        board_dir = cwd / ".board"
        if board_dir.exists():
            name = cwd.name
            if name not in self._registry.names():
                self._registry.add(name, str(cwd))
            if not self._registry.current:
                self._registry.current = name
                self._registry.save()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self._load_data()
        self._rebuild_board()
        # Focus first non-empty column
        self.col_index = self._next_nonempty_col(-1, +1)
        self.card_index = 0
        self._highlight_current()

    def _load_data(self) -> None:
        """Try to load from BoardStore; fall back to mock data."""
        try:
            from wt_board.store.board_store import BoardStore, find_board_root
            bp = Path(self.board_path) if self.board_path else None
            store = BoardStore(bp)
            self._store = store
            self._config = store.read_config()
            self._statuses = self._config.statuses

            tickets = store.list_issues()
            all_issues: List[Issue] = []
            for ticket in tickets:
                try:
                    issue = store.read_issue(ticket)
                    all_issues.append(issue)
                    cl = store.read_checklist(ticket)
                    if cl.total_count:
                        self._tc_map[ticket] = cl.progress_str
                    agent = store.read_agent(ticket)
                    self._agent_map[ticket] = agent.status
                except (FileNotFoundError, yaml.YAMLError):
                    pass

            for issue in all_issues:
                if issue.pipeline_step == "completed" and not self._show_completed:
                    continue
                self._issues_by_status.setdefault(issue.status, []).append(issue)

        except Exception:
            # No .board/ or load failed — use mock data
            for issue in _mock_issues():
                self._issues_by_status.setdefault(issue.status, []).append(issue)

    def _rebuild_board(self) -> None:
        """Mount KanbanColumn widgets into the board container."""
        try:
            board = self.query_one("#board-columns")
        except Exception:
            return

        board.remove_children()

        visible_col = 0
        for status_def in self._statuses:
            if status_def.terminal and not self._show_completed:
                continue
            issues = self._issues_by_status.get(status_def.name, [])
            col = KanbanColumn(
                status_def=status_def,
                issues=issues,
                tc_map=self._tc_map,
                agent_map=self._agent_map,
                selected_index=0 if (visible_col == self.col_index and issues) else -1,
            )
            board.mount(col)
            visible_col += 1

    def _refresh_board(self) -> None:
        """Reload data and rebuild the board UI."""
        self._issues_by_status.clear()
        self._tc_map.clear()
        self._agent_map.clear()
        self._load_data()
        self._rebuild_board()
        self.col_index = self._next_nonempty_col(-1, +1)
        self.card_index = 0
        self._highlight_current()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="board-layout"):
            # Sidebar with project list
            proj_list = [{"name": p.name, "path": p.path} for p in self._registry.projects]
            yield Sidebar(
                projects=proj_list,
                current=self._registry.current,
                id="sidebar",
            )

            # Main board area
            with Horizontal(id="board-columns"):
                pass  # Populated in _rebuild_board()

        yield Footer()

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def _columns(self) -> List[KanbanColumn]:
        return list(self.query(KanbanColumn))

    def _current_column(self) -> Optional[KanbanColumn]:
        cols = self._columns()
        if not cols or self.col_index >= len(cols):
            return None
        return cols[self.col_index]

    def _current_issue(self) -> Optional[Issue]:
        col = self._current_column()
        if col is None:
            return None
        return col.focused_issue()

    def _clamp_card(self) -> None:
        col = self._current_column()
        if col is None:
            return
        count = col.card_count()
        if count == 0:
            self.card_index = 0
        elif self.card_index >= count:
            self.card_index = count - 1
        col.set_focused_card(self.card_index)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _next_nonempty_col(self, start: int, direction: int) -> int:
        """Find next column with cards in the given direction (+1 or -1)."""
        cols = self._columns()
        idx = start + direction
        while 0 <= idx < len(cols):
            if cols[idx].card_count() > 0:
                return idx
            idx += direction
        return start  # stay put if nothing found

    def action_col_left(self) -> None:
        cols = self._columns()
        if not cols:
            return
        new_idx = self._next_nonempty_col(self.col_index, -1)
        if new_idx == self.col_index:
            # 이미 맨 왼쪽 → 사이드바로 포커스 이동
            self._focus_sidebar()
            return
        self.col_index = new_idx
        self.card_index = 0
        self._highlight_current()

    def action_col_right(self) -> None:
        if self._sidebar_focused:
            # 사이드바 → 보드로 복귀
            self._exit_sidebar()
            return
        cols = self._columns()
        if not cols:
            return
        self.col_index = self._next_nonempty_col(self.col_index, +1)
        self.card_index = 0
        self._highlight_current()

    def action_card_up(self) -> None:
        if self._sidebar_focused:
            self._sidebar_index = max(0, self._sidebar_index - 1)
            self._switch_to_sidebar_project()
            return
        self.card_index = max(0, self.card_index - 1)
        self._clamp_card()

    def action_card_down(self) -> None:
        if self._sidebar_focused:
            max_idx = len(self._registry.projects) - 1
            self._sidebar_index = min(max_idx, self._sidebar_index + 1)
            self._switch_to_sidebar_project()
            return
        col = self._current_column()
        if col is None:
            return
        self.card_index = min(col.card_count() - 1, self.card_index + 1)
        self._clamp_card()

    # ------------------------------------------------------------------
    # Sidebar focus
    # ------------------------------------------------------------------

    def _focus_sidebar(self) -> None:
        """사이드바로 포커스 이동."""
        self._sidebar_focused = True
        names = self._registry.names()
        if self._registry.current in names:
            self._sidebar_index = names.index(self._registry.current)
        else:
            self._sidebar_index = 0
        for col in self._columns():
            col.set_focused_card(-1)
        try:
            sidebar = self.query_one("#sidebar", Sidebar)
            sidebar.set_focused_mode(True, self._sidebar_index)
        except Exception:
            pass

    def _exit_sidebar(self) -> None:
        """사이드바에서 보드로 복귀."""
        self._sidebar_focused = False
        try:
            sidebar = self.query_one("#sidebar", Sidebar)
            sidebar.set_focused_mode(False)
        except Exception:
            pass
        self.col_index = self._next_nonempty_col(-1, +1)
        self.card_index = 0
        self._highlight_current()

    def _switch_to_sidebar_project(self) -> None:
        """↑↓로 사이드바 프로젝트를 이동하면 즉시 전환."""
        names = self._registry.names()
        if not names or self._sidebar_index >= len(names):
            return
        selected = names[self._sidebar_index]
        # 사이드바 하이라이트 갱신
        try:
            sidebar = self.query_one("#sidebar", Sidebar)
            sidebar.set_hover(self._sidebar_index)
        except Exception:
            pass
        # 프로젝트 전환
        entry = self._registry.switch(selected)
        if entry:
            self.board_path = str(Path(entry.path) / ".board")
            self._issues_by_status.clear()
            self._tc_map.clear()
            self._agent_map.clear()
            self._load_data()
            self._rebuild_board()

    def _highlight_current(self) -> None:
        cols = self._columns()
        for idx, col in enumerate(cols):
            if idx == self.col_index:
                col.set_focused_card(self.card_index if col.card_count() > 0 else -1)
            else:
                col.set_focused_card(-1)

    def action_open_detail(self) -> None:
        """Enter → 상세 화면."""
        if self._sidebar_focused:
            self._exit_sidebar()
            return
        issue = self._current_issue()
        if issue is None:
            self.notify("이슈를 선택해주세요.", severity="warning")
            return
        from wt_board.ui.screens.detail_screen import DetailScreen
        sync_svc = self._get_sync_service()
        agent_svc = self._build_agent_service()
        pipeline_svc = self._build_pipeline_service(agent_service=agent_svc)
        self.app.push_screen(
            DetailScreen(
                issue=issue,
                store=self._store,
                sync_service=sync_svc,
                config=self._config,
                pipeline_service=pipeline_svc,
                agent_service=agent_svc,
            )
        )

    def _build_tracker(self):
        """Construct a DoorayTracker from current config, or None."""
        try:
            if not self._store or self._config.tracker.type != "dooray":
                return None
            from wt_board.trackers.dooray import DoorayTracker
            dc = self._config.tracker.dooray
            return DoorayTracker(dc.cli_path, dc.api_key)
        except Exception:
            return None

    def _get_sync_service(self):
        """Build a SyncService if tracker is configured (cached per screen instance)."""
        if self._sync_service_cache is not None:
            return self._sync_service_cache
        try:
            if not self._store or self._config.tracker.type == "none":
                return None
            from wt_board.services.sync_service import SyncService
            tracker = self._build_tracker()
            if tracker is None:
                return None
            svc = SyncService(self._store, tracker, self._config)
            self._sync_service_cache = svc
            return svc
        except Exception:
            return None

    def action_delete_item(self) -> None:
        """x키 — 사이드바: 프로젝트 삭제, 보드: (미구현)"""
        if self._sidebar_focused:
            names = self._registry.names()
            if not names or self._sidebar_index >= len(names):
                return
            target = names[self._sidebar_index]
            if self._registry.remove(target):
                self._sidebar_index = max(0, self._sidebar_index - 1)
                self._switch_to_sidebar_project()
                try:
                    sidebar = self.query_one("#sidebar", Sidebar)
                    proj_list = [{"name": p.name, "path": p.path} for p in self._registry.projects]
                    sidebar.projects = proj_list
                    sidebar.current_project = self._registry.current
                    sidebar.set_hover(self._sidebar_index)
                except Exception:
                    pass
                self.notify(f"프로젝트 [cyan]{target}[/] 삭제.", severity="information")
            return
        self.notify("이슈 삭제는 아직 미구현입니다.", severity="warning")

    def action_new_issue(self) -> None:
        if self._sidebar_focused:
            # 사이드바에서 n → 프로젝트 추가
            from wt_board.ui.screens.create_dialog import AddProjectDialog
            def on_result(result) -> None:
                if result is None:
                    return
                name = result["name"]
                path = result["path"]
                wt_base = result.get("worktree_base", "worktrees")
                dooray_pid = result.get("dooray_project_id", "")
                self._registry.add(name, path)
                board_dir = Path(path) / ".board"
                if not board_dir.exists():
                    from wt_board.models.config import BoardConfig
                    board_dir.mkdir(parents=True)
                    (board_dir / "issues").mkdir(exist_ok=True)
                    (board_dir / "archive").mkdir(exist_ok=True)
                    (board_dir / "cache").mkdir(exist_ok=True)
                    config = BoardConfig()
                    config.project.name = name
                    config.project.worktree_base = wt_base
                    if dooray_pid:
                        config.tracker.dooray.project_id = dooray_pid
                    config.to_yaml(board_dir / "config.yaml")
                try:
                    sidebar = self.query_one("#sidebar", Sidebar)
                    proj_list = [{"name": p.name, "path": p.path} for p in self._registry.projects]
                    sidebar.refresh_projects(proj_list, self._registry.current)
                    sidebar.set_focused_mode(True, len(proj_list) - 1)
                    self._sidebar_index = len(proj_list) - 1
                except Exception:
                    pass
                self.notify(f"프로젝트 [cyan]{name}[/] 추가 완료.", severity="information")
            self.app.push_screen(AddProjectDialog(), callback=on_result)
            return

        from wt_board.ui.screens.create_dialog import CreateDialog
        # Pass tracker for Dooray lookup
        tracker = self._build_tracker()

        def on_result(result) -> None:
            if result is None:
                return
            ticket = result["ticket"]
            title = result.get("title", "")
            desc = result.get("description", "")
            assignee = result.get("assignee", "")
            if self._store:
                from wt_board.services.issue_service import IssueService
                svc = IssueService(self._store, self._config)
                issue = svc.create_issue(ticket, title=title)
                issue.pipeline_step = "plan"
                if desc:
                    issue.description = desc
                    issue.assignee = assignee
                self._store.write_issue(ticket, issue)
                if desc:
                    self._store.write_description(ticket, desc)
                # 새 이슈 → background agent 자동 시작
                try:
                    from wt_board.services.agent_service import AgentService
                    from wt_board.models.agent import AgentStatus
                    agent_svc = AgentService(self._store, self._config)
                    agent_svc.start_agent(ticket)
                    self._agent_map[ticket] = AgentStatus.ACTIVE
                except Exception:
                    pass
                self._refresh_board()
                self.notify(f"이슈 [cyan]#{ticket}[/] 생성 완료.", severity="information")

        self.app.push_screen(CreateDialog(tracker=tracker), callback=on_result)

    def action_start_agent(self) -> None:
        issue = self._current_issue()
        if issue is None:
            self.notify("이슈를 선택해주세요.", severity="warning")
            return
        if self._store is None:
            self.notify("저장소가 연결되어 있지 않습니다.", severity="error")
            return
        try:
            from wt_board.services.agent_service import AgentService
            from wt_board.models.agent import AgentStatus
            agent_svc = AgentService(self._store, self._config)
            agent = agent_svc.resume_agent(issue.ticket)
            if agent.status == AgentStatus.ACTIVE:
                agent_svc.focus_agent(issue.ticket)
                self._agent_map[issue.ticket] = AgentStatus.ACTIVE
                self._rebuild_board()
                self._highlight_current()
                self.notify("에이전트 포커스 전환.", severity="information")
        except Exception as exc:
            self.notify(f"에이전트 오류: {exc}", severity="error")

    def action_move_card(self) -> None:
        """m키 — MoveDialog로 이슈 상태 변경."""
        issue = self._current_issue()
        if issue is None:
            self.notify("이슈를 선택해주세요.", severity="warning")
            return
        # Build target list from config statuses (all except current)
        targets = [s for s in self._statuses if s.name != issue.status]
        if not targets:
            self.notify("이동 가능한 상태가 없습니다.", severity="warning")
            return

        saved_ticket = issue.ticket  # Save for re-focus after move

        from wt_board.ui.screens.create_dialog import MoveDialog

        def on_result(new_status) -> None:
            if new_status is None:
                return
            try:
                from wt_board.services.issue_service import IssueService
                svc = IssueService(self._store, self._config)
                svc.move_issue(saved_ticket, new_status)
                # Also sync pipeline_step to match status
                issue_obj = self._store.read_issue(saved_ticket)
                issue_obj.pipeline_step = new_status
                self._store.write_issue(saved_ticket, issue_obj)

                self._refresh_board()
                # Re-focus the moved card
                self._focus_ticket(saved_ticket)
                self.notify(f"#{saved_ticket} → {new_status}", severity="information")
            except Exception as exc:
                self.notify(f"이동 실패: {exc}", severity="error")

        self.app.push_screen(
            MoveDialog(ticket=issue.ticket, current_status=issue.status, target_statuses=targets),
            callback=on_result,
        )

    def _focus_ticket(self, ticket: str) -> None:
        """Move focus to a specific ticket after board refresh."""
        cols = self._columns()
        for col_idx, col in enumerate(cols):
            for card_idx, issue in enumerate(col.issues):
                if issue.ticket == ticket:
                    self.col_index = col_idx
                    self.card_index = card_idx
                    self._highlight_current()
                    return

    def action_toggle_completed(self) -> None:
        """H키 — 완료(completed) 이슈 표시/숨기기 토글."""
        self._show_completed = not self._show_completed
        self._refresh_board()
        if self._show_completed:
            self.notify("완료 이슈 표시.", severity="information")
        else:
            self.notify("완료 이슈 숨김.", severity="information")

    def action_sync(self) -> None:
        sync_service = self._get_sync_service()
        if sync_service is None:
            self.notify("Dooray 연동이 설정되지 않았습니다.", severity="warning")
            return
        try:
            updated = sync_service.sync_all()
            self._refresh_board()
            self.notify(f"Dooray 동기화 완료 ({len(updated)}개 이슈)", severity="information")
        except Exception as exc:
            self.notify(f"동기화 실패: {exc}", severity="error")

    def action_search(self) -> None:
        self.notify("Search — not yet implemented.", severity="information")

    def action_theme(self) -> None:
        """T — 테마 선택 다이얼로그 열기."""
        current_theme = self._config.ui.theme if hasattr(self._config, "ui") else "brown"

        def on_result(name: str) -> None:
            if name is None:
                return
            try:
                from wt_board.ui.themes import apply_theme
                apply_theme(name)
            except Exception as exc:
                self.notify(f"테마 적용 실패: {exc}", severity="error")
                return

            # Save to config
            try:
                if self._store is not None:
                    from wt_board.store.board_store import find_board_root
                    board_path = find_board_root()
                    if board_path is not None:
                        self._config.ui.theme = name
                        self._config.to_yaml(board_path / "config.yaml")
            except Exception:
                pass

            self.app.refresh_css()
            self.notify(f"테마 '{name}' 선택됨. 재시작하면 완전히 적용됩니다.", severity="information")

        from wt_board.ui.screens.create_dialog import ThemeDialog
        self.app.push_screen(ThemeDialog(current_theme=current_theme), callback=on_result)

    # ------------------------------------------------------------------
    # Mouse click
    # ------------------------------------------------------------------

    def on_issue_card_clicked(self, event: IssueCard.Clicked) -> None:
        """Click: select. Double-click (same card): open agent."""
        card = event.card
        cols = self._columns()
        for col_idx, col in enumerate(cols):
            cards = list(col.query(IssueCard))
            for card_idx, c in enumerate(cards):
                if c is card:
                    already_selected = (self.col_index == col_idx and self.card_index == card_idx)
                    self.col_index = col_idx
                    self.card_index = card_idx
                    self._highlight_current()
                    if already_selected:
                        self.action_open_detail()
                    return

