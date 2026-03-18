"""Main Textual application entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from textual.app import App

from wt_board.ui.screens.board_screen import BoardScreen


class WtBoardApp(App):
    CSS_PATH = "styles/board.tcss"
    TITLE = "wt-board"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("?", "help", "Help"),
    ]

    def __init__(self, board_path: Optional[str] = None) -> None:
        super().__init__()
        self.board_path = board_path

    def on_mount(self) -> None:
        self.push_screen(BoardScreen(board_path=self.board_path))
        self._check_onboarding()

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
