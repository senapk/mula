from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from mula.json_tools import JsonVplLoader
from mula.task import Task


class JsonVplLoaderTest(TestCase):
    def test_load_local_reads_current_moodle_artifacts_and_selected_language(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            task = repo / "labs" / "carro"
            cache = task / ".cache"
            starter = cache / "starter" / "py"
            starter.mkdir(parents=True)
            (task / "README.md").write_text("# Carro\n", encoding="utf-8")
            (cache / "README.html").write_text("<h1>Carro</h1>\n", encoding="utf-8")
            (cache / "tests.vpl").write_text("case=one\n", encoding="utf-8")
            (starter / "main.py").write_text("print(1)\n", encoding="utf-8")
            (cache / "starter" / "java").mkdir()

            with patch.object(JsonVplLoader, "_build_artifacts") as build:
                vpl, error = JsonVplLoader().load_local("labs/carro", str(repo), "py")

            self.assertEqual(error, "")
            build.assert_called_once_with(repo, task, check=True)
            self.assertEqual(vpl.title, "@labs/carro Carro")
            self.assertEqual(vpl.description, "<h1>Carro</h1>\n")
            self.assertEqual(vpl.upload[0].name, "vpl_evaluate.cases")
            self.assertEqual(vpl.upload[0].contents, "case=one\n")
            self.assertEqual([file.name for file in vpl.drafts["py"]], ["main.py"])
            self.assertNotIn("java", vpl.drafts)

    def test_load_local_builds_missing_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            task = repo / "labs" / "carro"
            task.mkdir(parents=True)
            (task / "README.md").write_text("# Carro\n", encoding="utf-8")
            calls: list[tuple[Path, Path, bool]] = []

            def fake_build(repo_path: Path, task_path: Path, check: bool = True) -> None:
                calls.append((repo_path, task_path, check))
                cache = task_path / ".cache"
                (cache / "starter" / "py").mkdir(parents=True)
                (cache / "README.html").write_text("<h1>Carro</h1>\n", encoding="utf-8")
                (cache / "tests.vpl").write_text("", encoding="utf-8")
                (cache / "starter" / "py" / "main.py").write_text("pass\n", encoding="utf-8")

            with patch.object(JsonVplLoader, "_build_artifacts", side_effect=fake_build):
                vpl, error = JsonVplLoader().load_local("labs/carro", str(repo), "py")

            self.assertEqual(error, "")
            self.assertEqual(calls, [(repo, task, True)])
            self.assertEqual(vpl.drafts["py"][0].contents, "pass\n")

    def test_build_artifacts_uses_current_tko_command_and_check(self) -> None:
        repo = Path("/tmp/course")
        task = repo / "labs" / "carro"

        with patch("mula.json_tools.subprocess.run") as run:
            JsonVplLoader._build_artifacts(repo, task)

        run.assert_called_once_with(
            ["tko", "build", "task", "labs/carro", "--moodle", "--check"],
            cwd=repo,
            check=True,
        )

    def test_missing_selected_starter_forces_full_build(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            task = repo / "labs" / "carro"
            cache = task / ".cache"
            task.mkdir(parents=True)
            (task / "README.md").write_text("# Carro\n", encoding="utf-8")
            (cache / "README.html").parent.mkdir(parents=True)
            (cache / "README.html").write_text("<h1>Carro</h1>\n", encoding="utf-8")
            (cache / "tests.vpl").write_text("", encoding="utf-8")
            (cache / "starter").mkdir()
            calls: list[bool] = []

            def fake_build(repo_path: Path, task_path: Path, check: bool = True) -> None:
                calls.append(check)
                starter = task_path / ".cache" / "starter" / "py"
                starter.mkdir(parents=True)
                (starter / "main.py").write_text("pass\n", encoding="utf-8")

            with patch.object(JsonVplLoader, "_build_artifacts", side_effect=fake_build):
                _, error = JsonVplLoader().load_local("labs/carro", str(repo), "py")

            self.assertEqual(error, "")
            self.assertEqual(calls, [False])

    def test_task_label_preserves_relative_path_key(self) -> None:
        task = Task().set_title("@labs/carro Carro")

        task.set_label_from_title()

        self.assertEqual(task.label, "labs/carro")
