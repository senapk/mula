class CommonParam:
    def __init__(self):
        self.local = False
        self.duedate: str | None = None
        self.maxfiles: int | None = None
        self.visible: bool | None = None
        self.exec: bool | None = None
        self.info: bool | None = None
