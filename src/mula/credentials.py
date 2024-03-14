import os
from typing import Optional
import pathlib
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
        self.database = None
        self.remote = None

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
        
        if self.database is None:
            print("Digite o nome do banco de dados remoto [fup | poo | ed]:", end="")
            self.database = input()

        self.remote = Credentials.database_url[0] + self.database + Credentials.database_url[1]


    def load_file(self, path):
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
        if "database" in config:
            self.database = config["database"]

    @staticmethod
    def load_credentials():
        if Credentials.instance is not None:
            return Credentials.instance
        Credentials.instance = Credentials()
        return Credentials.instance

    def __str__(self):
        return self.username + ":" + self.password + ":" + self.url + ":" + self.index
