from typing import Optional
from .structure_loader import StructureLoader
from .moodle_api import MoodleAPI
from .bar import Bar
from .json_tools import JsonVplLoader, JsonVPL
from .structure_item import StructureItem
from .param import CommonParam
from .structure import Structure


class Add:
    def __init__(self, section: Optional[int], param: CommonParam, structure: Structure | None =None):
        self.section: int = 0 if section is None else section
        self.param = param
        if structure is None:
            self.structure = StructureLoader.load()
        else:
            self.structure = structure

    def send_basic(self, api: MoodleAPI, vpl: JsonVPL, url: str) -> int:
        while True:
            try:
                qid = api.send_basic_info(url, vpl, self.param)
                break
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                api = MoodleAPI()
                Bar.send("!", 0)
        return qid

    def set_keep(self, api: MoodleAPI, qid: int, keep_size: int):
        if not self.param.content:
            return
        Bar.send("keep")
        while True:
            try:

                api.set_keep(qid, keep_size)
                break
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                api = MoodleAPI()
                Bar.send("!", 0)

    def update_extra(self, api: MoodleAPI, vpl: JsonVPL, qid: int):
        if self.param.exec:
            Bar.send("exec")
            while True:
                try:
                    api.set_execution_options(qid)
                    break
                except Exception as _e:
                    print(type(_e))  # debug
                    print(_e)
                    api = MoodleAPI()
                    Bar.send("!", 0)

        if self.param.content:
            Bar.send("files")
            while True:
                try:
                    api.send_files(vpl, qid)
                    break
                except Exception as _e:
                    print(type(_e))  # debug
                    print(_e)
                    api = MoodleAPI()
                    Bar.send("!", 0)

    def apply_action(self, vpl: JsonVPL, item: Optional[StructureItem]):
        api = MoodleAPI()  # creating new browser for each attempt to avoid some weird timeout

        if item is not None:
            print("    - Updating: Label found in " + str(item.id) + ": " + item.title)
            url = api.urlHandler.update_vpl(item.id)
            Bar.open()
            self.send_basic(api, vpl, url)
            self.update_extra(api, vpl, item.id)
            self.set_keep(api, item.id, len(vpl.keep))
            Bar.done()
        else:  # new
            print("    - Creating: New entry with title: " + vpl.title)
            Bar.open()
            url = api.urlHandler.new_vpl(self.section)
            qid = self.send_basic(api, vpl, url)
            Bar.send(str(qid))
            self.update_extra(api, vpl, qid)
            self.set_keep(api, qid, len(vpl.keep))
            self.structure.add_entry(self.section, qid, vpl.title)
            Bar.done()

    def add_target(self, target: str):
        print("- Target: " + target)
        if self.param.local:
            vpl = JsonVplLoader.load_local(target)
        else:
            vpl = JsonVplLoader.load_remote(target)
        itens_label_match = self.structure.search_by_label(StructureItem.parse_label(vpl.title), self.section)
        item = None if len(itens_label_match) == 0 else itens_label_match[0]
        while True:
            try:
                self.apply_action(vpl, item)
                return
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                Bar.fail(":" + str(_e))