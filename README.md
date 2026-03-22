<p align="center">
  <h1 align="center">agentic-kanban</h1>
  <p align="center">
    <strong>AI-Driven Kanban Board for Terminal-Based Parallel Development</strong>
  </p>
  <p align="center">
    Assign AI agents to issues and watch them flow through a 4-stage pipeline—all from your terminal.
  </p>
</p>

<p align="center">
  <a href="https://github.com/wooyounggggg/agentic-kanban/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python"></a>
  <a href="https://github.com/wooyounggggg/agentic-kanban/issues"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
</p>

---

## The Problem

Most AI coding tools work on one issue at a time. You queue up code changes, wait for them to finish, then move to the next task. When you're managing multiple issues across different features or bug fixes, this serial workflow becomes a bottleneck.

**agentic-kanban** changes that. It lets you assign AI agents to multiple issues in parallel, manage them on a visual kanban board, and track progress in real-time—all without leaving your terminal.

## What It Does

- **Visual Kanban Board** — Organize issues across 4 pipeline stages (Plan, Implement, Review, Completed) with vim keybindings
- **AI Agent Pipeline** — Each issue flows through Plan → Implement → Review stages, with agents handling each step automatically
- **Real-Time Streaming** — Watch agent work happen live in the Agent tab, updated every second
- **Dooray Integration** — Fetch issues from NHN Dooray, sync comments and status, auto-poll for updates
- **Multi-Project Support** — Switch between projects instantly via sidebar (powered by Git worktrees for isolation)
- **8 Beautiful Themes** — brown, catppuccin, nord, github-dark, dracula, solarized-dark, gruvbox, tokyo-night
- **Claude Code Skills** — Use `/agentic-kanban:plan`, `/agentic-kanban:implement`, etc. for headless agent workflows
- **Human-Readable Storage** — All data in `.kanban/` using YAML, Markdown, and JSONL—easy to version control and inspect

## Getting Started

### Requirements

- Python 3.9 or later
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- (Optional) NHN Dooray account + API key for issue tracker integration

### Installation

```bash
git clone https://github.com/wooyounggggg/agentic-kanban.git
cd agentic-kanban
pip install -e .
```

To also install Claude Code plugin skills (optional):

```bash
./install.sh
```

### First Run

```bash
cd <your-project-directory>
agentic-kanban init
agentic-kanban
```

The `init` command creates a `.kanban/` directory and prompts for your Dooray API key (if you plan to use it). Then `agentic-kanban` launches the TUI.

## How It Works

### The Pipeline

Every issue moves through 4 stages:

| Stage | What Happens | Output |
|-------|--------------|--------|
| **📝 Plan** | Spec + context → implementation plan | `plan.md` |
| **🔨 Implement** | Plan + prompt → actual code changes | Code commits |
| **🔍 Review** | Fix/improvement prompt → code refinements | Code commits |
| **✅ Completed** | Issue done | — |

Press `r` on any issue to run the agent for its current stage. The agent spawns a background `claude` process, streams output to `agent.log`, and saves a work summary to `worklog.jsonl` when done.

### The Board

```
┌─────────────────────────────────────────────────────┐
│                  agentic-kanban                     │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Plan 📝  │  │ Impl 🔨  │  │ Review 🔍        │  │
│  │ #101     │  │ #103 ⟳  │  │ #105             │  │
│  │ #102     │  │ #104     │  │ #106             │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │ Completed ✅                                 │  │
│  │ #100 #102                                     │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  r = run agent | n = new issue | f = fetch | etc.  │
└─────────────────────────────────────────────────────┘
```

Use arrow keys to navigate, vim keys to move issues between columns, and `?` for help.

## Dooray Integration

If you provide a Dooray API key during `init`, agentic-kanban will:

- **Fetch Issues** — Press `n` and enter a ticket number to auto-import issue title from Dooray
- **Load Details** — Press `f` to fetch the full issue description and comments from Dooray
- **Sync Status** — Every 60 seconds, auto-update issue titles, status, and assignee from Dooray
- **Show State** — Dooray workflow state appears as a chip on each card (in Korean if that's your Dooray language)

The integration uses `tools/dooray-cli.js` (included) to call Dooray's REST API.

## Claude Code Skills (Plugin)

For workflows that don't need the TUI, use the skills in Claude Code:

```
/agentic-kanban:setup 3724        # Create issue + worktree from ticket #3724
/agentic-kanban:plan 3724         # Interactive plan generation
/agentic-kanban:implement 3724    # Code implementation from plan
/agentic-kanban:review 3724       # Code review + fixes
```

Skills read and write the same `.kanban/` data, so you can mix TUI and skill workflows. Create a plan in the TUI, implement it via skill, review in TUI, then mark complete.

## Configuration

### Project Config (`.kanban/config.yaml`)

Created by `agentic-kanban init`. Customize pipeline stages, statuses, and agent behavior:

```yaml
project:
  name: my-project
  worktree_base: worktrees      # Directory for Git worktrees
  branch_prefix: feature-        # Branch naming: feature-{ticket}
  base_branch: develop           # Branch to create worktrees from

tracker:
  type: dooray
  dooray:
    cli_path: tools/dooray-cli.js
    api_key: <your-key>
  sync_interval: 60              # Auto-sync every 60 seconds

agent:
  binary: claude
  max_concurrent: 3              # Max parallel agents
```

### Global Config (`~/.config/agentic-kanban/settings.yaml`)

Appearance settings shared across all projects:

```yaml
theme: dracula                   # One of: brown, catppuccin, nord, etc.
```

## Data Structure

All board data lives in `.kanban/` (commitable, human-readable):

```
.kanban/
├── config.yaml                 # Project configuration
├── issues/
│   └── {ticket}/
│       ├── issue.yaml          # Issue metadata (status, priority, dates)
│       ├── plan.md             # Implementation plan
│       ├── checklist.yaml      # Task checklist
│       ├── worklog.jsonl       # Agent work summaries (one per line)
│       ├── agent.log           # Live stream of latest agent run
│       ├── description.md      # Dooray issue description (cached)
│       └── comments.md         # Dooray comments (cached)
├── archive/                    # Completed issues (moved here when done)
└── cache/                      # Temporary data
```

Each `.kanban/issues/{ticket}/` is self-contained. You can version control it, share it with teammates, or inspect the YAML directly.

## Common Tasks

### Create an Issue

In the TUI, press `n` and enter:
- Ticket number (e.g., `3724`)
- Title (auto-fetched from Dooray if available)
- Base branch (defaults to config value)

Or from CLI:

```bash
agentic-kanban add 3724 --title "Add new feature" --base main
```

### Run an Agent

1. Select an issue on the board
2. Press `r`
3. Enter a prompt (or accept the default)
4. Watch the Agent tab for live output
5. Once done, the issue auto-advances to the next stage (if plan exists for Implement, etc.)

### Fetch Dooray Details

- Press `f` on an issue to fetch description + comments
- View in Ticket and Comments tabs
- Synced automatically every 60 seconds

### Move Issues Between Stages

- `h` / `l` (vim) or arrow keys to select column
- `j` / `k` (vim) or arrow keys to select issue
- `<` / `>` to move left/right between columns

### View Issue Details

- Press `Enter` to open detail view
- See plan, checklist, worklog, and agent output
- Edit plan in-editor if needed

### Switch Projects

- Press `Ctrl+H` or `Ctrl+L` (or arrow keys in sidebar) to switch projects
- Each project has its own `.kanban/` directory with isolated worktrees

## Keyboard Shortcuts

All keybindings are shown in the TUI with `?`. Key ones:

| Key | Action |
|-----|--------|
| `r` | Run agent for current stage |
| `n` | New issue |
| `f` | Fetch issue from Dooray |
| `Enter` | Show issue details |
| `h`/`l` | Move between columns |
| `j`/`k` | Move between issues |
| `<`/`>` | Move issue left/right |
| `q` | Quit |
| `?` | Help |

## Migration from `.wt-state/`

If you've been using the old `.wt-state/` format (from `wt-` skills), agentic-kanban can import it:

```bash
agentic-kanban init
agentic-kanban migrate
```

This reads `worktrees/*/. wt-state/` and creates equivalent issues in `.kanban/issues/`.

## License

[MIT](LICENSE)
