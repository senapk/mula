from pathlib import Path
from typing import List, Optional
import json
import os
import tempfile
import re
import subprocess
from .credentials import Credentials
import requests
from .log import Log


# Format used to send additional files to VPL
class JsonFile:
    def __init__(self, name: str = "", contents: str = ""):
        self.name: str = name
        self.contents: str = contents
        self.encoding: int = 0

    def __str__(self):
        return self.name + ":" + self.contents + ":" + str(self.encoding)


class JsonVPL:
    test_cases_file_name = "vpl_evaluate.cases"

    def __init__(self, title: str = "", description: str = "", tests: Optional[str] = None):
        self.title: str = title
        self.description: str = description
        self.upload: List[JsonFile] = []
        self.required: List[JsonFile] = []
        self.keep: List[JsonFile] = []
        self.drafts: dict[str, list[JsonFile]] = {}
        
        if tests is not None:
            self.set_test_cases(tests)

    def set_test_cases(self, tests: str):
        file = next((file for file in self.upload if file.name == JsonVPL.test_cases_file_name), None)
        if file is not None:
            file.contents = tests
            return
        self.upload.append(JsonFile("vpl_evaluate.cases", tests))

    def to_json(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    def __str__(self):
        return self.to_json()


class JsonVplLoader:
    def __init__(self, log: Log | None = None):
        if log is None:
            self.log = Log(None)
        else:
            self.log = log

    def load_from_string(self, text: str) -> JsonVPL:
        data = json.loads(text)
        vpl = JsonVPL(data.get("title", ""), data.get("description", ""))
        for f in data.get("upload", []):
            vpl.upload.append(JsonFile(f["name"], f["contents"]))
        for f in data.get("keep", []):
            vpl.keep.append(JsonFile(f["name"], f["contents"]))
        for f in data.get("required", []):
            vpl.required.append(JsonFile(f["name"], f["contents"]))
        for k, v in data.get("draft", {}).items():
            for file in v:
                vpl.drafts.setdefault(k, []).append(JsonFile(file["name"], file["contents"]))
        return vpl

    def save_as(self, file_url: str, filename: str) -> bool:
        headers = {'User-Agent': 'Mozilla/5.0'}  # Evita bloqueios comuns
        try:
            r = requests.get(file_url, headers=headers, timeout=10)
            r.raise_for_status()  # Levanta erro para códigos HTTP como 404, 403 etc.
            with open(filename, 'wb') as f:
                f.write(r.content)
            return True
        except requests.RequestException as _:
            return False

    # remote is like https://raw.githubusercontent.com/qxcodefup/moodle/master/base/
    def load_remote(self, target: str) -> tuple[JsonVPL, str]:
        remote_url: str | None = Credentials.load_credentials().get_remote()
        if remote_url is None:
            return JsonVPL(), "Remote URL not set"
        url: str = remote_url + "/" + target + "/.cache/mapi.json"
        self.log.print("    - " + url)
        _, path = tempfile.mkstemp(suffix = "_" + target + '.json')
        self.log.print("    - Loading in " + path + " ... ")
        if self.save_as(url, path):
            return self.load_from_string(open(path).read()), ""
        return JsonVPL(), "Error downloading " + target

    @staticmethod
    def _task_path(target: str) -> Path:
        normalized: str = target.strip().replace("\\", "/")
        if normalized.startswith("@"):
            normalized = normalized[1:]
        path: Path = Path(normalized)
        if not normalized or path.is_absolute() or ".." in path.parts:
            raise ValueError("Task path must be relative to the repository root")
        return path

    @staticmethod
    def _title_from_readme(readme: Path) -> str:
        heading_pattern: re.Pattern[str] = re.compile(r"^#\s+(.+?)\s*$")
        for line in readme.read_text(encoding="utf-8").splitlines():
            match: re.Match[str] | None = heading_pattern.match(line)
            if match is not None:
                return match.group(1)
        return readme.parent.name

    @staticmethod
    def _moodle_title(task_path: Path, title: str) -> str:
        key: str = task_path.as_posix()
        prefix: str = f"@{key}"
        if title == prefix or title.startswith(prefix + " "):
            return title
        return f"{prefix} {title}".strip()

    @staticmethod
    def _draft_files(draft_folder: Path) -> list[JsonFile]:
        if not draft_folder.is_dir():
            return []
        files: list[JsonFile] = []
        for path in sorted((item for item in draft_folder.rglob("*") if item.is_file()), key=lambda item: item.as_posix()):
            if path.suffix in {".hide", ".exec"}:
                continue
            name: str = path.relative_to(draft_folder).as_posix()
            files.append(JsonFile(name, path.read_text(encoding="utf-8")))
        return files

    @staticmethod
    def _build_artifacts(repo: Path, task_path: Path, check: bool = True) -> None:
        relative_task: str = task_path.relative_to(repo).as_posix()
        arguments: list[str] = ["tko", "build", "task", relative_task, "--moodle"]
        if check:
            arguments.append("--check")
        subprocess.run(
            arguments,
            cwd=repo,
            check=True,
        )

    def load_local(
        self,
        target: str,
        base_folder: str,
        draft_language: str | None = None,
    ) -> tuple[JsonVPL, str]:
        try:
            relative_task: Path = self._task_path(target)
            repo: Path = Path(base_folder).resolve()
            task_folder: Path = (repo / relative_task).resolve()
            task_folder.relative_to(repo)
            if not task_folder.is_dir():
                return JsonVPL(), f"Task folder not found: {task_folder}"

            cache: Path = task_folder / ".cache"
            html_path: Path = cache / "README.html"
            cases_path: Path = cache / "tests.vpl"
            starter_path: Path | None = (
                cache / "starter" / draft_language if draft_language else None
            )
            missing_selected_starter: bool = (
                starter_path is not None and not starter_path.is_dir()
            )
            self.log.print("    - Checking Moodle artifacts ...")
            self._build_artifacts(
                repo, task_folder, check=not missing_selected_starter
            )

            if not html_path.is_file() or not cases_path.is_file():
                return JsonVPL(), f"Moodle artifacts not found in {cache}"

            title: str = self._moodle_title(
                relative_task,
                self._title_from_readme(task_folder / "README.md"),
            )
            description: str = html_path.read_text(encoding="utf-8")
            tests: str = cases_path.read_text(encoding="utf-8")
            vpl: JsonVPL = JsonVPL(title, description, tests)
            if draft_language is not None and starter_path is not None:
                vpl.drafts[draft_language] = self._draft_files(starter_path)
            self.log.print("    - Loading Moodle artifacts from " + str(cache) + " ... done")
            return vpl, ""
        except (OSError, subprocess.CalledProcessError, ValueError) as error:
            return JsonVPL(), f"Error loading TKO task {target}: {error}"
