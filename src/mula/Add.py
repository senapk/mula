"""Create VPL activities with the shared publishing checkpoint."""

from dataclasses import dataclass, field
from pathlib import Path

from .credentials import Credentials
from .moodle_api import MoodleAPI
from .operation_state import OperationState
from .readme_manifest import ReadmeGroup, load_readme_groups
from .structure_loader import StructureLoader
from .task import Task
from .update import UpdateOptions
from .workflow import PublishWorkflow


@dataclass
class AddOptions:
    course: str
    repo: str
    targets: list[str] = field(default_factory=list)
    section: int = 0
    duedate: str = "0"
    maxfiles: int = 5
    visible: int | None = None
    exec_: bool = True
    drafts: str | None = None
    threads: int = 1
    dry_run: bool = False
    drop: bool = False
    from_readme: bool = False
    _readme_groups: tuple[ReadmeGroup, ...] | None = field(default=None, init=False, repr=False)

    def readme_groups(self) -> tuple[ReadmeGroup, ...]:
        if self._readme_groups is None:
            self._readme_groups = load_readme_groups(Path(self.repo), self.section)
        return self._readme_groups

    def execution_options(self) -> UpdateOptions:
        return UpdateOptions(
            course=self.course, repo=self.repo, info=True, exec_=self.exec_,
            duedate=self.duedate, maxfiles=self.maxfiles, visible=self.visible,
            drafts=self.drafts, threads=self.threads,
        )

    def validate(self) -> None:
        self.execution_options().validate()
        if not Path(self.repo).is_dir():
            raise ValueError("--repo must be an existing local repository directory")
        if type(self.section) is not int or self.section < 0:
            raise ValueError("--section must be a nonnegative integer")
        if self.from_readme and self.targets:
            raise ValueError("--from-readme and manual targets are mutually exclusive")
        if not self.targets and not self.from_readme:
            raise ValueError("provide LABEL or SECTION:LABEL targets, or use --from-readme")
        self.tasks()  # Validate all targets before requesting credentials or writing files.

    def tasks(self) -> list[Task]:
        selected: dict[tuple[int, str], Task] = {}
        param = self.execution_options().task_parameters()
        if self.from_readme:
            return [Task().set_section(group.section).set_label(label).set_drafts(self.drafts)
                    .set_param(param).set_status(Task.TODO)
                    for group in self.readme_groups() for label in group.labels]
        for target in self.targets:
            if not isinstance(target, str):
                raise ValueError("targets must be LABEL or SECTION:LABEL")
            section = self.section
            label = target
            if ":" in target:
                prefix, label = target.split(":", 1)
                try:
                    section = int(prefix)
                except ValueError as error:
                    raise ValueError(f"Invalid target {target!r}: use LABEL or SECTION:LABEL") from error
            label = label.strip().lstrip("@")
            if (section < 0 or not label or ":" in label
                    or Path(label).is_absolute() or ".." in Path(label).parts):
                raise ValueError(f"Invalid target {target!r}: use a relative label and section >= 0")
            key = (section, label)
            if key not in selected:
                selected[key] = (Task().set_section(section).set_label(label)
                                 .set_drafts(self.drafts).set_param(param).set_status(Task.TODO))
        return list(selected.values())


class Add:
    @staticmethod
    def add(options: AddOptions) -> None:
        options.validate()
        tasks = options.tasks()
        credentials = Credentials.load_credentials()
        credentials.set_course(options.course)
        credentials.repo_path = str(Path(options.repo).resolve())
        structure = StructureLoader.load()
        if options.from_readme:
            for group in options.readme_groups():
                if group.section >= structure.get_number_of_sections():
                    raise ValueError(
                        f"README group {group.title!r} requires section {group.section}; "
                        f"the course has {structure.get_number_of_sections()} sections. "
                        "Prepare the sections first or adjust --section."
                    )
        for task in tasks:
            if task.section >= structure.get_number_of_sections():
                raise ValueError(f"Section {task.section} is out of range; check mula list -c {options.course}")
        if options.drop:
            PublishWorkflow.drop_existing(tasks, structure)
        if options.dry_run:
            print(f"Dry run: {len(tasks)} activity/activities selected for add.")
            if options.from_readme:
                groups = options.readme_groups()
                statuses = {(task.section, task.label): task.status for task in tasks}
                for group in groups:
                    print(f"  {group.title} (@{group.marker}) -> Section {group.section}: "
                          f"{structure.section_labels[group.section]} | {len(group.labels)} tasks")
                    for label in group.labels:
                        print(f"    {label} [{statuses[group.section, label]}]")
                print(f"Total: {len(groups)} active groups, {len(tasks)} tasks.")
                return
            for task in tasks:
                print(f"  Section {task.section}: {structure.section_labels[task.section]} | {task.label} [{task.status}]")
            return

        execution = options.execution_options()
        execution.course = credentials.get_course()
        execution.repo = credentials.repo_path
        state = OperationState(execution, credentials.url, MoodleAPI.default_timeout, tasks, "add", drop=options.drop)
        state.save()
        state.open_in_vscode()
        PublishWorkflow.execute(state, structure)
