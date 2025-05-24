from typing import List, Optional
import json
import os
import tempfile
from .credentials import Credentials
from .html import convert_markdown_to_html
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
        markdown = data.get("description", "")
        tempdir = tempfile.mkdtemp()

        self.log.print("    - Loading html description in " + tempdir + " ... ")
        md_file = os.path.join(tempdir, "description.md")
        html_file = os.path.join(tempdir, "description.html")
        with open(md_file, "w") as f:
            f.write(markdown)
        convert_markdown_to_html(md_file, html_file)
        html_description = ""
        with open(html_file, "r") as f:
            html_description = f.read()

        vpl = JsonVPL(data["title"], html_description)
        
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

    def load_local(self, target: str, base_folder: str) -> tuple[JsonVPL, str]:
        path = os.path.join(base_folder, target, ".cache", "mapi.json")
        self.log.print("    - Loading from local in "    + path + " ... ", end = "")
        if os.path.exists(path):
            with open(path, "r") as file:
                self.log.print("done")
                return self.load_from_string(file.read()), ""
        self.log.print("fail")
        return JsonVPL(), "File not found: " + path