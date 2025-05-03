import os
from typing import Optional
import json
import getpass
import appdirs

class Credentials:
    instance = None

    package_name = "mula"
    credentials_file = "credentials.json"

    database_init = "https://raw.githubusercontent.com/"
    database_end = "base"
    database_url = ["https://raw.githubusercontent.com/qxcode", "/arcade/master/base"]
    moodle_url = "https://moodle2.quixada.ufc.br"

    def __init__(self):
        self.url = Credentials.moodle_url
        self.username: str | None = None
        self.password: str | None = None
        self.course_id: Optional[str] = None # moodle course id
        self.remote_alias: str | None = None # fup | ed | poo
        self.folder_db: str | None = None
        self.remote_db: str | None = None

    def fill_from_auth(self) -> bool:
        if self.username is None and self.password is None:
            self.try_load_auth()
            if self.username is not None and self.password is not None:
                return True
        return False


    def fill_empty(self):
        if self.fill_from_auth():
            return
        self.force_read()

    def force_read(self):
        if self.username is None:
            print("Digite seu usuário do moodle: ", end="")
            self.username = input()

        if self.password is None:
            print("Digite sua senha do moodle:", flush=True)
            self.password = getpass.getpass()

    def try_load_auth(self):
        settings_file = os.path.join(appdirs.user_data_dir(Credentials.package_name), Credentials.credentials_file)
        try:
            with open(settings_file) as f:
                config = json.load(f)
            if "username" in config:
                self.username = config["username"]
            if "password" in config:
                self.password = config["password"]
        except (FileNotFoundError, json.JSONDecodeError) as e:
            pass

    def save_auth(self):

        settings_file = os.path.join(appdirs.user_data_dir(Credentials.package_name), Credentials.credentials_file)
        data_to_save = {
            "username": self.username,
            "password": self.password,
        }
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        with open(settings_file, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        print(f"Credentials saved to {settings_file}")

    def load_file(self, path: str):
        config = {}
        try:
            if not os.path.isfile(path):
                raise FileNotFoundError
            with open(path) as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print("Create a file with your access credentials: " + path)
            print(e)
            exit(1)
        if "username" in config:
            self.username = config["username"]
        if "password" in config:
            self.password = config["password"]
        if "index" in config:
            self.course_id = config["index"]

    def set_remote(self, remote: str | None):
        if remote is None:
            return
        if remote == "fup" or remote == "poo" or remote == "ed":
            self.remote_alias = remote
            self.remote_db = Credentials.database_url[0] + remote + Credentials.database_url[1]
        elif remote.startswith(Credentials.database_init) and remote.endswith(Credentials.database_end):
            self.remote_alias = "user"
            self.remote_db = remote
        else:
            print("Remote database not found")
            print("Personal remote databases must start with " + Credentials.database_init + " and end with " + Credentials.database_end)
            exit(1)

    @staticmethod
    def load_credentials():
        if Credentials.instance is not None:
            return Credentials.instance
        Credentials.instance = Credentials()
        return Credentials.instance

    def __str__(self) -> str:
        return "{}:{}:{}:{}".format(self.username, self.password, self.url, self.course_id)
