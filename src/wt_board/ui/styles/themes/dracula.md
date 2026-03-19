# Dracula Theme

Vibrant, high-contrast dark theme with purple and pink accents. Maximum energy and visibility.

## Color Palette

| Element | Hex | Usage |
|---------|-----|-------|
| **Background** | `#282a36` | App background, base layer |
| **Surface** | `#44475a` | Cards, panels, container backgrounds |
| **Surface-Alt** | `#6272a4` | Hover states, alt backgrounds |
| **Accent-Purple** | `#bd93f9` | Focused elements, headers, links |
| **Accent-Green** | `#50fa7b` | Current/active state, success indicators |
| **Accent-Pink** | `#ff79c6` | Errors, alerts, highlights |
| **Text** | `#f8f8f2` | Primary text |
| **Text-Muted** | `#6272a4` | Secondary text, hints |

## Theme CSS

### board.tcss (Board Layout)

```tcss
/* board.tcss — Dracula theme */

/* --------------------------------------------------------------------------
   App-wide defaults
   -------------------------------------------------------------------------- */
Screen {
    background: #282a36;
    color: #f8f8f2;
}

/* --------------------------------------------------------------------------
   Header
   -------------------------------------------------------------------------- */
Header {
    background: #191a21;
    color: #bd93f9;
    text-style: bold;
    height: 1;
}

/* --------------------------------------------------------------------------
   Footer
   -------------------------------------------------------------------------- */
Footer {
    background: #191a21;
    color: #6272a4;
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
    border: round #6272a4;
    overflow-y: auto;
}

KanbanColumn .col-header {
    background: #44475a;
    color: #bd93f9;
    text-style: bold;
    padding: 0 1;
    text-align: center;
    height: 1;
}

KanbanColumn .col-empty {
    color: #6272a4;
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
    border: tall #6272a4;
    background: #44475a;
}

IssueCard:focus {
    border: tall #bd93f9;
    background: #6272a4;
}

IssueCard.selected {
    border: tall #bd93f9;
    background: #6272a4;
}
```

### detail.tcss (Detail Panel)

```tcss
/* detail.tcss — Dracula theme */

#detail-panel {
    height: 1fr;
    width: 100%;
    padding: 1;
    overflow-y: auto;
}

#detail-header {
    color: #f8f8f2;
    height: auto;
    margin-bottom: 1;
    border-bottom: solid #6272a4;
    padding-bottom: 1;
}

/* Section headers */
#cl-section-header,
#plan-section-header,
#worklog-section-header,
#desc-section-header,
#comments-section-header {
    color: #bd93f9;
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
    background: #6272a4;
}

ChecklistWidget .cl-item.cl-done {
    color: #6272a4;
}

/* Plan / Description / Comments viewer */
PlanViewer {
    height: auto;
    max-height: 24;
    overflow-y: auto;
    padding: 0 1;
    border: round #6272a4;
}

/* Worklog */
WorklogWidget {
    height: auto;
    max-height: 20;
    overflow-y: auto;
    padding: 0 1;
}

WorklogWidget .wl-entry {
    border-bottom: dashed #44475a;
    padding-bottom: 1;
    margin-bottom: 1;
    height: auto;
}

WorklogWidget .wl-empty {
    color: #6272a4;
    padding: 1;
}
```

### sidebar.py (Sidebar Widget CSS)

```python
DEFAULT_CSS = """
Sidebar {
    width: 20;
    height: 100%;
    background: #44475a;
    border-right: solid #6272a4;
    padding: 1;
}
Sidebar.focused-mode {
    border-right: solid #bd93f9;
}
Sidebar .sb-title {
    color: #bd93f9;
    text-style: bold;
    padding: 0 0 1 0;
}
Sidebar .sb-section {
    color: #6272a4;
    text-style: italic;
    height: 1;
    margin-top: 1;
}
Sidebar .sb-section-active {
    color: #bd93f9;
    text-style: bold;
    height: 1;
    margin-top: 1;
}
Sidebar .sb-item {
    color: #6272a4;
    padding-left: 1;
    height: 1;
}
Sidebar .sb-item-current {
    color: #f8f8f2;
    text-style: bold;
    padding-left: 1;
    height: 1;
}
Sidebar .sb-item-hover {
    color: #bd93f9;
    text-style: bold;
    padding-left: 1;
    height: 1;
    background: #6272a4;
}
Sidebar .sb-hint {
    color: #6272a4;
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
    border: tall #6272a4;
    background: #44475a;
}
IssueCard:focus {
    border: tall #bd93f9;
    background: #6272a4;
}
IssueCard.selected {
    border: tall #bd93f9;
    background: #6272a4;
}
"""
```

### Inline Color Overrides (issue_card.py build_markup)

Replace hardcoded colors in `_build_markup()`:
- `[on #30363d cyan]` → `[on #6272a4 cyan]` (chip backgrounds)
- `[on #30363d]` → `[on #6272a4]` (status/label backgrounds)
- `[on #30363d dim magenta]` → `[on #6272a4 dim magenta]` (tag backgrounds)

---

## Theme Switching Implementation

Already covered in **Catppuccin theme** section above. Add "dracula" to THEMES dict:

```python
THEMES = {
    "github-dark": "styles/board.tcss",
    "catppuccin": "styles/themes/catppuccin.tcss",
    "nord": "styles/themes/nord.tcss",
    "dracula": "styles/themes/dracula.tcss",
}
```

---

## Visual Characteristics

- **Energy**: Vibrant colors jump off the screen
- **Contrast**: Maximum contrast with pink/purple accents (~10:1 WCAG AAA+)
- **Personality**: Fun, modern, distinctly recognizable
- **Visibility**: Excellent for presentations or high-visibility work
- **Accessibility**: High contrast but may be overwhelming for extended sessions; consider Nord for that
