"""BoardScreen — main Kanban board screen."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Static, SelectionList

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
        Binding("n", "new_issue", "New Issue"),
        Binding("enter", "open_detail", "Detail"),
        Binding("a", "start_agent", "Agent"),
        Binding("m", "move_card", "Move"),
        Binding("s", "sync", "Sync"),
        Binding("/", "search", "Search"),
        Binding("P", "add_project", "Add Project"),
        Binding("S", "switch_project", "Switch Project"),
        Binding("left,h", "col_left", "Left", show=False),
        Binding("right,l", "col_right", "Right", show=False),
        Binding("up,k", "card_up", "Up", show=False),
        Binding("down,j", "card_down", "Down", show=False),
    ]

    CSS_PATH = "../styles/board.tcss"

    # Current column index (reactive so we can track it)
    col_index: reactive[int] = reactive(0)
    card_index: reactive[int] = reactive(0)

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
                except Exception:
                    pass

            for issue in all_issues:
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

        for col_idx, status_def in enumerate(self._statuses):
            issues = self._issues_by_status.get(status_def.name, [])
            col = KanbanColumn(
                status_def=status_def,
                issues=issues,
                tc_map=self._tc_map,
                agent_map=self._agent_map,
                selected_index=0 if (col_idx == self.col_index and issues) else -1,
            )
            board.mount(col)

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
        self.col_index = self._next_nonempty_col(self.col_index, -1)
        self.card_index = 0
        self._highlight_current()

    def action_col_right(self) -> None:
        cols = self._columns()
        if not cols:
            return
        self.col_index = self._next_nonempty_col(self.col_index, +1)
        self.card_index = 0
        self._highlight_current()

    def action_card_up(self) -> None:
        self.card_index = max(0, self.card_index - 1)
        self._clamp_card()

    def action_card_down(self) -> None:
        col = self._current_column()
        if col is None:
            return
        self.card_index = min(col.card_count() - 1, self.card_index + 1)
        self._clamp_card()

    def _highlight_current(self) -> None:
        cols = self._columns()
        for idx, col in enumerate(cols):
            if idx == self.col_index:
                col.set_focused_card(self.card_index if col.card_count() > 0 else -1)
            else:
                col.set_focused_card(-1)

    def action_open_detail(self) -> None:
        issue = self._current_issue()
        if issue is None:
            self.notify("No issue selected.", severity="warning")
            return
        from wt_board.ui.screens.detail_screen import DetailScreen
        sync_svc = self._get_sync_service()
        self.app.push_screen(DetailScreen(issue=issue, store=self._store, sync_service=sync_svc))

    def _get_sync_service(self):
        """Build a SyncService if tracker is configured."""
        try:
            if not self._store or not self._config.tracker.dooray.api_key:
                return None
            from wt_board.trackers.dooray import DoorayTracker
            from wt_board.services.sync_service import SyncService
            tracker = DoorayTracker(self._config.tracker.dooray)
            return SyncService(self._store, tracker, self._config)
        except Exception:
            return None

    def action_new_issue(self) -> None:
        from wt_board.ui.screens.create_dialog import CreateDialog
        # Pass tracker for Dooray lookup
        tracker = None
        try:
            if self._store and self._config.tracker.type == "dooray":
                from wt_board.trackers.dooray import DoorayTracker
                tracker = DoorayTracker(self._config.tracker.dooray)
        except Exception:
            pass

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
                if desc:
                    issue.description = desc
                    issue.assignee = assignee
                    self._store.write_issue(ticket, issue)
                    self._store.write_description(ticket, desc)
                self._issues_by_status.clear()
                self._tc_map.clear()
                self._agent_map.clear()
                self._load_data()
                self._rebuild_board()
                self.col_index = self._next_nonempty_col(-1, +1)
                self.card_index = 0
                self._highlight_current()
                self.notify(f"이슈 [cyan]#{ticket}[/] 생성 완료.", severity="information")

        self.app.push_screen(CreateDialog(tracker=tracker), callback=on_result)

    def action_start_agent(self) -> None:
        issue = self._current_issue()
        if issue is None:
            self.notify("No issue selected.", severity="warning")
            return
        self.notify(f"Agent action for #{issue.ticket} — not yet implemented.", severity="information")

    def action_move_card(self) -> None:
        issue = self._current_issue()
        if issue is None:
            self.notify("No issue selected.", severity="warning")
            return
        options = [(f"{s.icon} {s.label}", s.name) for s in self._statuses if s.name != issue.status]
        if not options:
            self.notify("No valid transitions.", severity="warning")
            return
        # Show inline notification listing options (full modal SelectionList is in a future iteration)
        targets = ", ".join(f"{icon} {name}" for icon, name in options)
        self.notify(f"Move #{issue.ticket} to: {targets}\n(Full move dialog coming soon)", severity="information")

    def action_sync(self) -> None:
        self.notify("Sync with Dooray — not yet implemented.", severity="information")

    def action_search(self) -> None:
        self.notify("Search — not yet implemented.", severity="information")

    # ------------------------------------------------------------------
    # Mouse click
    # ------------------------------------------------------------------

    def on_issue_card_clicked(self, event: IssueCard.Clicked) -> None:
        """Handle mouse click on a card. Click to select, click again to open detail."""
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

    def action_add_project(self) -> None:
        """Add a new project to the registry."""
        from wt_board.ui.screens.create_dialog import AddProjectDialog
        def on_result(result) -> None:
            if result is None:
                return
            name = result["name"]
            path = result["path"]
            wt_base = result.get("worktree_base", "worktrees")
            dooray_pid = result.get("dooray_project_id", "")
            self._registry.add(name, path)
            # Init .board/ for the new project if not exists
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
            self._refresh_sidebar()
            self.notify(f"프로젝트 [cyan]{name}[/] 추가 완료.", severity="information")
        self.app.push_screen(AddProjectDialog(), callback=on_result)

    def action_switch_project(self) -> None:
        """Switch to another project."""
        names = self._registry.names()
        if len(names) <= 1:
            self.notify("Only one project registered.", severity="warning")
            return
        from wt_board.ui.screens.create_dialog import SwitchProjectDialog
        def on_result(result: Optional[str]) -> None:
            if result is None:
                return
            entry = self._registry.switch(result)
            if entry:
                self.board_path = str(Path(entry.path) / ".board")
                self._issues_by_status.clear()
                self._tc_map.clear()
                self._agent_map.clear()
                self._load_data()
                self._rebuild_board()
                self._refresh_sidebar()
                self.col_index = self._next_nonempty_col(-1, +1)
                self.card_index = 0
                self._highlight_current()
                self.notify(f"Switched to [cyan]{result}[/].", severity="information")
        self.app.push_screen(
            SwitchProjectDialog(names=names, current=self._registry.current),
            callback=on_result,
        )

    def _refresh_sidebar(self) -> None:
        try:
            sidebar = self.query_one("#sidebar", Sidebar)
            proj_list = [{"name": p.name, "path": p.path} for p in self._registry.projects]
            sidebar.refresh_projects(proj_list, self._registry.current)
        except Exception:
            pass
