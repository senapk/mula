from typing import Optional

class CommonParam:
    def __init__(self):
        self.duedate: Optional[str]= None
        self.maxfiles: Optional[int] = None
        self.visible: Optional[bool] = None
        self.exec: bool = None
        self.content: bool = None