import os
from typing import Optional
import json
import getpass

class Credentials:
    instance = None

    database_url = ["https://raw.githubusercontent.com/qxcode", "/arcade/master/base"]
    moodle_url = "https://moodle2.quixada.ufc.br"

    def __init__(self):
        self.url = Credentials.moodle_url
        self.username = None
        self.password = None
        self.index: Optional[str] = None
        self.remote_db = None
        self.remote_url = None

    def fill_empty(self):
        if self.username is None:
            print("Digite seu usuário do moodle: ", end="")
            self.username = input()

        if self.password is None:
            print("Digite sua senha do moodle:", flush=True)
            self.password = getpass.getpass()

        if self.index is None:
            print("Digite o número do curso:", end="")
            self.index = input()

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
            self.index = config["index"]

    def set_remote(self, remote: str):
        if remote == "fup" or remote == "poo" or remote == "ed":
            self.remote_db = remote
            self.remote_url = Credentials.database_url[0] + remote + Credentials.database_url[1]
        else:
            print("Remote database not found")
            exit(1)

    @staticmethod
    def load_credentials():
        if Credentials.instance is not None:
            return Credentials.instance
        Credentials.instance = Credentials()
        return Credentials.instance

    def __str__(self) -> str:
        return "{}:{}:{}:{}".format(self.username, self.password, self.url, self.index)
