from .add import Add
from .structure import Structure
from .moodle_api import MoodleAPI
from .bar import Bar
from .param import CommonParam

class Update:

    @staticmethod
    def load_itens(args_all, args_section, args_ids, args_labels, structure):
        item_list = []
        if args_all:
            item_list = structure.get_itens()
        elif args_section is not None and len(args_section) > 0:
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
    def from_remote(item_list, param: CommonParam, structure):
        for item in item_list:
            print("- Updating: " + str(item))
            if item.label == "":
                print("    - Skipping: No label found")
                continue
            action = Add(item.section, param, structure=structure)
            action.add_target(item.label)

    @staticmethod
    def exec_opt(item_list, args_exec_options):
        i = 0
        api = MoodleAPI()
        while i < len(item_list):
            item = item_list[i]
            print("- Change execution options for " + str(item.id))
            print("    -", str(item))
            try:
                Bar.open()
                if args_exec_options:
                    api.set_execution_options(item.id)

                i += 1
                Bar.done()
            except Exception as _e:
                api = MoodleAPI()
                print(type(_e))  # debug
                print(_e)
                Bar.fail(": timeout")

