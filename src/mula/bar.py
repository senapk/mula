# to print loading bar
class Bar:
    @staticmethod
    def open():
        print("    - [ ", end='', flush=True)

    @staticmethod
    def send(text: str, fill: int = 0):
        print(text.center(fill, '.') + " ", end='', flush=True)

    @staticmethod
    def done(text: str = ""):
        print("] DONE" + text)

    @staticmethod
    def fail(text: str = ""):
        print("] FAIL" + text)
