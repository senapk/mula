"""Shared execution and resumption for add and update."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .credentials import Credentials
from .log import Log
from .moodle_api import MoodleAPI
from .operation_state import OperationState
from .publish import Publish
from .structure import Structure
from .structure_loader import StructureLoader
from .task import Task
from .text import Text


class PublishWorkflow:
    @staticmethod
    def drop_existing(tasks: list[Task], structure: Structure) -> None:
        for task in tasks:
            if (task.id == 0 and task.status in (Task.TODO, Task.FAIL)
                    and structure.search_by_label(task.label, task.section)):
                task.set_status(Task.SKIP)
                print(f"- Skip Section {task.section}: {task.label} (key already exists)")

    @staticmethod
    def execute(state: OperationState, structure: Structure) -> None:
        if state.operation == "add" and state.drop:
            PublishWorkflow.drop_existing(state.tasks, structure)
        lock = threading.Lock()

        def worker(entry: tuple[int, Task]) -> None:
            index, task = entry
            if task.status in (Task.DONE, Task.SKIP):
                return
            try:
                if state.options.threads == 1:
                    print(Text.format("{y}", f"- Start {task.id}: {task.label} - {task.title}"))
                else:
                    log_name = str(task.id) if task.id else f"add-{task.section}-{index}"
                    log_file = os.path.join(".log", log_name)
                    os.makedirs(".log", exist_ok=True)
                    task.set_log(Log(log_file))
                    print(f"- Start {task.id}: {task.label} - {task.title} with log file: {log_file}")
                Publish(task).set_section(task.section).set_structure(structure).execute()
                print(f"- Finish {task.label}")
            except Exception:
                task.set_status(Task.FAIL)
                raise
            finally:
                with lock:
                    state.save()

        try:
            with ThreadPoolExecutor(max_workers=state.options.threads) as executor:
                for _ in executor.map(worker, enumerate(state.tasks)):
                    pass  # Consume results so worker failures reach the caller.
        finally:
            state.save()

    @staticmethod
    def resume() -> None:
        state = OperationState.load()
        if not any(task.status in (Task.TODO, Task.FAIL) for task in state.tasks):
            print("No pending tasks in the last operation.")
            return
        if state.options.info and not Path(state.options.repo or "").is_dir():
            raise ValueError(f"Saved repository is unavailable: {state.options.repo}")
        credentials = Credentials.load_credentials()
        credentials.url = state.moodle_url
        credentials.set_course(state.options.course)
        credentials.repo_path = state.options.repo
        MoodleAPI.default_timeout = state.timeout
        credentials.fill_empty()
        structure = StructureLoader.load()
        state.save()  # Also upgrades a legacy update.json before opening the current file.
        state.open_in_vscode()
        PublishWorkflow.execute(state, structure)
