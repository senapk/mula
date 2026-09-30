import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from mula.credentials import Credentials
from mula.moodle_api import MoodleAPI
from mula.task import Task
from mula.update import Update, UpdateOptions
from mula.workflow import PublishWorkflow
from mula.operation_state import OperationState


class OperationStateTest(TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory / "cache" / "operation.json"
        path_patch = patch("mula.operation_state.checkpoint_path", return_value=self.path)
        path_patch.start()
        self.addCleanup(path_patch.stop)
        self.credentials = Credentials()
        self.credentials.username = "test-user"
        self.credentials.password = "test-password"
        self.credentials.course_alias = {"course": 42}
        credentials_patch = patch("mula.credentials.Credentials.load_credentials", return_value=self.credentials)
        credentials_patch.start()
        self.addCleanup(credentials_patch.stop)
        original_timeout = MoodleAPI.default_timeout
        self.addCleanup(setattr, MoodleAPI, "default_timeout", original_timeout)

    def make_state(self, statuses=(Task.TODO,), **options) -> OperationState:
        settings = UpdateOptions(course="42", visible=0, duedate="0", **options)
        tasks = [
            Task().set_id(123 + index).set_section(0).set_label("labs/task")
            .set_title("Título, com: pontuação").set_status(status).set_drafts(settings.drafts)
            .set_param(settings.task_parameters())
            for index, status in enumerate(statuses)
        ]
        return OperationState(settings, "https://saved.example", 27, tasks)

    def test_round_trip_preserves_complete_context_without_credentials(self) -> None:
        state = self.make_state(
            (Task.TODO, Task.FAIL, Task.DONE, Task.SKIP), info=True,
            repo=str(self.directory), drafts="py", maxfiles=5, exec_=True, threads=4,
        )
        state.save()
        loaded = OperationState.load()
        self.assertEqual(loaded.moodle_url, state.moodle_url)
        self.assertEqual(loaded.timeout, 27)
        self.assertEqual(loaded.options, state.options)
        self.assertEqual([task.status for task in loaded.tasks], [Task.TODO, Task.FAIL, Task.DONE, Task.SKIP])
        self.assertEqual(loaded.tasks[0].title, "Título, com: pontuação")
        self.assertFalse(loaded.tasks[0].param.visible)
        self.assertEqual(loaded.tasks[0].param.duedate, "0")
        self.assertTrue(loaded.tasks[0].param.info)
        self.assertTrue(loaded.tasks[0].param.exec)
        self.assertEqual(loaded.tasks[0].drafts, "py")
        text = self.path.read_text(encoding="utf-8")
        self.assertNotIn("test-user", text)
        self.assertNotIn("test-password", text)

    def test_missing_or_broken_checkpoint_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "No saved operation"):
            OperationState.load()
        self.path.parent.mkdir()
        for text in ("not json", "{}", "[]", "null"):
            with self.subTest(text=text):
                self.path.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Invalid operation checkpoint"):
                    OperationState.load()

    def test_invalid_saved_parameters_or_tasks_are_rejected(self) -> None:
        state = self.make_state()
        state.save()
        original = json.loads(self.path.read_text(encoding="utf-8"))
        cases = (
            ("version", 3), ("timeout", 0), ("moodle_url", "not a URL"),
            ("threads", 0), ("visible", False), ("duedate", "2026:02:30:12:00"),
            ("info", "false"), ("tasks", []), ("status", "unknown"), ("id", 0),
        )
        for field, value in cases:
            with self.subTest(field=field):
                payload = json.loads(json.dumps(original))
                if field in ("threads", "visible", "duedate", "info"):
                    payload["options"][field] = value
                elif field in ("status", "id"):
                    payload["tasks"][0][field] = value
                else:
                    payload[field] = value
                self.path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Invalid operation checkpoint"):
                    OperationState.load()

    def test_failed_atomic_replace_preserves_previous_checkpoint(self) -> None:
        state = self.make_state()
        state.save()
        previous = self.path.read_bytes()
        state.tasks[0].set_status(Task.DONE)
        with patch("mula.operation_state.os.replace", side_effect=OSError("failed")):
            with self.assertRaises(OSError):
                state.save()
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_new_update_saves_resolved_context_before_opening_and_executing(self) -> None:
        task = Task().set_id(123).set_title("Task").set_label("labs/task")
        self.make_state().save()
        options = UpdateOptions(course="course", all_=True, info=True, repo=".", drafts="py")

        def inspect_open() -> None:
            loaded = OperationState.load()
            self.assertEqual(loaded.options.course, "42")
            self.assertEqual(loaded.options.repo, str(Path.cwd()))
            self.assertTrue(loaded.options.info)
            self.assertEqual(loaded.tasks[0].status, Task.TODO)
            self.assertEqual(loaded.tasks[0].drafts, "py")

        with patch("mula.structure_loader.StructureLoader.load") as load, \
             patch.object(Update, "load_itens_from_structure", return_value=[task]), \
             patch.object(OperationState, "open_in_vscode", side_effect=inspect_open) as editor, \
             patch.object(PublishWorkflow, "execute") as execute:
            Update.update(options)
            editor.assert_called_once()
            execute.assert_called_once()
            self.assertIs(execute.call_args.args[1], load.return_value)
        self.assertEqual(self.credentials.get_course(), "42")

    def test_dry_run_empty_selection_and_invalid_update_preserve_checkpoint(self) -> None:
        self.make_state().save()
        previous = self.path.read_bytes()
        cases = (
            (UpdateOptions(course="course", all_=True, dry_run=True), [Task().set_id(123)]),
            (UpdateOptions(course="course", all_=True, visible=0), []),
        )
        for options, tasks in cases:
            with self.subTest(dry_run=options.dry_run), \
                 patch("mula.structure_loader.StructureLoader.load"), \
                 patch.object(Update, "load_itens_from_structure", return_value=tasks), \
                 patch.object(Update, "print_dry_run"), \
                 patch.object(OperationState, "open_in_vscode") as editor, \
                 patch.object(PublishWorkflow, "execute") as execute:
                Update.update(options)
                editor.assert_not_called()
                execute.assert_not_called()
                self.assertEqual(self.path.read_bytes(), previous)
        with self.assertRaises(ValueError):
            Update.update(UpdateOptions(course="course", all_=True))
        self.assertEqual(self.path.read_bytes(), previous)

    def test_resume_restores_host_course_repository_actions_and_timeout(self) -> None:
        state = self.make_state(info=True, repo=str(self.directory), drafts="py", threads=3)
        state.save()
        self.credentials.course_alias["course"] = 999
        with patch("mula.structure_loader.StructureLoader.load") as load, \
             patch.object(OperationState, "open_in_vscode") as editor, \
             patch.object(PublishWorkflow, "execute") as execute:
            PublishWorkflow.resume()
            restored = execute.call_args.args[0]
            self.assertEqual(restored.options, state.options)
            self.assertIs(execute.call_args.args[1], load.return_value)
            editor.assert_called_once()
        self.assertEqual(self.credentials.url, state.moodle_url)
        self.assertEqual(self.credentials.get_course(), "42")
        self.assertEqual(self.credentials.repo_path, str(self.directory))
        self.assertEqual(MoodleAPI.default_timeout, 27)

    def test_completed_resume_does_not_authenticate_write_or_open_editor(self) -> None:
        self.make_state((Task.DONE, Task.SKIP)).save()
        previous = self.path.read_bytes()
        with patch.object(self.credentials, "fill_empty") as auth, \
             patch("mula.structure_loader.StructureLoader.load") as load, \
             patch.object(OperationState, "open_in_vscode") as editor, \
             patch.object(PublishWorkflow, "execute") as execute:
            PublishWorkflow.resume()
            auth.assert_not_called()
            load.assert_not_called()
            editor.assert_not_called()
            execute.assert_not_called()
        self.assertEqual(self.path.read_bytes(), previous)

    def test_unavailable_repository_fails_before_authentication(self) -> None:
        self.make_state(info=True, repo=str(self.directory / "missing")).save()
        previous = self.path.read_bytes()
        with patch.object(self.credentials, "fill_empty") as auth, \
             patch("mula.structure_loader.StructureLoader.load") as load:
            with self.assertRaisesRegex(ValueError, "repository is unavailable"):
                PublishWorkflow.resume()
            auth.assert_not_called()
            load.assert_not_called()
        self.assertEqual(self.path.read_bytes(), previous)

    def test_workers_retry_pending_tasks_and_save_after_each_task(self) -> None:
        state = self.make_state((Task.TODO, Task.FAIL, Task.DONE, Task.SKIP), threads=4)
        state.save()

        def publisher(task):
            result = Mock()
            result.set_section.return_value = result
            result.set_structure.return_value = result
            result.execute.side_effect = lambda: task.set_status(Task.DONE)
            return result

        with patch("mula.workflow.Publish", side_effect=publisher) as publish, \
             patch("mula.workflow.os.makedirs"), patch.object(Task, "set_log"), \
             patch.object(state, "save", wraps=state.save) as save:
            PublishWorkflow.execute(state, Mock())
            self.assertCountEqual([call.args[0].id for call in publish.call_args_list], [123, 124])
            self.assertEqual(save.call_count, 3)
        self.assertEqual([task.status for task in OperationState.load().tasks], [Task.DONE] * 3 + [Task.SKIP])

    def test_worker_failure_is_saved_and_propagated(self) -> None:
        state = self.make_state()
        state.save()
        with patch("mula.workflow.Publish") as publish:
            publish.return_value.set_section.return_value = publish.return_value
            publish.return_value.set_structure.return_value.execute.side_effect = RuntimeError("failed")
            with self.assertRaisesRegex(RuntimeError, "failed"):
                PublishWorkflow.execute(state, Mock())
        self.assertEqual(OperationState.load().tasks[0].status, Task.FAIL)

    def test_resume_executes_saved_pending_tasks_even_when_editor_is_missing(self) -> None:
        self.make_state((Task.TODO, Task.FAIL, Task.DONE, Task.SKIP)).save()

        def publisher(task):
            result = Mock()
            result.set_section.return_value = result
            result.set_structure.return_value = result
            result.execute.side_effect = lambda: task.set_status(Task.DONE)
            return result

        with patch("mula.structure_loader.StructureLoader.load"), \
             patch("mula.operation_state.subprocess.run", side_effect=FileNotFoundError()), \
             patch("mula.workflow.Publish", side_effect=publisher) as publish:
            PublishWorkflow.resume()
            self.assertEqual(publish.call_count, 2)
        restored = OperationState.load()
        self.assertEqual([task.status for task in restored.tasks], [Task.DONE] * 3 + [Task.SKIP])
        self.assertEqual(restored.options.visible, 0)
        self.assertEqual(restored.options.duedate, "0")
        self.assertEqual(restored.timeout, 27)

    def test_editor_launch_and_failures_do_not_block_execution(self) -> None:
        state = self.make_state()
        state.save()
        with patch("mula.operation_state.subprocess.run") as run:
            state.open_in_vscode()
            run.assert_called_once_with(
                ["code", "--reuse-window", str(self.path)], check=True, capture_output=True, timeout=5,
            )
        for error in (FileNotFoundError(), subprocess.CalledProcessError(1, "code"), subprocess.TimeoutExpired("code", 5)):
            with self.subTest(error=error), patch("mula.operation_state.subprocess.run", side_effect=error), \
                 patch("builtins.print") as output:
                state.open_in_vscode()
                self.assertIn("could not open VS Code", output.call_args.args[0])
