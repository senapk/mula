# to print loading bar
from .text import Text
class Log:

    def __init__(self, destiny: None | str  = None):
        self.destiny: None | str = destiny

    def print(self, text: str | Text, end: str = "\n"):
        if self.destiny is None:
            if isinstance(text, Text):
                text = str(text)
            print(text, end=end)
            return
        with open(self.destiny, 'a') as f:
            if isinstance(text, Text):
                text = text.get_str()
            f.write(text)
            f.write(end)

    def open(self):
        if self.destiny is None:
            print("    - [ ", end='', flush=True)
            return
        with open(self.destiny, 'a') as f:
            f.write("    - [ ")

    def send(self, text: str, fill: int = 0):
        if self.destiny is None:
            print(text.center(fill, '.') + " ", end='', flush=True)
            return
        with open(self.destiny, 'a') as f:
            f.write(text.center(fill, '.') + " ")

    def done(self, text: str = ""):
        if self.destiny is None:
            print(Text().addf("g", "] DONE" + text))
            return
        with open(self.destiny, 'a') as f:
            f.write("] DONE" + text)
            f.write("\n")

    def fail(self, text: str = ""):
        if self.destiny is None:
            print(Text().addf("r", "] FAIL" + text))
            return
        with open(self.destiny, 'a') as f:
            f.write("] FAIL" + text)
            f.write("\n")
