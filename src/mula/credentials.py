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
        self.__course_id: Optional[str] = None # moodle course id
        self.remote_alias: str | None = None # fup | ed | poo
        self.folder_db: str | None = None
        self.__remote_db: str | None = None
        self.course_alias: dict[str, int] = {} # course alias

    def fill_empty(self) -> bool:
        if self.username is not None and self.password is not None:
            return False
        self.force_read()
        return True

    def get_course(self) -> str:
        if self.__course_id is None:
            print("Course not set")
            print("Use --course <course id>")
            print("or --alias <alias>")
            raise ValueError("Course not set")
        return self.__course_id

    def set_course(self, course: str):
        if course in self.course_alias:
            alias = course
            course = str(self.course_alias[course])
            print("Using course alias: " + str(alias) + " -> " + course)
        self.__course_id = course

    def force_read(self):
        if self.username is None:
            print("Digite seu usuário do moodle: ", end="")
            self.username = input()

        if self.password is None:
            print("Digite sua senha do moodle:", flush=True)
            self.password = getpass.getpass()

    def load_file(self):
        settings_file = self.get_settings_file()
        try:
            with open(settings_file) as f:
                config = json.load(f)
            if "username" in config:
                self.username = config["username"]
            if "password" in config:
                self.password = config["password"]
            if "course_alias" in config:
                self.course_alias = config["course_alias"]
            return self
        except (FileNotFoundError, json.JSONDecodeError) as _:
            print("Error loading credentials file.")
        return self

    def set_alias(self, course: int, alias: str):
        # verify if alias is only letters and underline
        valid = "abcdefghijklmnopqrstuvwxyz_"
        for c in alias:
            if c not in valid:
                print("Alias must be only non capital letters and underline")
                return
        self.course_alias[alias] = course

    def get_settings_file(self) -> str:
        settings_file = os.path.join(appdirs.user_data_dir(Credentials.package_name), Credentials.credentials_file)
        return settings_file

    def save_file(self):
        settings_file = self.get_settings_file()
        data_to_save: dict[str, Optional[str | dict[str, int]]] = {
            "username": self.username,
            "password": self.password,
            "course_alias": self.course_alias,
        }
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        with open(settings_file, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        print(f"Credentials saved to {settings_file}")

    # def load_file(self, path: str):
    #     config = {}
    #     try:
    #         if not os.path.isfile(path):
    #             raise FileNotFoundError
    #         with open(path) as f:
    #             config = json.load(f)
    #     except (FileNotFoundError, json.JSONDecodeError) as e:
    #         print("Create a file with your access credentials: " + path)
    #         print(e)
    #         exit(1)
    #     if "username" in config:
    #         self.username = config["username"]
    #     if "password" in config:
    #         self.password = config["password"]
    #     if "course_alias" in config:
    #         self.course_alias = config["course_alias"]

    def set_remote(self, remote: str | None):
        if remote is None:
            return
        if remote == "fup" or remote == "poo" or remote == "ed":
            self.remote_alias = remote
            self.__remote_db = Credentials.database_url[0] + remote + Credentials.database_url[1]
        elif remote.startswith(Credentials.database_init) and remote.endswith(Credentials.database_end):
            self.remote_alias = "user"
            self.__remote_db = remote
        else:
            print("Remote database not found")
            print("Personal remote databases must start with " + Credentials.database_init + " and end with " + Credentials.database_end)
            exit(1)

    def get_remote(self) -> str | None:
        if self.__remote_db is None:
            print("Remote database not set")
            print("Use --remote <fup | ed | poo>")
            print("or --remote <url>")
            raise ValueError("Remote database not set")
        return self.__remote_db

    @staticmethod
    def load_credentials():
        if Credentials.instance is not None:
            return Credentials.instance
        Credentials.instance = Credentials()
        return Credentials.instance

    def __str__(self) -> str:
        return "{}:{}:{}:{}".format(self.username, self.password, self.url, self.folder_db)
