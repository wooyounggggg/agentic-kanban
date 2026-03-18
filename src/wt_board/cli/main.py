"""Click-based CLI for wt-board."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from wt_board.models.config import BoardConfig, DEFAULT_STATUSES
from wt_board.store.board_store import BoardStore, find_board_root

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_store_and_config() -> tuple:
    """Return (BoardStore, BoardConfig) for the current project.

    Exits with an error message if no ``.board/`` directory is found.
    """
    board_path = find_board_root()
    if board_path is None:
        console.print(
            "[red]No .board/ directory found. Run [bold]wt-board init[/bold] first.[/red]"
        )
        sys.exit(1)
    store = BoardStore(board_path)
    config = store.read_config()
    return store, config


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """wt-board: TUI Kanban Board for Git worktree-based parallel development."""
    if ctx.invoked_subcommand is None:
        try:
            from wt_board.ui.app import WtBoardApp
            app = WtBoardApp()
            app.run()
        except ImportError:
            console.print(
                "[yellow]TUI not available. Use sub-commands: init, add, list, move, show.[/yellow]"
            )


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@cli.command()
def init() -> None:
    """Initialize .board/ directory in the current project."""
    cwd = Path.cwd()
    board_dir = cwd / ".board"

    if board_dir.exists():
        console.print(f"[yellow].board/ already exists at {board_dir}[/yellow]")
        return

    board_dir.mkdir(parents=True)
    (board_dir / "issues").mkdir()
    (board_dir / "archive").mkdir()
    (board_dir / "cache").mkdir()

    config = BoardConfig()
    config.project.name = cwd.name

    tracker_type = click.prompt(
        "Tracker type",
        default="dooray",
        type=click.Choice(["dooray", "none"]),
    )
    config.tracker.type = tracker_type

    if tracker_type == "dooray":
        api_key = click.prompt(
            "Dooray API key (leave blank to skip)",
            default="",
            hide_input=True,
        )
        if api_key:
            config.tracker.dooray.api_key = api_key

    store = BoardStore(board_dir)
    store.write_config(config)

    console.print(f"[green]Initialized .board/ at {board_dir}[/green]")


# ---------------------------------------------------------------------------
# migrate
# ---------------------------------------------------------------------------


@cli.command()
def migrate() -> None:
    """Migrate worktree data from .wt-state/ format to .board/."""
    cwd = Path.cwd()
    worktrees_dir = cwd / "worktrees"

    if not worktrees_dir.exists():
        console.print("[yellow]No worktrees/ directory found — nothing to migrate.[/yellow]")
        return

    board_dir = find_board_root()
    if board_dir is None:
        console.print("[red]Run [bold]wt-board init[/bold] first.[/red]")
        sys.exit(1)

    from wt_board.store.migration import migrate_from_wt_state

    migrated = migrate_from_wt_state(cwd, board_dir)
    for ticket in migrated:
        console.print(f"  migrated [cyan]{ticket}[/cyan]")
    console.print(f"[green]Migration complete: {len(migrated)} issue(s) imported.[/green]")


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("ticket")
@click.option("--title", "-t", default="", help="Issue title")
@click.option("--base", "-b", default=None, help="Base branch")
def add(ticket: str, title: str, base: Optional[str]) -> None:
    """Create issue + worktree for TICKET."""
    store, config = _load_store_and_config()

    from wt_board.services.issue_service import IssueService

    svc = IssueService(store, config)
    issue = svc.create_issue(ticket, title=title, base_branch=base)

    console.print(
        f"[green]Created[/green] [cyan]{issue.ticket}[/cyan] "
        f"(status: {issue.status}, worktree: {issue.worktree.path})"
    )


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@cli.command(name="list")
def list_() -> None:
    """List all issues grouped by status."""
    store, config = _load_store_and_config()

    from wt_board.services.issue_service import IssueService

    svc = IssueService(store, config)
    by_status = svc.list_issues_by_status()

    table = Table(title="Issues", show_lines=True)
    table.add_column("Ticket", style="cyan", no_wrap=True)
    table.add_column("Title")
    table.add_column("Status", style="magenta")
    table.add_column("Priority", justify="right")

    for status_name, issues in by_status.items():
        for issue in issues:
            status_def = config.get_status_def(status_name)
            label = (status_def.label if status_def else status_name)
            table.add_row(
                issue.ticket,
                issue.title or "—",
                label,
                str(issue.priority),
            )

    if not any(issues for issues in by_status.values()):
        console.print("[yellow]No issues found.[/yellow]")
        return

    console.print(table)


# ---------------------------------------------------------------------------
# move
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("ticket")
@click.argument("status")
def move(ticket: str, status: str) -> None:
    """Move TICKET to STATUS."""
    store, config = _load_store_and_config()

    from wt_board.services.issue_service import IssueService

    svc = IssueService(store, config)
    try:
        issue = svc.move_issue(ticket, status)
        console.print(
            f"[green]Moved[/green] [cyan]{ticket}[/cyan] to [magenta]{issue.status}[/magenta]"
        )
    except (ValueError, FileNotFoundError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("ticket")
def show(ticket: str) -> None:
    """Show details for TICKET."""
    store, config = _load_store_and_config()

    try:
        issue = store.read_issue(ticket)
    except FileNotFoundError:
        console.print(f"[red]Issue not found: {ticket}[/red]")
        sys.exit(1)

    status_def = config.get_status_def(issue.status)
    status_label = (
        f"{status_def.icon} {status_def.label}" if status_def else issue.status
    )

    console.rule(f"[cyan]{issue.ticket}[/cyan]")
    console.print(f"[bold]Title:[/bold]    {issue.title or '(no title)'}")
    console.print(f"[bold]Status:[/bold]   {status_label}")
    console.print(f"[bold]Priority:[/bold] {issue.priority}")
    console.print(f"[bold]Branch:[/bold]   {issue.worktree.branch}")
    console.print(f"[bold]Worktree:[/bold] {issue.worktree.path}")
    console.print(f"[bold]Created:[/bold]  {issue.created_at}")
    console.print(f"[bold]Updated:[/bold]  {issue.updated_at}")

    if issue.tracker.url:
        console.print(f"[bold]Tracker:[/bold]  {issue.tracker.url}")

    plan = store.read_plan(ticket)
    if plan:
        console.rule("Plan")
        console.print(plan)

    from wt_board.services.checklist_service import ChecklistService

    cl_svc = ChecklistService(store)
    progress = cl_svc.get_progress(ticket)
    if progress != "0/0":
        console.print(f"[bold]Checklist:[/bold] {progress}")


if __name__ == "__main__":
    cli()
