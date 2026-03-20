# Nord Theme

Arctic, north-bluish dark theme with modern minimalism. Great for focus and clarity.

## Color Palette

| Element | Hex | Usage |
|---------|-----|-------|
| **Background** | `#2e3440` | App background, base layer |
| **Surface** | `#3b4252` | Cards, panels, container backgrounds |
| **Surface-Alt** | `#434c5e` | Hover states, alt backgrounds |
| **Accent-Cyan** | `#88c0d0` | Focused elements, headers, links |
| **Accent-Green** | `#a3be8c` | Current/active state, success indicators |
| **Accent-Red** | `#bf616a` | Errors, alerts |
| **Text** | `#eceff4` | Primary text |
| **Text-Muted** | `#4c566a` | Secondary text, hints |

## Theme CSS

### board.tcss (Board Layout)

```tcss
/* board.tcss — Nord theme */

/* --------------------------------------------------------------------------
   App-wide defaults
   -------------------------------------------------------------------------- */
Screen {
    background: #2e3440;
    color: #eceff4;
}

/* --------------------------------------------------------------------------
   Header
   -------------------------------------------------------------------------- */
Header {
    background: #2e3440;
    color: #88c0d0;
    text-style: bold;
    height: 1;
}

/* --------------------------------------------------------------------------
   Footer
   -------------------------------------------------------------------------- */
Footer {
    background: #2e3440;
    color: #4c566a;
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
    border: round #434c5e;
    overflow-y: auto;
}

KanbanColumn .col-header {
    background: #3b4252;
    color: #88c0d0;
    text-style: bold;
    padding: 0 1;
    text-align: center;
    height: 1;
}

KanbanColumn .col-empty {
    color: #4c566a;
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
    border: tall #434c5e;
    background: #3b4252;
}

IssueCard:focus {
    border: tall #88c0d0;
    background: #434c5e;
}

IssueCard.selected {
    border: tall #88c0d0;
    background: #434c5e;
}
```

### detail.tcss (Detail Panel)

```tcss
/* detail.tcss — Nord theme */

#detail-panel {
    height: 1fr;
    width: 100%;
    padding: 1;
    overflow-y: auto;
}

#detail-header {
    color: #eceff4;
    height: auto;
    margin-bottom: 1;
    border-bottom: solid #434c5e;
    padding-bottom: 1;
}

/* Section headers */
#cl-section-header,
#plan-section-header,
#worklog-section-header,
#desc-section-header,
#comments-section-header {
    color: #88c0d0;
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
    background: #434c5e;
}

ChecklistWidget .cl-item.cl-done {
    color: #4c566a;
}

/* Plan / Description / Comments viewer */
PlanViewer {
    height: auto;
    max-height: 24;
    overflow-y: auto;
    padding: 0 1;
    border: round #434c5e;
}

/* Worklog */
WorklogWidget {
    height: auto;
    max-height: 20;
    overflow-y: auto;
    padding: 0 1;
}

WorklogWidget .wl-entry {
    border-bottom: dashed #3b4252;
    padding-bottom: 1;
    margin-bottom: 1;
    height: auto;
}

WorklogWidget .wl-empty {
    color: #4c566a;
    padding: 1;
}
```

### sidebar.py (Sidebar Widget CSS)

```python
DEFAULT_CSS = """
Sidebar {
    width: 20;
    height: 100%;
    background: #3b4252;
    border-right: solid #434c5e;
    padding: 1;
}
Sidebar.focused-mode {
    border-right: solid #88c0d0;
}
Sidebar .sb-title {
    color: #88c0d0;
    text-style: bold;
    padding: 0 0 1 0;
}
Sidebar .sb-section {
    color: #4c566a;
    text-style: italic;
    height: 1;
    margin-top: 1;
}
Sidebar .sb-section-active {
    color: #88c0d0;
    text-style: bold;
    height: 1;
    margin-top: 1;
}
Sidebar .sb-item {
    color: #4c566a;
    padding-left: 1;
    height: 1;
}
Sidebar .sb-item-current {
    color: #eceff4;
    text-style: bold;
    padding-left: 1;
    height: 1;
}
Sidebar .sb-item-hover {
    color: #88c0d0;
    text-style: bold;
    padding-left: 1;
    height: 1;
    background: #434c5e;
}
Sidebar .sb-hint {
    color: #4c566a;
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
    border: tall #434c5e;
    background: #3b4252;
}
IssueCard:focus {
    border: tall #88c0d0;
    background: #434c5e;
}
IssueCard.selected {
    border: tall #88c0d0;
    background: #434c5e;
}
"""
```

### Inline Color Overrides (issue_card.py build_markup)

Replace hardcoded colors in `_build_markup()`:
- `[on #30363d cyan]` → `[on #434c5e cyan]` (chip backgrounds)
- `[on #30363d]` → `[on #434c5e]` (status/label backgrounds)
- `[on #30363d dim magenta]` → `[on #434c5e dim magenta]` (tag backgrounds)

---

## Theme Switching Implementation

Already covered in **Catppuccin theme** section above. Add "nord" to THEMES dict:

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

- **Clarity**: Clean, minimal design with Arctic palette
- **Contrast**: Exceptionally high readability (~9:1 WCAG AAA)
- **Focus**: Reduced visual noise, ideal for concentration
- **Professional**: Modern, corporate-friendly aesthetic
- **Accessibility**: WCAG AAA compliant, colorblind-friendly (cyan + green)
