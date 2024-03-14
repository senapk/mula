from typing import List, Optional
import json
import urllib.request
import urllib.error
import os
import tempfile
from .credentials import Credentials



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
        return vpl

    @staticmethod
    def save_as(file_url, filename) -> bool:
        try:
            urllib.request.urlretrieve(file_url, filename)
        except urllib.error.HTTPError:
            return False
        return True

    # remote is like https://raw.githubusercontent.com/qxcodefup/moodle/master/base/
    @staticmethod
    def load(target: str) -> JsonVPL:

        remote_url = Credentials.load_credentials().remote
        url = os.path.join(remote_url, target + "/.cache/mapi.json")            
        _fd, path = tempfile.mkstemp(suffix = "_" + target + '.json')
        print("    - Loading from remote in"    + path + " ... ", end = "")
        if JsonVplLoader.save_as(url, path):
            print("done")
            return JsonVplLoader._load_from_string(open(path).read())
        print("fail: invalid target " + target)
        exit(1)

