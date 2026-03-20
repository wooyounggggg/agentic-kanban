"""Theme definitions and TCSS generation for agentic-kanban."""

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
    "dracula": {
        "bg": "#282a36",
        "surface": "#44475a",
        "surface_alt": "#6272a4",
        "border": "#6272a4",
        "accent": "#bd93f9",
        "accent_light": "#ff79c6",
        "text": "#f8f8f2",
        "muted": "#6272a4",
        "header_bg": "#1e1f29",
        "green": "#50fa7b",
        "red": "#ff5555",
        "selection": "#44475a",
    },
    "solarized-dark": {
        "bg": "#002b36",
        "surface": "#073642",
        "surface_alt": "#094d5a",
        "border": "#586e75",
        "accent": "#268bd2",
        "accent_light": "#2aa198",
        "text": "#839496",
        "muted": "#586e75",
        "header_bg": "#001e26",
        "green": "#859900",
        "red": "#dc322f",
        "selection": "#073642",
    },
    "gruvbox": {
        "bg": "#1d2021",
        "surface": "#282828",
        "surface_alt": "#3c3836",
        "border": "#504945",
        "accent": "#d79921",
        "accent_light": "#fabd2f",
        "text": "#ebdbb2",
        "muted": "#665c54",
        "header_bg": "#141617",
        "green": "#98971a",
        "red": "#cc241d",
        "selection": "#3c3836",
    },
    "tokyo-night": {
        "bg": "#1a1b26",
        "surface": "#24283b",
        "surface_alt": "#414868",
        "border": "#414868",
        "accent": "#7aa2f7",
        "accent_light": "#bb9af7",
        "text": "#c0caf5",
        "muted": "#565f89",
        "header_bg": "#13141c",
        "green": "#9ece6a",
        "red": "#f7768e",
        "selection": "#283457",
    },
}

THEME_NAMES = list(THEMES.keys())


def get_theme(name: str) -> Dict[str, str]:
    """Return theme color dict, falling back to 'brown'."""
    return THEMES.get(name, THEMES["brown"])


def _styles_dir() -> Path:
    return Path(__file__).parent / "styles"


def apply_theme(name: str, board_tcss=None, detail_tcss=None) -> None:
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

    board_tcss = Path(board_tcss) if board_tcss else styles / "board.tcss"
    detail_tcss = Path(detail_tcss) if detail_tcss else styles / "detail.tcss"

    board_tmpl = styles / "board.tcss.tmpl"
    detail_tmpl = styles / "detail.tcss.tmpl"

    if board_tmpl.exists():
        tmpl = board_tmpl.read_text(encoding="utf-8")
        board_tcss.write_text(tmpl.format(**colors), encoding="utf-8")

    if detail_tmpl.exists():
        tmpl = detail_tmpl.read_text(encoding="utf-8")
        detail_tcss.write_text(tmpl.format(**colors), encoding="utf-8")
