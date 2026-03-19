"""Theme definitions and TCSS generation for wt-board."""

from __future__ import annotations

from pathlib import Path
from typing import Dict


THEMES: Dict[str, Dict[str, str]] = {
    "brown": {
        "bg": "#1a1612",
        "surface": "#2a2420",
        "surface_alt": "#3a3430",
        "border": "#4a4440",
        "accent": "#c4956a",
        "accent_light": "#d4a57a",
        "text": "#d4ccc4",
        "muted": "#7a7470",
        "header_bg": "#120e0a",
        "green": "#8fac6e",
        "red": "#c47070",
        "selection": "#3a3025",
    },
    "catppuccin": {
        "bg": "#1e1e2e",
        "surface": "#313244",
        "surface_alt": "#45475a",
        "border": "#585b70",
        "accent": "#89b4fa",
        "accent_light": "#b4d0fb",
        "text": "#cdd6f4",
        "muted": "#6c7086",
        "header_bg": "#11111b",
        "green": "#a6e3a1",
        "red": "#f38ba8",
        "selection": "#45475a",
    },
    "nord": {
        "bg": "#2e3440",
        "surface": "#3b4252",
        "surface_alt": "#434c5e",
        "border": "#4c566a",
        "accent": "#88c0d0",
        "accent_light": "#8fbcbb",
        "text": "#eceff4",
        "muted": "#4c566a",
        "header_bg": "#242933",
        "green": "#a3be8c",
        "red": "#bf616a",
        "selection": "#434c5e",
    },
    "github-dark": {
        "bg": "#0d1117",
        "surface": "#161b22",
        "surface_alt": "#21262d",
        "border": "#30363d",
        "accent": "#58a6ff",
        "accent_light": "#79c0ff",
        "text": "#c9d1d9",
        "muted": "#6e7681",
        "header_bg": "#010409",
        "green": "#39d353",
        "red": "#f85149",
        "selection": "#0d419f",
    },
}

THEME_NAMES = list(THEMES.keys())


def get_theme(name: str) -> Dict[str, str]:
    """Return theme color dict, falling back to 'brown'."""
    return THEMES.get(name, THEMES["brown"])


def _styles_dir() -> Path:
    return Path(__file__).parent / "styles"


def apply_theme(name: str, board_tcss: Path = None, detail_tcss: Path = None) -> None:
    """Rewrite TCSS files from templates using the given theme's colors.

    Parameters
    ----------
    name:
        Theme name (key in ``THEMES``).
    board_tcss:
        Path to ``board.tcss``. Defaults to the package's styles directory.
    detail_tcss:
        Path to ``detail.tcss``. Defaults to the package's styles directory.
    """
    colors = get_theme(name)
    styles = _styles_dir()

    if board_tcss is None:
        board_tcss = styles / "board.tcss"
    if detail_tcss is None:
        detail_tcss = styles / "detail.tcss"

    board_tmpl = styles / "board.tcss.tmpl"
    detail_tmpl = styles / "detail.tcss.tmpl"

    if board_tmpl.exists():
        tmpl = board_tmpl.read_text(encoding="utf-8")
        board_tcss.write_text(tmpl.format(**colors), encoding="utf-8")

    if detail_tmpl.exists():
        tmpl = detail_tmpl.read_text(encoding="utf-8")
        detail_tcss.write_text(tmpl.format(**colors), encoding="utf-8")
