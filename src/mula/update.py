"""Update workflow and its typed input contract."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .credentials import Credentials
from .moodle_api import MoodleAPI
from .operation_state import OperationState
from .workflow import PublishWorkflow
from .structure import Structure
from .structure_loader import StructureLoader
from .task import Task, TaskParameters


@dataclass
class UpdateOptions:
    """Parameters passed from the CLI to the update workflow."""

    course: str
    all_: bool = False
    ids: list[int] | None = None
    labels: list[str] | None = None
    sections: list[int] | None = None
    repo: str | None = None
    dry_run: bool = False
    info: bool = False
    drafts: str | None = None
    duedate: str | None = None
    maxfiles: int | None = None
    visible: int | None = None
    exec_: bool = False
    threads: int = 1

    def has_action(self) -> bool:
        return any((
            self.info, self.exec_, self.drafts is not None,
            self.duedate is not None, self.maxfiles is not None,
            self.visible is not None,
        ))

    def validate(self) -> None:
        if not isinstance(self.course, str) or not self.course.strip():
            raise ValueError("invalid course")
        if type(self.info) is not bool or type(self.exec_) is not bool:
            raise ValueError("invalid action flags")
        if type(self.threads) is not int or self.threads < 1:
            raise ValueError("--threads must be a positive integer")
        if self.visible is not None and (type(self.visible) is not int or self.visible not in (0, 1)):
            raise ValueError("--visible must be 0 or 1")
        if self.maxfiles is not None and (type(self.maxfiles) is not int or self.maxfiles < 0):
            raise ValueError("--maxfiles must be a nonnegative integer")
        for name in ("repo", "drafts", "duedate"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"invalid --{name}")
        if self.duedate is not None and self.duedate != "0":
            try:
                year, month, day, hour, minute = (int(part) for part in self.duedate.split(":"))
                datetime(year, month, day, hour, minute)
            except ValueError as error:
                raise ValueError("--duedate requires 0 or a valid YYYY:MM:DD:HH:MM date") from error
        if self.dry_run:
            return
        if not self.has_action():
            raise ValueError(
                "specify at least one change: --info, --duedate, --maxfiles, --visible or --exec"
            )
        if self.drafts is not None and not self.info:
            raise ValueError("--lang requires --info")
        if self.info and self.repo is None:
            raise ValueError("--info requires --repo <local repository>")

    def task_parameters(self) -> TaskParameters:
        param = TaskParameters()
        param.duedate = self.duedate
        param.maxfiles = self.maxfiles
        param.info = self.info
        param.exec = self.exec_
        if self.visible is not None:
            param.visible = self.visible == 1
        return param


class Update:
    @staticmethod
    def update(options: UpdateOptions) -> None:
        options.validate()
        credentials = Credentials.load_credentials()
        credentials.repo_path = options.repo
        credentials.set_course(options.course)
        structure = StructureLoader.load()
        tasks = Update.load_itens_from_structure(
            options.all_, options.sections, options.ids, options.labels, structure,
        )
        if not tasks:
            print("No activities matched the selection. Check the course with mula list -c <course>.")
            return
        if options.dry_run:
            Update.print_dry_run(tasks, structure)
            return

        # Store the resolved ID and an absolute path, independent of aliases and cwd.
        options.course = credentials.get_course()
        if options.repo is not None:
            options.repo = str(Path(options.repo).resolve())
            credentials.repo_path = options.repo
        param = options.task_parameters()
        for task in tasks:
            task.set_param(param).set_drafts(options.drafts).set_status(Task.TODO)
        state = OperationState(options, credentials.url, MoodleAPI.default_timeout, tasks)
        state.save()
        state.open_in_vscode()
        PublishWorkflow.execute(state, structure)

    @staticmethod
    def print_dry_run(task_list: list[Task], structure: Structure) -> None:
        pending = [task for task in task_list if task.status not in (Task.DONE, Task.SKIP)]
        print(f"Dry run: {len(pending)} activity/activities selected for update.")
        for task in pending:
            section = task.section
            if 0 <= section < structure.get_number_of_sections():
                section_name = structure.section_labels[section]
            else:
                section_name = "unknown section"
            print(f"  ID {task.id} | Section {section}: {section_name} | {task.label} | {task.title}")
        skipped = len(task_list) - len(pending)
        if skipped:
            print(f"Skipped {skipped} completed or skipped activity/activities.")

    @staticmethod
    def load_itens_from_structure(
        args_all: bool, args_section: list[int] | None, args_ids: list[int] | None,
        args_labels: list[str] | None, structure: Structure,
    ) -> list[Task]:
        item_list: list[Task] = []
        if args_all:
            item_list = structure.get_itens()
        elif args_section and len(args_section) > 0:
            for section in args_section:
                if 0 <= section < structure.get_number_of_sections():
                    item_list += structure.get_itens(section)
                else:
                    print(f"Section {section} is out of range (0-{structure.get_number_of_sections() - 1}).")
        elif args_ids:
            for qid in args_ids:
                if structure.has_id(qid):
                    item_list.append(structure.get_item(qid))
                else:
                    print("    - id not found: ", qid)
        if args_labels:
            for label in args_labels:
                item_list += [item for item in structure.get_itens() if item.label == label]
        return list({item.id: item for item in item_list}.values())
