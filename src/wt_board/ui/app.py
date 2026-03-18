"""Main Textual application entry point."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from textual.app import App

from wt_board.ui.screens.board_screen import BoardScreen


class WtBoardApp(App):
    CSS_PATH = "styles/board.tcss"
    TITLE = "wt-board"

    BINDINGS = [
        ("q", "request_quit", "Quit"),
        ("?", "help", "Help"),
    ]

    def __init__(self, board_path: Optional[str] = None) -> None:
        super().__init__()
        self.board_path = board_path
        self._last_quit_press = 0.0

    def on_mount(self) -> None:
        self.push_screen(BoardScreen(board_path=self.board_path))
        self._check_onboarding()
        self._setup_auto_sync()

    def _setup_auto_sync(self) -> None:
        """Set up periodic auto-sync if configured."""
        try:
            from wt_board.store.board_store import find_board_root
            board_path = find_board_root()
            if board_path is None:
                return
            from wt_board.models.config import BoardConfig
            config = BoardConfig.from_yaml(board_path / "config.yaml")
            if config.tracker.auto_sync:
                interval = max(60, config.tracker.sync_interval)
                self.set_interval(interval, self._auto_sync)
        except Exception:
            pass

    def _auto_sync(self) -> None:
        """Silently sync all issues in the background. Only notifies on error."""
        try:
            screen = self.screen
            from wt_board.ui.screens.board_screen import BoardScreen
            if not isinstance(screen, BoardScreen):
                return
            sync_service = screen._get_sync_service()
            if sync_service is None:
                return
            sync_service.sync_all()
            # Reload board data quietly
            screen._issues_by_status.clear()
            screen._tc_map.clear()
            screen._agent_map.clear()
            screen._load_data()
            screen._rebuild_board()
            cols = screen._columns()
            if cols:
                screen.col_index = min(screen.col_index, len(cols) - 1)
                screen._clamp_card()
                screen._highlight_current()
        except Exception as exc:
            self.notify(f"자동 동기화 실패: {exc}", severity="error")

    def action_request_quit(self) -> None:
        """q 한 번 → 안내, 빠르게 두 번 → 종료."""
        now = time.monotonic()
        if now - self._last_quit_press < 1.5:
            self.exit()
        else:
            self._last_quit_press = now
            self.notify("한 번 더 [bold]q[/]를 누르면 종료합니다.", severity="warning")

    def _check_onboarding(self) -> None:
        """최초 실행 시 Dooray API key가 없으면 온보딩 다이얼로그."""
        try:
            from wt_board.store.board_store import find_board_root
            board_path = find_board_root()
            if board_path is None:
                return
            from wt_board.models.config import BoardConfig
            config_file = board_path / "config.yaml"
            config = BoardConfig.from_yaml(config_file)
            if config.tracker.type == "dooray" and not config.tracker.dooray.api_key:
                self._show_onboarding(board_path, config)
        except Exception:
            pass

    def _show_onboarding(self, board_path: Path, config) -> None:
        from wt_board.ui.screens.create_dialog import OnboardingDialog

        def on_result(api_key: Optional[str]) -> None:
            if api_key:
                config.tracker.dooray.api_key = api_key
                config.to_yaml(board_path / "config.yaml")
                self.notify("Dooray API key 저장 완료.", severity="information")

        self.push_screen(OnboardingDialog(), callback=on_result)
