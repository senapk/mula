from .add import Add
from .structure_loader import StructureLoader
from .update import Update
from .moodle_api import MoodleAPI
from .bar import Bar
from .viewer import Viewer
from .param import CommonParam

from typing import Optional

import os


class Actions:

    @staticmethod
    def add(args):
        param = CommonParam()
        param.duedate = "0" if args.duedate is None else args.duedate
        param.maxfiles = 3 if args.maxfiles is None else int(args.maxfiles)
        param.content = True
        param.exec = True

        if args.visible is not None:
            param.visible = True if args.visible == 1 else False
      
        for target in args.targets:
            label = target
            section = args.section
            if args.section is None:
                section = 0
                label = target
                if ":" in target:
                    section, label = target.split(":")
            action = Add(int(section), param)
            action.add_target(label)

    @staticmethod
    def update(args):
        param = CommonParam()
        param.duedate = args.duedate
        param.maxfiles = args.maxfiles
        param.content= args.content
        param.exec = args.exec

        if args.visible is not None:
            param.visible = True if args.visible == 1 else False

        structure = StructureLoader.load()
        item_list = Update.load_itens(args.all, args.sections, args.ids, args.labels, structure)

        if len(item_list) == 0:
            print("No item found / selected")
            return

        Update.from_remote(item_list, param, structure)

    @staticmethod
    def down(args):
        args_output: str = args.output

        api = MoodleAPI()
        structure = StructureLoader.load()
        item_list = Update.load_itens(args.all, args.sections, args.ids, args.labels, structure)

        i = 0
        while i < len(item_list):
            item = item_list[i]
            path = os.path.normpath(os.path.join(args_output, str(item.id) + ".json"))
            print("- Saving id " + str(item.id))
            print("    -", str(item))
            try:
                Bar.open()
                data = api.download(item.id)
                open(path, "w").write(str(data))
                i += 1
                Bar.done(": " + path)
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                Bar.fail(": timeout")

    @staticmethod
    def rm(args):
        structure = StructureLoader.load()
        item_list = Update.load_itens(args.all, args.sections, args.ids, args.labels, structure)

        i = 0
        while i < len(item_list):
            api = MoodleAPI()
            item = item_list[i]
            print("- Removing id " + str(item.id))
            print("    -", str(item))
            try:
                Bar.open()
                api.delete(item.id)
                i += 1
                Bar.done()
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                Bar.fail(": timeout")

    @staticmethod
    def list(args):
        args_section: Optional[int] = args.section
        args_url: bool = args.url
        args_topic_only: bool = args.topic
        viewer = Viewer(args_url, args_topic_only)
        if args_section is not None:
            viewer.list_section(args_section)
        else:
            viewer.list_all()

