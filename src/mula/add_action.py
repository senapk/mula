class AddAction:
    TODO = "TODO" # tentar fazer
    SKIP = "SKIP" # ignorar, provavelmente não achou label
    FAIL = "FAIL" # tentou fazer, mas falhou
    DONE = "DONE" # fez com sucesso

    def __init__(self):
        self.status: str = ""
        self.idx: int = 0
        self.section: int = 0
        self.drafts: str | None = None
        self.label: str = ""
        self.title: str = ""

    def __str__(self):
        return f"status:{self.status}, section:{self.section}, label:{self.label}, title:{self.title}, index:{self.idx}"

    def set_status(self, status: str):
        if status not in [AddAction.TODO, AddAction.SKIP, AddAction.FAIL, AddAction.DONE]:
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
    
    def set_idx(self, idx: int):
        if idx < 0:
            raise Exception("Invalid index")
        self.idx = idx
        return self

    def serialize(self):
        return f"status:{self.status}, drafts:{self.drafts}, section:{self.section}, label:{self.label}"

    def rebuild(self, serial: str):
        serial = serial.replace("{", "").replace("}", "")
        parts = serial.split(",")
        parts = [x.strip() for x in parts]
        for part in parts:
            key, value = part.split(":")
            if key == "status":
                self.status = value
            elif key == "section":
                self.section = int(value)
            elif key == "label":
                self.label = value
            elif key == "index":
                self.idx = int(value)
            elif key == "title":
                self.title = value
            elif key == "drafts":
                self.drafts = value
            else:
                raise Exception("Unknown key in serialized string")
