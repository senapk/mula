from typing import Optional
from .structure_loader import StructureLoader
from .moodle_api import MoodleAPI
from .log import Log
from .json_tools import JsonVplLoader, JsonVPL
from .structure_item import StructureItem
from .param import TaskParameters
from .structure import Structure
from .credentials import Credentials
from .add_action import AddAction


class Add:
    def __init__(self, param: TaskParameters):
        self.section: int = 0
        self.param: TaskParameters = param
        self.credentials: Credentials = Credentials.load_credentials()
        self.log: Log = Log(None)
        self.structure: Structure | None = None
        self.api = MoodleAPI()

    def set_structure(self, structure: Structure):
        self.structure = structure
        return self

    def set_section(self, section: int):
        self.section = section
        return self

    def set_log(self, log: Log):
        self.log = log
        return self

    def send_basic(self, api: MoodleAPI, vpl: JsonVPL, url: str) -> int:
        self.log.send("info")
        qid = api.send_basic_info(url, vpl, self.param)
        return qid

    def set_keep(self, api: MoodleAPI, qid: int, keep_size: int):
        if not self.param.info:
            return
        self.log.send("keep")
        api.set_keep(qid, keep_size)
 

    def update_extra(self, api: MoodleAPI, vpl: JsonVPL, qid: int, drafts: str | None):
        if self.param.exec:
            self.log.send("exec")
            api.set_execution_options(qid)

        if drafts:
            self.log.send("drafts")
            vpl.required = vpl.drafts[drafts]
            api.send_files(vpl, qid)

    def apply_action(self, vpl: JsonVPL, item: Optional[StructureItem], action: AddAction):
        api: MoodleAPI = self.api
        if self.structure is None:
            self.log.print("error: structure not set")
            return

        if item is not None:
            self.log.print("    - Updating: Label found in " + str(item.id) + ": " + item.title)
            url = api.urlHandler.update_vpl(item.id)
            self.log.open()
            self.send_basic(api, vpl, url)
            self.update_extra(api, vpl, item.id, action.drafts)
            self.set_keep(api, item.id, len(vpl.keep))
            self.log.done()
        else:  # new
            self.log.print("    - Creating: New entry with title: " + vpl.title)
            self.log.open()
            url = api.urlHandler.new_vpl(self.section)
            qid = self.send_basic(api, vpl, url)
            self.log.send(str(qid))
            self.update_extra(api, vpl, qid, action.drafts)
            self.set_keep(api, qid, len(vpl.keep))
            self.structure.add_entry(self.section, qid, vpl.title)
            self.log.done()

    def execute(self, action: AddAction):
        self.log.print(f"    - target: {action.section} {action.label}")
        loader: JsonVplLoader = JsonVplLoader(self.log)
        if self.credentials.folder_db is not None:
            vpl, err = loader.load_local(action.label, self.credentials.folder_db)
        else:
            vpl, err = loader.load_remote(action.label)
        if err:
            action.set_status(AddAction.FAIL)
            self.log.print("error:" + err)
            return
        if self.structure is None:
            self.log.print("error: structure not set")
            action.set_status(AddAction.FAIL)
            return
        label_to_search = StructureItem.parse_label(vpl.title)
        itens_label_match: list[StructureItem] = self.structure.search_by_label(label_to_search, self.section)
        if len(itens_label_match) == 0:
            self.log.print("    - No match found")
        for item in itens_label_match:
            print("    - Found: " + str(item.id) + ": " + item.title)
        item = None if len(itens_label_match) == 0 else itens_label_match[0]    

        try:
            self.apply_action(vpl, item, action)
            action.set_status(AddAction.DONE)
        except Exception as e:
            action.set_status(AddAction.FAIL)
            self.log.print("error:" + str(e))
        return