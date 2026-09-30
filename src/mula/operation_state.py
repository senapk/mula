"""The single checkpoint for the most recent add or update."""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from platformdirs import user_cache_path

from .task import Task

if TYPE_CHECKING:
    from .update import UpdateOptions


OPTION_FIELDS = (
    "course", "repo", "info", "drafts", "duedate", "maxfiles", "visible", "exec_", "threads",
)
TASK_FIELDS = ("status", "id", "section", "label", "title", "drafts")


def checkpoint_path() -> Path:
    return user_cache_path("mula") / "operation.json"


@dataclass
class OperationState:
    options: "UpdateOptions"
    moodle_url: str
    timeout: int
    tasks: list[Task]
    operation: str = "update"
    drop: bool = False

    def save(self) -> None:
        """Replace the checkpoint atomically; callers synchronize worker writes."""
        path = checkpoint_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 2,
            "operation": self.operation,
            "drop": self.drop,
            "moodle_url": self.moodle_url,
            "timeout": self.timeout,
            "options": {name: getattr(self.options, name) for name in OPTION_FIELDS},
        }
        temporary: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix=".operation-", suffix=".tmp", delete=False,
            ) as file:
                temporary = Path(file.name)
                header = json.dumps(payload, ensure_ascii=False, indent=2)
                file.write(header[:-2] + ',\n  "tasks": [')
                for index, task in enumerate(self.tasks):
                    row = {name: getattr(task, name) for name in TASK_FIELDS}
                    separator = "," if index else ""
                    file.write(separator + "\n    { " + json.dumps(row, ensure_ascii=False)[1:-1] + " }")
                file.write("\n  ]\n}\n" if self.tasks else "]\n}\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @classmethod
    def load(cls) -> "OperationState":
        from .update import UpdateOptions

        path = checkpoint_path()
        # Read the previously supported update checkpoint if no new run exists.
        if not path.exists():
            legacy = path.with_name("update.json")
            if legacy.exists():
                path = legacy
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise ValueError("No saved operation found. Run mula add or mula update first.") from error
        except (json.JSONDecodeError, UnicodeError) as error:
            raise ValueError(f"Invalid operation checkpoint: {path}") from error

        try:
            if not isinstance(payload, dict) or type(payload["version"]) is not int:
                raise ValueError("invalid format")
            if payload["version"] not in (1, 2):
                raise ValueError("unsupported format version")
            operation = "update" if payload["version"] == 1 else payload["operation"]
            if operation not in ("add", "update"):
                raise ValueError("unknown operation")
            drop = payload.get("drop", False)
            if type(drop) is not bool or (drop and operation != "add"):
                raise ValueError("invalid drop option")
            url = payload["moodle_url"]
            if not isinstance(url, str):
                raise ValueError("invalid Moodle URL")
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username:
                raise ValueError("invalid Moodle URL")
            timeout = payload["timeout"]
            if type(timeout) is not int or timeout < 1:
                raise ValueError("invalid timeout")
            values = payload["options"]
            if not isinstance(values, dict) or set(values) != set(OPTION_FIELDS):
                raise ValueError("invalid saved options")
            options = UpdateOptions(**values)
            options.validate()
            if operation == "add" and not options.info:
                raise ValueError("add requires local content")
            if options.repo is not None and not Path(options.repo).is_absolute():
                raise ValueError("saved repository path must be absolute")

            rows = payload["tasks"]
            if not isinstance(rows, list) or not rows:
                raise ValueError("invalid task list")
            tasks: list[Task] = []
            seen: set[int] = set()
            for row in rows:
                if not isinstance(row, dict) or set(row) != set(TASK_FIELDS):
                    raise ValueError("invalid task")
                minimum_id = 0 if operation == "add" else 1
                if (type(row["id"]) is not int or row["id"] < minimum_id
                        or (row["id"] > 0 and row["id"] in seen)):
                    raise ValueError("invalid or duplicate activity ID")
                if type(row["section"]) is not int or row["section"] < 0:
                    raise ValueError("invalid section")
                if not all(isinstance(row[name], str) for name in ("label", "title", "status")):
                    raise ValueError("invalid task text")
                if row["status"] not in (Task.TODO, Task.FAIL, Task.DONE, Task.SKIP):
                    raise ValueError("invalid task status")
                if row["drafts"] is not None and not isinstance(row["drafts"], str):
                    raise ValueError("invalid task language")
                if row["drafts"] != options.drafts:
                    raise ValueError("task language differs from saved options")
                task = Task()
                for name in TASK_FIELDS:
                    setattr(task, name, row[name])
                task.set_param(options.task_parameters())
                tasks.append(task)
                if task.id > 0:
                    seen.add(task.id)
            if operation == "add":
                targets = [(task.section, task.label) for task in tasks]
                if any(not task.label.strip() for task in tasks) or len(set(targets)) != len(targets):
                    raise ValueError("invalid or duplicate add targets")
            return cls(options, url, timeout, tasks, operation, drop=drop)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid operation checkpoint {path}: {error}") from error

    def open_in_vscode(self) -> None:
        path = checkpoint_path()
        print(f"{self.operation.capitalize()} checkpoint: {path}")
        try:
            subprocess.run(
                ["code", "--reuse-window", str(path)],
                check=True, capture_output=True, timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            print(f"Warning: could not open VS Code. Follow the progress in {path}.")
