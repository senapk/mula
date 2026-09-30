"""Read the ordered task groups in a TKO repository index."""

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt


GROUP_MARKER = re.compile(r"<!--\s*@([\w./-]+)(.*?)-->", re.DOTALL)


@dataclass(frozen=True)
class ReadmeGroup:
    title: str
    marker: str
    section: int
    labels: tuple[str, ...]


def load_readme_groups(repo: Path, start_section: int = 0) -> tuple[ReadmeGroup, ...]:
    repo = repo.resolve()
    readme = repo / "README.md"
    try:
        source = readme.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Cannot read repository README: {readme}") from error
    lines = source.splitlines()
    if lines and lines[0].strip() == "---":
        end = next((index for index in range(1, len(lines)) if lines[index].strip() in ("---", "...")), None)
        if end is None:
            raise ValueError(f"Unclosed front matter in {readme}")
        source = "\n".join(lines[end + 1:])

    tokens = MarkdownIt("commonmark", {"html": True}).parse(source)
    groups: list[tuple[str, str, list[str]]] = []
    current: list[str] | None = None
    list_depth = 0
    for index, token in enumerate(tokens):
        if token.type == "list_item_open":
            list_depth += 1
        elif token.type == "list_item_close":
            list_depth -= 1
        elif token.type == "heading_open" and token.tag in ("h1", "h2"):
            current = None
            if token.tag != "h2":
                continue
            children = tokens[index + 1].children or []
            marker = next((match for child in children if child.type == "html_inline"
                           and (match := GROUP_MARKER.fullmatch(child.content))), None)
            if marker is None or re.search(r"\bactive\s*=\s*0\b", marker[2]):
                continue
            title = "".join(child.content for child in children if child.type in ("text", "code_inline")).strip()
            if not title:
                raise ValueError(f"Group @{marker[1]} has no title in {readme}")
            current = []
            groups.append((title, marker[1], current))
        elif token.type == "inline" and list_depth and current is not None:
            for child in token.children or []:
                if child.type != "link_open":
                    continue
                href = child.attrGet("href") or ""
                url = urlsplit(href)
                if url.scheme or url.netloc:
                    continue
                path = PurePosixPath(unquote(url.path).replace("\\", "/"))
                if path.name.lower() != "readme.md":
                    continue
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError(f"Task link must stay inside the repository: {href}")
                if path.parent == PurePosixPath("."):
                    continue  # A link to the repository index is not a task.
                task_readme = repo / str(path)
                if not task_readme.is_file():
                    raise ValueError(f"Task README not found: {task_readme}")
                if not task_readme.resolve().is_relative_to(repo):
                    raise ValueError(f"Task link resolves outside the repository: {href}")
                label = path.parent.as_posix()
                if ":" in label:
                    raise ValueError(f"Invalid task label in README: {label}")
                if label not in current:
                    current.append(label)

    if not any(labels for _, _, labels in groups):
        raise ValueError(f"No tasks found in active README groups: {readme}")
    return tuple(ReadmeGroup(title, marker, start_section + index, tuple(labels))
                 for index, (title, marker, labels) in enumerate(groups))
