# Catppuccin Mocha Theme

A warm, cozy dark theme with pastels. Perfect for extended work sessions.

## Color Palette

| Element | Hex | Usage |
|---------|-----|-------|
| **Background** | `#1e1e2e` | App background, base layer |
| **Surface** | `#313244` | Cards, panels, container backgrounds |
| **Surface-Alt** | `#45475a` | Hover states, alt backgrounds |
| **Accent-Blue** | `#89b4fa` | Focused elements, headers, links |
| **Accent-Green** | `#a6e3a1` | Current/active state, success indicators |
| **Accent-Red** | `#f38ba8` | Errors, alerts |
| **Text** | `#cdd6f4` | Primary text |
| **Text-Muted** | `#6c7086` | Secondary text, hints |

## Theme CSS

### board.tcss (Board Layout)

```tcss
/* board.tcss — Catppuccin Mocha theme */

/* --------------------------------------------------------------------------
   App-wide defaults
   -------------------------------------------------------------------------- */
Screen {
    background: #1e1e2e;
    color: #cdd6f4;
}

/* --------------------------------------------------------------------------
   Header
   -------------------------------------------------------------------------- */
Header {
    background: #11111b;
    color: #89b4fa;
    text-style: bold;
    height: 1;
}

/* --------------------------------------------------------------------------
   Footer
   -------------------------------------------------------------------------- */
Footer {
    background: #11111b;
    color: #6c7086;
    height: 1;
}

/* --------------------------------------------------------------------------
   Board layout
   -------------------------------------------------------------------------- */
#board-layout {
    height: 1fr;
    width: 100%;
}

/* --------------------------------------------------------------------------
   Columns area
   -------------------------------------------------------------------------- */
#board-columns {
    height: 1fr;
    width: 1fr;
    overflow-x: auto;
}

/* KanbanColumn */
KanbanColumn {
    width: 1fr;
    min-width: 22;
    height: 100%;
    margin: 0 1;
    border: round #45475a;
    overflow-y: auto;
}

KanbanColumn .col-header {
    background: #313244;
    color: #89b4fa;
    text-style: bold;
    padding: 0 1;
    text-align: center;
    height: 1;
}

KanbanColumn .col-empty {
    color: #6c7086;
    padding: 1;
    text-align: center;
    height: 3;
}

/* --------------------------------------------------------------------------
   Issue cards
   -------------------------------------------------------------------------- */
IssueCard {
    height: auto;
    padding: 0 1;
    margin: 1 1 0 1;
    border: tall #45475a;
    background: #313244;
}

IssueCard:focus {
    border: tall #89b4fa;
    background: #45475a;
}

IssueCard.selected {
    border: tall #89b4fa;
    background: #45475a;
}
```

### detail.tcss (Detail Panel)

```tcss
/* detail.tcss — Catppuccin Mocha theme */

#detail-panel {
    height: 1fr;
    width: 100%;
    padding: 1;
    overflow-y: auto;
}

#detail-header {
    color: #cdd6f4;
    height: auto;
    margin-bottom: 1;
    border-bottom: solid #45475a;
    padding-bottom: 1;
}

/* Section headers */
#cl-section-header,
#plan-section-header,
#worklog-section-header,
#desc-section-header,
#comments-section-header {
    color: #89b4fa;
    text-style: bold;
    height: 1;
    margin-top: 1;
}

/* Checklist */
ChecklistWidget {
    height: auto;
    max-height: 20;
    overflow-y: auto;
}

ChecklistWidget .cl-item {
    padding: 0 1;
    height: 1;
}

ChecklistWidget .cl-item.cl-selected {
    background: #45475a;
}

ChecklistWidget .cl-item.cl-done {
    color: #6c7086;
}

/* Plan / Description / Comments viewer */
PlanViewer {
    height: auto;
    max-height: 24;
    overflow-y: auto;
    padding: 0 1;
    border: round #45475a;
}

/* Worklog */
WorklogWidget {
    height: auto;
    max-height: 20;
    overflow-y: auto;
    padding: 0 1;
}

WorklogWidget .wl-entry {
    border-bottom: dashed #313244;
    padding-bottom: 1;
    margin-bottom: 1;
    height: auto;
}

WorklogWidget .wl-empty {
    color: #6c7086;
    padding: 1;
}
```

### sidebar.py (Sidebar Widget CSS)

```python
DEFAULT_CSS = """
Sidebar {
    width: 20;
    height: 100%;
    background: #313244;
    border-right: solid #45475a;
    padding: 1;
}
Sidebar.focused-mode {
    border-right: solid #89b4fa;
}
Sidebar .sb-title {
    color: #89b4fa;
    text-style: bold;
    padding: 0 0 1 0;
}
Sidebar .sb-section {
    color: #6c7086;
    text-style: italic;
    height: 1;
    margin-top: 1;
}
Sidebar .sb-section-active {
    color: #89b4fa;
    text-style: bold;
    height: 1;
    margin-top: 1;
}
Sidebar .sb-item {
    color: #6c7086;
    padding-left: 1;
    height: 1;
}
Sidebar .sb-item-current {
    color: #cdd6f4;
    text-style: bold;
    padding-left: 1;
    height: 1;
}
Sidebar .sb-item-hover {
    color: #89b4fa;
    text-style: bold;
    padding-left: 1;
    height: 1;
    background: #45475a;
}
Sidebar .sb-hint {
    color: #6c7086;
    margin-top: 1;
    height: auto;
}
"""
```

### issue_card.py (Issue Card Widget CSS)

```python
DEFAULT_CSS = """
IssueCard {
    height: auto;
    padding: 0 1;
    margin: 0 0 1 0;
    border: tall #45475a;
    background: #313244;
}
IssueCard:focus {
    border: tall #89b4fa;
    background: #45475a;
}
IssueCard.selected {
    border: tall #89b4fa;
    background: #45475a;
}
"""
```

### Inline Color Overrides (issue_card.py build_markup)

Replace hardcoded colors in `_build_markup()`:
- `[on #30363d cyan]` → `[on #45475a cyan]` (chip backgrounds)
- `[on #30363d]` → `[on #45475a]` (status/label backgrounds)
- `[on #30363d dim magenta]` → `[on #45475a dim magenta]` (tag backgrounds)

---

## Theme Switching Implementation

Add to `config.yaml`:

```yaml
ui:
  theme: catppuccin  # Options: github-dark, catppuccin, nord, dracula
```

Add to `src/agentic_kanban/ui/theme.py` (new file):

```python
"""Theme loader for agentic-kanban."""

import os
from pathlib import Path
from typing import Dict, Optional

THEMES = {
    "github-dark": "styles/board.tcss",
    "catppuccin": "styles/themes/catppuccin.tcss",
    "nord": "styles/themes/nord.tcss",
    "dracula": "styles/themes/dracula.tcss",
}

def load_theme(theme_name: str) -> str:
    """Load TCSS for a given theme."""
    if theme_name not in THEMES:
        theme_name = "github-dark"

    theme_path = Path(__file__).parent / THEMES[theme_name]
    if theme_path.exists():
        return theme_path.read_text()
    return ""

def get_theme_colors(theme_name: str) -> Dict[str, str]:
    """Return color palette for a theme."""
    palettes = {
        "github-dark": {
            "bg": "#0d1117",
            "surface": "#161b22",
            "accent": "#58a6ff",
            "text": "#c9d1d9",
            "muted": "#6e7681",
        },
        "catppuccin": {
            "bg": "#1e1e2e",
            "surface": "#313244",
            "accent": "#89b4fa",
            "text": "#cdd6f4",
            "muted": "#6c7086",
        },
        "nord": {
            "bg": "#2e3440",
            "surface": "#3b4252",
            "accent": "#88c0d0",
            "text": "#eceff4",
            "muted": "#4c566a",
        },
        "dracula": {
            "bg": "#282a36",
            "surface": "#44475a",
            "accent": "#bd93f9",
            "text": "#f8f8f2",
            "muted": "#6272a4",
        },
    }
    return palettes.get(theme_name, palettes["github-dark"])
```

Then in your main app class:

```python
class WtBoard(App):
    def on_mount(self) -> None:
        # Load theme from config
        config = load_config()  # your config loader
        theme = config.get("ui", {}).get("theme", "github-dark")
        theme_css = load_theme(theme)
        self.stylesheet.load(theme_css)
```

---

## Visual Characteristics

- **Warmth**: Soft pastels with reduced blue-light stress
- **Contrast**: Excellent readability with ~8:1 WCAG AA contrast
- **Personality**: Friendly and inviting, suitable for long sessions
- **Accessibility**: Colorblind-friendly accent colors (blue + green)
