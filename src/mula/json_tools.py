from typing import List, Optional
import json
import urllib.request
import urllib.error
import os
import tempfile
from .credentials import Credentials
import requests


# Format used to send additional files to VPL
class JsonFile:
    def __init__(self, name: str, contents: str):
        self.name: str = name
        self.contents: str = contents
        self.encoding: int = 0

    def __str__(self):
        return self.name + ":" + self.contents + ":" + str(self.encoding)


class JsonVPL:
    test_cases_file_name = "vpl_evaluate.cases"

    def __init__(self, title: str, description: str, tests: Optional[str] = None):
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
    @staticmethod
    def _load_from_string(text: str) -> JsonVPL:
        data = json.loads(text)
        vpl = JsonVPL(data["title"], data["description"])
        for f in data["upload"]:
            vpl.upload.append(JsonFile(f["name"], f["contents"]))
        for f in data["keep"]:
            vpl.keep.append(JsonFile(f["name"], f["contents"]))
        for f in data["required"]:
            vpl.required.append(JsonFile(f["name"], f["contents"]))
        for k, v in data["draft"].items():
            for file in v:
                vpl.drafts.setdefault(k, []).append(JsonFile(file["name"], file["contents"]))
        return vpl

    @staticmethod
    def save_as(file_url: str, filename: str) -> bool:
        headers = {'User-Agent': 'Mozilla/5.0'}  # Evita bloqueios comuns
        try:
            r = requests.get(file_url, headers=headers, timeout=10)
            r.raise_for_status()  # Levanta erro para códigos HTTP como 404, 403 etc.
            with open(filename, 'wb') as f:
                f.write(r.content)
            return True
        except requests.RequestException as e:
            print(f"Error downloading file: {e}")
            return False

    # remote is like https://raw.githubusercontent.com/qxcodefup/moodle/master/base/
    @staticmethod
    def load_remote(target: str) -> JsonVPL:

        remote_url: str | None = Credentials.load_credentials().get_remote()
        if remote_url is None:
            print("Error: remote url not set")
            exit(1)
        url: str = remote_url + "/" + target + "/.cache/mapi.json"
        print("    - " + url)
        _fd, path = tempfile.mkstemp(suffix = "_" + target + '.json')
        print("    - Loading in "    + path + " ... ", end = "")
        if JsonVplLoader.save_as(url, path):
            print("done")
            return JsonVplLoader._load_from_string(open(path).read())
        print("fail: invalid target " + target)
        exit(1)

    @staticmethod
    def load_local(target: str, base_folder: str) -> JsonVPL:

        path = os.path.join(base_folder, target, ".cache", "mapi.json")
        print("    - Loading from local in "    + path + " ... ", end = "")
        if os.path.exists(path):
            with open(path, "r") as file:
                print("done")
                return JsonVplLoader._load_from_string(file.read())
        else:
            print("fail: invalid target " + target)
            exit(1)
