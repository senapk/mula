"""Typer interface for creating VPLs from a local repository."""

from pathlib import Path

import typer
from typer.core import TyperCommand

from .Add import Add, AddOptions
from .credentials import Credentials


class AddCommand(TyperCommand):
    def parse_args(self, ctx: typer.Context, args: list[str]) -> list[str]:
        remaining = super().parse_args(ctx, args)
        if not ctx.resilient_parsing:
            if ctx.params.get("from_readme") and ctx.params.get("targets"):
                raise typer.BadParameter("--from-readme and manual targets are mutually exclusive", ctx=ctx)
            if not ctx.params.get("from_readme") and not ctx.params.get("targets"):
                raise typer.BadParameter("provide targets or choose --from-readme", ctx=ctx)
        return remaining


def add(
    targets: list[str] = typer.Argument([], metavar="[SECTION:]LABEL...", help="Task labels; exclusive with --from-readme"),
    course: str = typer.Option(..., "--course", "-c", metavar="COURSE", help="Moodle course ID or alias"),
    repo: Path = typer.Option(
        ..., "--repo", "-r", exists=True, file_okay=False, readable=True, metavar="DIR",
        help="Local task repository", rich_help_panel="Local content",
    ),
    drafts: str | None = typer.Option(
        None, "--lang", "-l", metavar="LANG", help="Send starter files for a language (e.g. py)",
        rich_help_panel="Local content",
    ),
    from_readme: bool = typer.Option(
        False, "--from-readme", help="Read active groups in repo/README.md into consecutive sections; exclusive with manual targets",
        rich_help_panel="Local content",
    ),
    section: int = typer.Option(
        0, "--section", "-S", min=0, metavar="INDEX", help="Default section, or first section for --from-readme (starts at 0)",
        rich_help_panel="Activity settings",
    ),
    duedate: str = typer.Option(
        "0", "--duedate", metavar="DATE", help="Closing date YYYY:MM:DD:HH:MM; 0 disables it",
        rich_help_panel="Activity settings",
    ),
    maxfiles: int = typer.Option(
        5, "--maxfiles", min=0, metavar="COUNT", help="Maximum student files (at least the number of preserved files)",
        rich_help_panel="Activity settings",
    ),
    visible: int | None = typer.Option(
        None, "--visible", min=0, max=1, metavar="0|1", help="Hide (0) or show (1); omit to keep the Moodle default",
        rich_help_panel="Activity settings",
    ),
    exec_: bool = typer.Option(
        True, "--exec/--no-exec", help="Enable Run, Evaluate and Debug", rich_help_panel="Activity settings",
    ),
    threads: int = typer.Option(
        1, "--threads", "-t", min=1, metavar="COUNT", help="Concurrent workers",
        rich_help_panel="Execution",
    ),
    drop: bool = typer.Option(
        False, "--drop", help="Skip keys already present in the destination section",
        rich_help_panel="Execution",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="List targets without publishing, saving a checkpoint or opening VS Code",
        rich_help_panel="Execution",
    ),
) -> None:
    """Create VPL activities from a local repository.

    Pass LABEL or SECTION:LABEL targets. Existing labels in the target section
    are updated unless --drop skips them. Title and description are always loaded from the repository.
    Alternatively, --from-readme distributes active README groups from --section.
    Includes checked and unchecked tasks. Destination sections must already exist.
    Parameters and progress are saved to operation.json in the Mula cache,
    which opens in VS Code. Use mula resume to retry pending tasks.

    Examples:
      mula add -c course -r ./tasks -l py 3:labs/car 5:labs/bike
      mula add -c course -r ./tasks --section 2 labs/car labs/bike
      mula add -c course -r ./tasks --dry-run 3:labs/car
      mula add -c course -r ./tasks --from-readme --section 1 -l py --dry-run
      mula resume
    """
    options = AddOptions(
        course=course, repo=str(repo), targets=targets, section=section,
        duedate=duedate, maxfiles=maxfiles, visible=visible, exec_=exec_,
        drafts=drafts, threads=threads, dry_run=dry_run, from_readme=from_readme, drop=drop,
    )
    try:
        options.validate()
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    Credentials.load_credentials().fill_empty()
    try:
        Add.add(options)
    except (OSError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1) from error
