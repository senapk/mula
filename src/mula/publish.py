from .moodle_api import MoodleAPI
from .json_tools import JsonVplLoader, JsonVPL
from .structure import Structure
from .credentials import Credentials
from .task import Task


class Publish:
    def __init__(self, task: Task):
        self.section: int = 0
        self.credentials: Credentials = Credentials.load_credentials()
        self.structure: Structure | None = None
        self.api = MoodleAPI().set_task(task)
        self.task = task

    def set_structure(self, structure: Structure):
        self.structure = structure
        return self

    def set_section(self, section: int):
        self.section = section
        return self

    def send_basic(self, api: MoodleAPI, vpl: JsonVPL, url: str,) -> int:
        self.task.log.send("info")
        qid = api.send_basic_info(url, vpl)
        return qid

    def set_keep(self, api: MoodleAPI, qid: int, keep_size: int):
        if not self.task.param.info:
            return
        self.task.log.send("keep")
        api.set_keep(qid, keep_size)
 

    def update_extra(self, api: MoodleAPI, vpl: JsonVPL, qid: int):
        if self.task.param.exec:
            self.task.log.send("exec")
            api.set_execution_options(qid)

        if self.task.drafts:
            self.task.log.send("drafts")
            vpl.required = vpl.drafts[self.task.drafts]
            api.send_files(vpl, qid)

    def apply_action(self, vpl: JsonVPL):
        api: MoodleAPI = self.api
        task: Task = self.task
        if self.structure is None:
            task.log.print("    - Error: structure not set")
            return

        if task.id != 0:
            task.log.print("    - Updating: Label found in " + str(task.id) + ": " + task.title)
            url = api.urlHandler.update_vpl(task.id)
            task.log.open()
            self.send_basic(api, vpl, url)
            self.update_extra(api, vpl, task.id)
            self.set_keep(api, task.id, len(vpl.keep))
            task.log.done()
        else:  # new
            task.log.print("    - Creating: New entry with title: " + vpl.title)
            task.log.open()
            url = api.urlHandler.new_vpl(self.section)
            qid = self.send_basic(api, vpl, url)
            task.log.send(str(qid))
            self.update_extra(api, vpl, qid)
            self.set_keep(api, qid, len(vpl.keep))
            self.structure.add_entry(self.section, qid, vpl.title)
            task.log.done()

    def execute(self):
        task: Task = self.task
        task.log.print(f"    - target: {task.section} {task.label}")
        loader: JsonVplLoader = JsonVplLoader(task.log)
        if self.credentials.folder_db is not None:
            vpl, err = loader.load_local(task.label, self.credentials.folder_db)
        else:
            vpl, err = loader.load_remote(task.label)
        if err:
            task.set_status(Task.FAIL)
            task.log.print("    - Error:" + err)
            return
        if self.structure is None:
            task.log.print("    - Error: structure not set")
            task.set_status(Task.FAIL)
            return
        
        # se o id é 0, é operação de ADD, deve veriricar se existe alguém nessa seção com esse label e fazer o update
        if task.id == 0:
            label_to_search = task.label
            print("    - Searching for label: " + label_to_search)
            itens_label_match: list[Task] = self.structure.search_by_label(label_to_search, self.section)
            if len(itens_label_match) == 0:
                task.log.print("    - No match found")
            for item in itens_label_match:
                print("    - Found: " + str(item.id) + ": " + item.title)
            item = None if len(itens_label_match) == 0 else itens_label_match[0]    
            self.task.id = item.id if item is not None else 0
        else:
            task.log.print("    - Updating: " + str(task.id) + ": " + task.title + ": using label " + task.label)
        try:
            self.apply_action(vpl)
            task.set_status(Task.DONE)
        except Exception as e:
            task.set_status(Task.FAIL)
            task.log.print("    - Error:" + str(e))
        return