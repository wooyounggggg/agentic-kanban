"""Main Textual application entry point."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from textual.app import App

from agentic_kanban.ui.screens.board_screen import BoardScreen


class WtBoardApp(App):
    CSS_PATH = "styles/board.tcss"
    TITLE = "agentic-kanban"

    BINDINGS = [
        ("q", "request_quit", "Quit"),
        ("?", "help", "Help"),
    ]

    def __init__(self, board_path: Optional[str] = None) -> None:
        self._apply_startup_theme()
        super().__init__()
        self.board_path = board_path
        self._last_quit_press = 0.0

    @staticmethod
    def _global_settings_path():
        from pathlib import Path
        return Path.home() / ".config" / "agentic-kanban" / "settings.yaml"

    def _apply_startup_theme(self) -> None:
        """Apply the saved theme from global settings."""
        try:
            from agentic_kanban.ui.themes import apply_theme
            import yaml
            path = self._global_settings_path()
            if path.exists():
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                theme = data.get("theme", "brown")
                apply_theme(theme)
        except Exception:
            pass

    def _load_config(self):
        """Return (config, board_path) or (None, None) if not found."""
        try:
            from agentic_kanban.store.board_store import find_board_root
            from agentic_kanban.models.config import BoardConfig
            board_path = find_board_root()
            if board_path is None:
                return None, None
            config = BoardConfig.from_yaml(board_path / "config.yaml")
            return config, board_path
        except Exception:
            return None, None

    def on_mount(self) -> None:
        config, board_path = self._load_config()
        self.push_screen(BoardScreen(board_path=self.board_path))
        self._check_onboarding(config, board_path)
        self._setup_auto_sync(config)

    def _setup_auto_sync(self, config=None) -> None:
        """Set up periodic auto-sync if configured."""
        try:
            if config is None:
                return
            if config.tracker.auto_sync:
                interval = config.tracker.sync_interval or 60
                self.set_interval(interval, self._auto_sync)
        except Exception:
            pass

    def _auto_sync(self) -> None:
        """워커 스레드에서 동기화 후 메인 스레드에서 보드 갱신."""
        try:
            screen = self.screen
            from agentic_kanban.ui.screens.board_screen import BoardScreen
            if not isinstance(screen, BoardScreen):
                return
            sync_service = screen._get_sync_service()
            if sync_service is None:
                return

            import threading

            def _sync_worker():
                try:
                    sync_service.sync_all_light()
                    self.call_from_thread(screen._refresh_board)
                except Exception:
                    pass

            threading.Thread(target=_sync_worker, daemon=True).start()
        except Exception:
            pass

    def action_help(self) -> None:
        from agentic_kanban.ui.screens.create_dialog import HelpDialog
        self.push_screen(HelpDialog())

    def action_request_quit(self) -> None:
        """q 한 번 → 안내, 빠르게 두 번 → 종료."""
        now = time.monotonic()
        if now - self._last_quit_press < 1.5:
            self.exit()
        else:
            self._last_quit_press = now
            self.notify("q를 한 번 더 누르면 종료합니다.", severity="warning", timeout=2)

    def _check_onboarding(self, config=None, board_path=None) -> None:
        """최초 실행 시 Dooray API key가 없으면 온보딩 다이얼로그."""
        try:
            if config is None or board_path is None:
                return
            if config.tracker.type == "dooray" and not config.tracker.dooray.api_key:
                self._show_onboarding(board_path, config)
        except Exception:
            pass

    def _show_onboarding(self, board_path: Path, config) -> None:
        from agentic_kanban.ui.screens.create_dialog import OnboardingDialog

        def on_result(api_key: Optional[str]) -> None:
            if api_key:
                config.tracker.dooray.api_key = api_key
                config.to_yaml(board_path / "config.yaml")
                self.notify("Dooray API key 저장 완료.", severity="information")

        self.push_screen(OnboardingDialog(), callback=on_result)
