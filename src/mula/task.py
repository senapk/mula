from .log import Log
import os


class TaskParameters:
    def __init__(self):
        self.duedate: str | None = None
        self.maxfiles: int | None = None
        self.visible: bool | None = None
        self.exec: bool | None = None
        self.info: bool | None = None

class Task:
    TODO = "TODO" # tentar fazer
    SKIP = "SKIP" # ignorar, provavelmente não achou label
    FAIL = "FAIL" # tentou fazer, mas falhou
    DONE = "DONE" # fez com sucesso

    def __init__(self):
        self.status: str = ""
        self.id: int = 0
        self.section: int = 0
        self.drafts: str | None = None
        self.label: str = ""
        self.title: str = ""
        self.log: Log = Log()
        self.param: TaskParameters = TaskParameters()

    def __str__(self):
        return f"status:{self.status}, section:{self.section}, label:{self.label}, title:{self.title}, index:{self.id}"

    def set_log(self, log: Log):
        if log.destiny is not None and os.path.exists(log.destiny):
            with open(log.destiny, 'w') as f:
                f.write("")
        self.log = log
        return self

    def set_param(self, params: TaskParameters):
        self.param = params
        return self

    def set_status(self, status: str):
        if status not in [Task.TODO, Task.SKIP, Task.FAIL, Task.DONE]:
            raise Exception("Invalid status")
        self.status = status
        return self

    def set_drafts(self, drafts: str | None):
        self.drafts = drafts
        return self

    def set_section(self, section: int):
        if section < 0:
            raise Exception("Invalid section")
        self.section = section
        return self
    
    def set_label(self, label: str):
        if len(label) == 0:
            raise Exception("Invalid label")
        self.label = label
        return self
    
    def set_title(self, title: str):
        if len(title) == 0:
            raise Exception("Invalid title")
        self.title = title
        return self
    
    def set_id(self, id: int):
        if id < 0:
            raise Exception("Invalid index")
        self.id = id
        return self

    def serialize(self):
        return f"status:{self.status}, drafts:{"" if self.drafts is None else self.drafts}, section:{self.section}, index:{self.id}, label:{self.label}, title:{self.title}"

    # "@123 ABCDE..." -> 123
    # "" se não tiver label
    def set_label_from_title(self):
        title = self.title
        valid_chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_"
        ttl_splt = title.strip().split(" ")
        for ttl in ttl_splt:
            if len(ttl) > 0 and ttl[0] == '@':
                # Remove all invalid characters from the label
                label = "".join(c for c in ttl[1:] if c in valid_chars)
                self.label = label
        return self

    def rebuild(self, serial: str):
        serial = serial.replace("{", "").replace("}", "")
        parts = serial.split(",")
        parts = [x.strip() for x in parts]
        for part in parts:
            pieces = part.split(":")
            key = pieces[0].strip()
            if len(pieces) == 2:
                value = pieces[1].strip()
            else:
                # Join the rest of the pieces if there are more than 2
                # This is useful for keys with ":" in their values
                value = ":".join(pieces[1:]).strip()
            if key == "status":
                self.status = value
            elif key == "section":
                self.section = int(value)
            elif key == "label":
                self.label = value
            elif key == "index":
                self.id = int(value)
            elif key == "title":
                self.title = value
            elif key == "drafts":
                if value == "" or value == "None":
                    self.drafts = None
                else:
                    self.drafts = value
            else:
                raise Exception("Unknown key in serialized string")
