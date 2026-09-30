import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from mula.__main__ import app
from mula.Add import Add, AddOptions
from mula.credentials import Credentials
from mula.moodle_api import MoodleAPI
from mula.operation_state import OperationState
from mula.publish import Publish
from mula.task import Task
from mula.structure import Structure
from mula.update import UpdateOptions
from mula.workflow import PublishWorkflow


class AddTest(TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name)
        self.path = self.repo / "cache" / "operation.json"
        path_patch = patch("mula.operation_state.checkpoint_path", return_value=self.path)
        path_patch.start()
        self.addCleanup(path_patch.stop)
        self.credentials = Credentials()
        self.credentials.username = "test"
        self.credentials.password = "test"
        self.credentials.course_alias = {"course": 42}
        credentials_patch = patch("mula.credentials.Credentials.load_credentials", return_value=self.credentials)
        credentials_patch.start()
        self.addCleanup(credentials_patch.stop)
        original_timeout = MoodleAPI.default_timeout
        self.addCleanup(setattr, MoodleAPI, "default_timeout", original_timeout)

    def options(self, **values) -> AddOptions:
        return AddOptions(course="course", repo=str(self.repo), targets=["2:labs/car", "labs/bike"], **values)

    def structure(self):
        result = Mock()
        result.get_number_of_sections.return_value = 4
        result.section_labels = ["zero", "one", "two", "three"]
        return result

    def test_cli_passes_typed_options_and_effective_defaults(self) -> None:
        with patch("mula.cli_add.Add.add") as add, patch.object(self.credentials, "load_file", return_value=self.credentials):
            result = CliRunner().invoke(app, ["add", "-c", "course", "-r", str(self.repo), "2:labs/car", "labs/bike"])
            self.assertEqual(result.exit_code, 0, result.output)
            options = add.call_args.args[0]
            self.assertIsInstance(options, AddOptions)
            self.assertEqual(options.targets, ["2:labs/car", "labs/bike"])
            self.assertEqual(options.section, 0)
            self.assertEqual(options.threads, 1)
            self.assertEqual(options.maxfiles, 5)
            self.assertEqual(options.duedate, "0")
            self.assertTrue(options.exec_)
            self.assertTrue(options.execution_options().info)

    def test_cli_changes_are_forwarded_and_legacy_flags_are_rejected(self) -> None:
        with patch.object(self.credentials, "load_file", return_value=self.credentials):
            with patch("mula.cli_add.Add.add") as add:
                result = CliRunner().invoke(app, [
                    "add", "-c", "course", "-r", str(self.repo), "-S", "1", "--visible", "0",
                    "--maxfiles", "0", "--duedate", "2026:10:15:23:59", "--no-exec", "-l", "py",
                    "-t", "3", "--dry-run", "--drop", "labs/car",
                ])
                self.assertEqual(result.exit_code, 0, result.output)
                options = add.call_args.args[0]
                self.assertEqual((options.section, options.visible, options.maxfiles, options.threads), (1, 0, 0, 3))
                self.assertFalse(options.exec_)
                self.assertTrue(options.dry_run)
                self.assertTrue(options.drop)
                self.assertEqual(options.drafts, "py")
            for flag in ("--create", "--follow"):
                with self.subTest(flag=flag), patch("mula.cli_add.Add.add") as add:
                    result = CliRunner().invoke(app, ["add", "-c", "course", "-r", str(self.repo), "labs/car", flag, "file"])
                    self.assertEqual(result.exit_code, 2, result.output)
                    add.assert_not_called()

    def test_invalid_cli_parameters_do_not_authenticate_or_overwrite(self) -> None:
        self.path.parent.mkdir()
        self.path.write_text("previous", encoding="utf-8")
        cases = (
            [], ["bad:labs/car"], ["-1:labs/car"], ["3:"], ["labs/car", "--duedate", "2026:2:30:12:00"],
            ["labs/car", "--threads", "0"], ["../car"], ["/absolute"], [""],
        )
        with patch.object(self.credentials, "load_file", return_value=self.credentials), \
             patch.object(self.credentials, "fill_empty") as auth:
            for arguments in cases:
                with self.subTest(arguments=arguments), patch("mula.cli_add.Add.add") as add:
                    result = CliRunner().invoke(app, ["add", "-c", "course", "-r", str(self.repo), *arguments])
                    self.assertEqual(result.exit_code, 2, result.output)
                    add.assert_not_called()
            auth.assert_not_called()
        self.assertEqual(self.path.read_text(encoding="utf-8"), "previous")

    def test_help_does_not_request_credentials(self) -> None:
        with patch.object(self.credentials, "load_file", return_value=self.credentials), \
             patch.object(self.credentials, "fill_empty") as auth:
            result = CliRunner().invoke(app, ["add", "--help"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Activity settings", result.output)
            self.assertIn("mula resume", result.output)
            self.assertNotIn("--follow", result.output)
            self.assertNotIn("--create", result.output)
            auth.assert_not_called()

    def test_task_sections_override_default_and_duplicates_are_collapsed(self) -> None:
        options = self.options(section=1, drafts="py")
        options.targets += ["2:labs/car", "@labs/bike"]
        tasks = options.tasks()
        self.assertEqual([(task.section, task.label) for task in tasks], [(2, "labs/car"), (1, "labs/bike")])
        self.assertTrue(all(task.id == 0 and task.status == Task.TODO for task in tasks))
        self.assertTrue(all(task.param.info and task.param.exec and task.drafts == "py" for task in tasks))

    def test_new_add_replaces_update_checkpoint_before_editor_and_execution(self) -> None:
        previous = OperationState(UpdateOptions(course="999", visible=0), "https://other.example", 10,
                                  [Task().set_id(456).set_status(Task.TODO)])
        previous.save()

        def inspect_editor():
            state = OperationState.load()
            self.assertEqual(state.operation, "add")
            self.assertEqual(state.options.course, "42")
            self.assertEqual(state.options.repo, str(self.repo))
            self.assertEqual([task.id for task in state.tasks], [0, 0])
            self.assertEqual([task.section for task in state.tasks], [2, 0])

        with patch("mula.Add.StructureLoader.load", return_value=self.structure()), \
             patch.object(OperationState, "open_in_vscode", side_effect=inspect_editor) as editor, \
             patch.object(PublishWorkflow, "execute") as execute:
            Add.add(self.options())
            editor.assert_called_once()
            execute.assert_called_once()
        self.assertEqual(json.loads(self.path.read_text())["operation"], "add")

    def test_add_dry_run_and_invalid_section_preserve_previous_state(self) -> None:
        self.path.parent.mkdir()
        self.path.write_text("previous", encoding="utf-8")
        with patch("mula.Add.StructureLoader.load", return_value=self.structure()), \
             patch.object(OperationState, "open_in_vscode") as editor, \
             patch.object(PublishWorkflow, "execute") as execute:
            Add.add(self.options(dry_run=True))
            options = self.options()
            options.targets = ["4:labs/car"]
            with self.assertRaisesRegex(ValueError, "out of range"):
                Add.add(options)
            editor.assert_not_called()
            execute.assert_not_called()
        self.assertEqual(self.path.read_text(encoding="utf-8"), "previous")

    def test_resume_retries_only_pending_add_tasks_with_saved_sections(self) -> None:
        options = self.options(drafts="py", visible=0)
        tasks = options.tasks()
        tasks += [Task().set_id(789).set_section(3).set_label("labs/done").set_drafts("py").set_status(Task.DONE)]
        tasks[1].set_status(Task.FAIL)
        execution = options.execution_options()
        execution.course = "42"
        state = OperationState(execution, "https://saved.example", 27, tasks, "add")
        state.save()

        def publisher(task):
            result = Mock()
            result.set_section.return_value = result
            result.set_structure.return_value = result
            result.execute.side_effect = lambda: task.set_id(123 + task.section).set_status(Task.DONE)
            return result

        with patch("mula.workflow.StructureLoader.load", return_value=self.structure()), \
             patch.object(OperationState, "open_in_vscode"), \
             patch("mula.workflow.Publish", side_effect=publisher) as publish:
            PublishWorkflow.resume()
            self.assertEqual([call.args[0].section for call in publish.call_args_list], [2, 0])
        restored = OperationState.load()
        self.assertEqual(restored.operation, "add")
        self.assertEqual([task.status for task in restored.tasks], [Task.DONE] * 3)
        self.assertEqual([task.id for task in restored.tasks], [125, 123, 789])
        self.assertEqual(restored.options.visible, 0)
        self.assertEqual(restored.options.drafts, "py")
        self.assertEqual(self.credentials.url, "https://saved.example")
        self.assertEqual(MoodleAPI.default_timeout, 27)

    def test_legacy_update_checkpoint_can_be_resumed_and_upgraded(self) -> None:
        state = OperationState(UpdateOptions(course="42", visible=0), "https://saved.example", 27,
                               [Task().set_id(123).set_status(Task.FAIL)])
        state.save()
        payload = json.loads(self.path.read_text())
        payload["version"] = 1
        del payload["operation"]
        self.path.with_name("update.json").write_text(json.dumps(payload))
        self.path.unlink()
        with patch("mula.workflow.StructureLoader.load", return_value=self.structure()), \
             patch.object(OperationState, "open_in_vscode") as editor, \
             patch.object(PublishWorkflow, "execute") as execute:
            PublishWorkflow.resume()
            editor.assert_called_once()
            self.assertEqual(execute.call_args.args[0].operation, "update")
        self.assertEqual(OperationState.load().operation, "update")
        self.assertEqual(json.loads(self.path.read_text())["version"], 2)

    def test_created_activity_id_is_preserved_if_upload_fails(self) -> None:
        task = Task().set_label("labs/car").set_section(2).set_status(Task.TODO)
        task.log = Mock()
        publisher = object.__new__(Publish)
        publisher.task = task
        publisher.api = Mock()
        publisher.structure = Mock()
        publisher.section = 2
        publisher.send_basic = Mock(return_value=123)
        publisher.update_exec = Mock(side_effect=RuntimeError("upload failed"))
        publisher.execute = Mock(side_effect=lambda: publisher.apply_action(Mock(title="Car")))
        options = self.options().execution_options()
        options.course = "42"
        state = OperationState(options, "https://saved.example", 10, [task], "add")
        state.save()
        with patch("mula.workflow.Publish", return_value=publisher):
            with self.assertRaisesRegex(RuntimeError, "upload failed"):
                PublishWorkflow.execute(state, self.structure())
        self.assertEqual(task.id, 123)
        restored = OperationState.load().tasks[0]
        self.assertEqual(restored.id, 123)
        self.assertEqual(restored.status, Task.FAIL)

    def test_drop_skips_existing_key_only_in_destination_section_and_survives_resume(self) -> None:
        existing = Task().set_id(123).set_section(2).set_label("labs/car")
        other_section = Task().set_id(456).set_section(1).set_label("labs/bike")
        structure = Structure([[], [other_section], [existing], []], ["zero", "one", "two", "three"])
        with patch("mula.Add.StructureLoader.load", return_value=structure), \
             patch.object(OperationState, "open_in_vscode"), \
             patch.object(PublishWorkflow, "execute"):
            Add.add(self.options(drop=True))
        state = OperationState.load()
        self.assertTrue(state.drop)
        self.assertEqual([task.status for task in state.tasks], [Task.SKIP, Task.TODO])

        # A key added since the checkpoint is also skipped on resume.
        structure.add_entry(0, 789, "@labs/bike Bike")
        with patch("mula.workflow.StructureLoader.load", return_value=structure), \
             patch.object(OperationState, "open_in_vscode"), \
             patch("mula.workflow.Publish") as publish:
            PublishWorkflow.resume()
            publish.assert_not_called()
        self.assertEqual([task.status for task in OperationState.load().tasks], [Task.SKIP, Task.SKIP])

    def test_drop_does_not_skip_retry_of_activity_created_by_same_operation(self) -> None:
        task = Task().set_id(123).set_section(2).set_label("labs/car").set_status(Task.FAIL)
        structure = Structure([[], [], [task], []], ["zero", "one", "two", "three"])
        PublishWorkflow.drop_existing([task], structure)
        self.assertEqual(task.status, Task.FAIL)
