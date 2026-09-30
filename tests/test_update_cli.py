from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from mula.__main__ import app
from mula.update import UpdateOptions


class UpdateCliTest(TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()
        self.credentials = Mock()
        self.credentials.load_file.return_value = self.credentials
        credentials_patch = patch(
            "mula.credentials.Credentials.load_credentials", return_value=self.credentials,
        )
        credentials_patch.start()
        self.addCleanup(credentials_patch.stop)

    def invoke(self, *arguments: str):
        return self.runner.invoke(app, ["update", "-c", "course", *arguments])

    def test_help_groups_options_and_does_not_request_credentials(self) -> None:
        result = self.runner.invoke(app, ["update", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        for text in ("choose exactly one", "Changes", "Local content", "Execution", "--all"):
            self.assertIn(text, result.output)
        self.credentials.fill_empty.assert_not_called()

    def test_repeated_and_legacy_selectors_forward_the_same_typed_options(self) -> None:
        cases = (
            (["--id", "123", "--id", "456"], "ids", [123, 456]),
            (["-I", "123", "456"], "ids", [123, 456]),
            (["--section", "0", "--section", "2"], "sections", [0, 2]),
            (["-S", "0", "2"], "sections", [0, 2]),
            (["--label", "labs/a", "--label", "labs/b"], "labels", ["labs/a", "labs/b"]),
            (["-A"], "all_", True),
            (["-L", "labs/a", "labs/b"], "labels", ["labs/a", "labs/b"]),
        )
        for arguments, field, expected in cases:
            with self.subTest(arguments=arguments), patch("mula.cli_update.Update.update") as update:
                result = self.invoke(*arguments, "--visible", "0", "--duedate", "0", "--threads", "4")
                self.assertEqual(result.exit_code, 0, result.output)
                options = update.call_args.args[0]
                self.assertIsInstance(options, UpdateOptions)
                self.assertEqual(getattr(options, field), expected)
                self.assertEqual(options.visible, 0)
                self.assertEqual(options.duedate, "0")
                self.assertEqual(options.threads, 4)
                self.assertFalse(options.task_parameters().visible)

    def test_option_groups_reject_conflicts_before_authentication(self) -> None:
        for arguments in (["--all", "--id", "1"], ["--id", "1", "--section", "0"]):
            with self.subTest(arguments=arguments), patch("mula.cli_update.Update.update") as update:
                result = self.invoke(*arguments, "--visible", "0")
                self.assertEqual(result.exit_code, 2, result.output)
                self.assertIn("mutually", result.output)
                update.assert_not_called()
        self.credentials.fill_empty.assert_not_called()

    def test_removed_update_options_are_rejected(self) -> None:
        for arguments in (
            ["--create", "file"], ["--follow", "file"], ["--resume"],
            ["--ids", "123"], ["--sections", "0"], ["--drafts", "py"],
            ["-i"], ["-a"], ["-s", "0"], ["-d", "py"],
        ):
            with self.subTest(arguments=arguments), patch("mula.cli_update.Update.update") as update:
                result = self.invoke("--all", "--visible", "0", *arguments)
                self.assertEqual(result.exit_code, 2, result.output)
                update.assert_not_called()
        self.credentials.fill_empty.assert_not_called()

    def test_resume_has_no_execution_arguments_or_overrides(self) -> None:
        cases = (
            ["resume", "--course", "course"], ["resume", "--threads", "4"],
            ["resume", "--visible", "0"], ["resume", "--dry-run"],
            ["resume", "something"], ["--timeout", "30", "resume"],
        )
        for arguments in cases:
            with self.subTest(arguments=arguments), patch("mula.cli_update.PublishWorkflow.resume") as resume:
                result = self.runner.invoke(app, arguments)
                self.assertEqual(result.exit_code, 2, result.output)
                resume.assert_not_called()
        self.credentials.fill_empty.assert_not_called()

    def test_resume_dispatches_without_requesting_credentials_in_root(self) -> None:
        with patch("mula.cli_update.PublishWorkflow.resume") as resume:
            result = self.runner.invoke(app, ["resume"])
            self.assertEqual(result.exit_code, 0, result.output)
            resume.assert_called_once_with()
        self.credentials.fill_empty.assert_not_called()

    def test_resume_storage_errors_are_clear(self) -> None:
        with patch("mula.cli_update.PublishWorkflow.resume", side_effect=ValueError("No saved operation found")):
            result = self.runner.invoke(app, ["resume"])
            self.assertEqual(result.exit_code, 1, result.output)
            self.assertIn("No saved operation found", result.output)
        self.credentials.fill_empty.assert_not_called()

    def test_missing_options_and_dependencies_are_usage_errors(self) -> None:
        cases = (
            (["--visible", "0"], "choose one"),
            (["--all"], "at least one change"),
            (["--all", "--info"], "--info requires --repo"),
            (["--all", "--lang", "py"], "--lang requires --info"),
        )
        for arguments, message in cases:
            with self.subTest(arguments=arguments), patch("mula.cli_update.Update.update") as update:
                result = self.invoke(*arguments)
                self.assertEqual(result.exit_code, 2, result.output)
                self.assertIn(message, result.output)
                update.assert_not_called()
        self.credentials.fill_empty.assert_not_called()

    def test_invalid_values_are_rejected_before_execution(self) -> None:
        cases = (
            ["--all", "--duedate", "2026:02:30:12:00"],
            ["--all", "--duedate", "2026:1:1:25:00"],
            ["--all", "--duedate", "tomorrow"],
            ["--id", "0", "--visible", "0"],
            ["--id", "1", "0", "--visible", "0"],
            ["--section", "-1", "--visible", "0"],
            ["--all", "--maxfiles", "-1"],
            ["--all", "--visible", "2"],
            ["--all", "--visible", "0", "--threads", "0"],
            ["--all", "--visble", "0"],
        )
        for arguments in cases:
            with self.subTest(arguments=arguments), patch("mula.cli_update.Update.update") as update:
                result = self.invoke(*arguments)
                self.assertEqual(result.exit_code, 2, result.output)
                update.assert_not_called()
        self.credentials.fill_empty.assert_not_called()

    def test_dry_run_accepts_no_actions_or_repo(self) -> None:
        with patch("mula.cli_update.Update.update") as update:
            result = self.invoke("--all", "--info", "--dry-run")
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(update.call_args.args[0].dry_run)

    def test_content_options_reach_the_workflow(self) -> None:
        with TemporaryDirectory() as directory:
            with patch("mula.cli_update.Update.update") as update:
                result = self.invoke(
                    "--all", "--info", "-r", directory, "-l", "java",
                    "--duedate", "2026:10:15:23:59", "--maxfiles", "5", "--exec",
                )
                self.assertEqual(result.exit_code, 0, result.output)
                options = update.call_args.args[0]
                self.assertEqual(options.repo, directory)
                self.assertEqual(options.drafts, "java")
                self.assertEqual(options.duedate, "2026:10:15:23:59")
                self.assertEqual(options.maxfiles, 5)
                self.assertTrue(options.info)
                self.assertTrue(options.exec_)

    def test_invalid_source_paths_are_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            file = Path(directory) / "file"
            file.write_text("", encoding="utf-8")
            cases = (
                ["--all", "--info", "--repo", str(file)],
                ["--all", "--info", "--repo", str(Path(directory) / "missing")],
            )
            for arguments in cases:
                with self.subTest(arguments=arguments), patch("mula.cli_update.Update.update") as update:
                    result = self.invoke(*arguments)
                    self.assertEqual(result.exit_code, 2, result.output)
                    update.assert_not_called()
        self.credentials.fill_empty.assert_not_called()
