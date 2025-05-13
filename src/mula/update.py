from .add import Add
from .structure import Structure
from .moodle_api import MoodleAPI
from .log import Log
from .param import TaskParameters
from .structure_item import StructureItem
from .add_action import AddAction

class Update:

    @staticmethod
    def load_itens(args_all: bool, args_section: list[int], args_ids: list[int], args_labels: list[str], structure: Structure):
        item_list: list[StructureItem] = []
        if args_all:
            item_list = structure.get_itens()
        elif args_section and len(args_section) > 0:
            for section in args_section:
                item_list += structure.get_itens(section)
        elif args_ids:
            for qid in args_ids:
                if structure.has_id(qid):
                    item_list.append(structure.get_item(qid))
                else:
                    print("    - id not found: ", qid)
        if args_labels:
            for label in args_labels:
                item_list += [item for item in structure.get_itens() if item.label == label]
        return item_list

    @staticmethod
    def from_remote(item_list: list[StructureItem], param: TaskParameters, structure: Structure):
        for item in item_list:
            print("- Updating: " + str(item))
            if item.label == "":
                print("    - Skipping: No label found")
                continue
            add = Add(param, structure)
            
            action = AddAction()
            action.set_idx(item.id)
            action.set_section(item.section)
            action.set_label(item.label)
            action.set_title(item.title)
            add.execute(action)

    @staticmethod
    def exec_opt(item_list: list[StructureItem], args_exec_options: bool):
        i = 0
        api = MoodleAPI()
        log = Log()
        while i < len(item_list):
            item = item_list[i]
            log.print("- Change execution options for " + str(item.id))
            log.print("    -", str(item))
            try:
                log.open()
                if args_exec_options:
                    api.set_execution_options(item.id)

                i += 1
                log.done()
            except Exception as _e:
                api = MoodleAPI()
                print(type(_e))  # debug
                print(_e)
                log.fail(": timeout")
