"""Typer interface for selecting, planning and executing VPL updates."""

from pathlib import Path

import typer
from typer.core import TyperCommand

from .cli_selection import normalize_selection
from .credentials import Credentials
from .update import Update, UpdateOptions
from .workflow import PublishWorkflow


SELECTION_PANEL = "Selection (choose exactly one)"
ACTION_PANEL = "Changes (combine as needed)"
SOURCE_PANEL = "Local content"
EXECUTION_PANEL = "Execution"


class UpdateCommand(TyperCommand):
    """Enforce option groups while Typer parses the command."""

    mutually_exclusive_groups = (("all_", "ids", "labels", "sections"),)

    def parse_args(self, ctx: typer.Context, args: list[str]) -> list[str]:
        remaining = super().parse_args(ctx, args)
        if ctx.resilient_parsing:
            return remaining
        params = {param.name: param for param in self.params}
        for group in self.mutually_exclusive_groups:
            selected = [name for name in group if ctx.params.get(name)]
            if len(selected) > 1:
                options = [params[name].opts[0] for name in selected]
                raise typer.BadParameter(
                    f"options {', '.join(options)} are mutually exclusive", ctx=ctx,
                )
        if not any(ctx.params.get(name) for name in self.mutually_exclusive_groups[0]):
            raise typer.BadParameter(
                "choose one of --all, --id, --label or --section", ctx=ctx,
            )
        return remaining


def update(
    ctx: typer.Context,
    course: str = typer.Option(..., "--course", "-c", metavar="COURSE", help="Moodle course ID or alias"),
    all_: bool = typer.Option(
        False, "--all", "-A", help="Select every VPL in the course", rich_help_panel=SELECTION_PANEL,
    ),
    ids: list[int] | None = typer.Option(
        None, "--id", "-I", min=1, metavar="ID",
        help="Activity ID; repeat --id for multiple activities", rich_help_panel=SELECTION_PANEL,
    ),
    labels: list[str] | None = typer.Option(
        None, "--label", "-L", metavar="LABEL",
        help="Exact activity label; repeat --label for multiple labels", rich_help_panel=SELECTION_PANEL,
    ),
    sections: list[int] | None = typer.Option(
        None, "--section", "-S", min=0, metavar="INDEX",
        help="Section index from mula list (starts at 0); repeat --section", rich_help_panel=SELECTION_PANEL,
    ),
    info: bool = typer.Option(
        False, "--info", help="Update title and description; requires --repo", rich_help_panel=ACTION_PANEL,
    ),
    duedate: str | None = typer.Option(
        None, "--duedate", metavar="DATE",
        help="Closing date YYYY:MM:DD:HH:MM; 0 disables it", rich_help_panel=ACTION_PANEL,
    ),
    maxfiles: int | None = typer.Option(
        None, "--maxfiles", min=0, metavar="COUNT",
        help="Maximum student files (at least the number of preserved files)", rich_help_panel=ACTION_PANEL,
    ),
    visible: int | None = typer.Option(
        None, "--visible", min=0, max=1, metavar="0|1",
        help="Hide (0) or show (1) the activity", rich_help_panel=ACTION_PANEL,
    ),
    exec_: bool = typer.Option(
        False, "--exec", help="Enable Run, Evaluate and Debug", rich_help_panel=ACTION_PANEL,
    ),
    repo: Path | None = typer.Option(
        None, "--repo", "-r", metavar="DIR", exists=True, file_okay=False, readable=True,
        help="Local task repository used by --info", rich_help_panel=SOURCE_PANEL,
    ),
    drafts: str | None = typer.Option(
        None, "--lang", "-l", metavar="LANG",
        help="Send starter files for a language (e.g. py); requires --info", rich_help_panel=SOURCE_PANEL,
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="List pending activities without updating or writing files",
        rich_help_panel=EXECUTION_PANEL,
    ),
    threads: int = typer.Option(
        1, "--threads", "-t", min=1, metavar="COUNT",
        help="Concurrent workers when executing updates", rich_help_panel=EXECUTION_PANEL,
    ),
) -> None:
    """Update selected VPL activities in Moodle.

    Choose one selection, then specify one or more changes.
    Progress and parameters are saved automatically to operation.json in the Mula cache.
    The file opens in VS Code for monitoring. Use mula resume to retry pending tasks.
    --dry-run only lists the selection and does not require changes or --repo.

    Examples:
      mula update -c course --id 123 --id 456 --visible 0
      mula update -c course --all --info --repo ./tasks --lang py
      mula resume
      mula update -c course --section 0 --dry-run
    """
    selection = normalize_selection(all_, ids, labels, sections, ctx.args)
    options = UpdateOptions(
        course=course, all_=selection.all, ids=selection.id,
        labels=selection.label, sections=selection.section,
        repo=str(repo) if repo is not None else None,
        dry_run=dry_run, info=info, drafts=drafts, duedate=duedate,
        maxfiles=maxfiles, visible=visible, exec_=exec_, threads=threads,
    )
    try:
        options.validate()
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    Credentials.load_credentials().fill_empty()
    try:
        Update.update(options)
    except (OSError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1) from error


def resume() -> None:
    """Resume pending tasks from the last add or update, using all saved parameters.

    No arguments or execution options are accepted.
    New add or update runs replace the previous checkpoint.
    Completed and skipped tasks are not repeated.
    """
    try:
        PublishWorkflow.resume()
    except (OSError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1) from error
