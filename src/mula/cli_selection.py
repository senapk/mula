"""Normalize activity selectors, including the legacy multi-value syntax."""

from dataclasses import dataclass

import typer


@dataclass
class ActivitySelection:
    all: bool
    id: list[int] | None
    label: list[str] | None
    section: list[int] | None


def normalize_selection(
    all_: bool,
    ids: list[int] | None,
    labels: list[str] | None,
    sections: list[int] | None,
    extra_values: list[str] | None = None,
) -> ActivitySelection:
    ids = list(ids) if ids else None
    labels = list(labels) if labels else None
    sections = list(sections) if sections else None
    selected = [bool(all_), bool(ids), bool(labels), bool(sections)]
    if sum(selected) > 1:
        raise typer.BadParameter("choose only one of --all, --id, --label or --section")
    if extra_values:
        if any(value.startswith("-") for value in extra_values):
            raise typer.BadParameter(f"unexpected option or argument: {extra_values[0]}")
        if ids:
            try:
                ids.extend(int(value) for value in extra_values)
            except ValueError as error:
                raise typer.BadParameter("activity IDs must be integers") from error
        elif labels:
            labels.extend(extra_values)
        elif sections:
            try:
                sections.extend(int(value) for value in extra_values)
            except ValueError as error:
                raise typer.BadParameter("section indices must be integers") from error
        else:
            raise typer.BadParameter("choose --all, --id, --label or --section before extra values")
    if ids and any(value < 1 for value in ids):
        raise typer.BadParameter("IDs must be greater than zero")
    if sections and any(value < 0 for value in sections):
        raise typer.BadParameter("section indices cannot be negative")
    return ActivitySelection(all=all_, id=ids, label=labels, section=sections)
