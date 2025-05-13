from mula.task import Task
from .add import Add
from .structure_loader import StructureLoader
from .update import Update
from .moodle_api import MoodleAPI
from .log import Log
from .viewer import Viewer
from .credentials import Credentials
from .url_handler import URLHandler
from .task import TaskParameters
from .structure import Structure
from concurrent.futures import ThreadPoolExecutor
import threading
import json
import argparse
from typing import Optional

import os

class Actions:

    @staticmethod
    def auth(_: argparse.Namespace):
        credentials = Credentials.load_credentials()
        credentials.username = None
        credentials.password = None
        credentials.force_read()
        credentials.save_file()

    @staticmethod
    def alias(args: argparse.Namespace):
        credentials = Credentials.load_credentials()
        credentials.set_alias(args.course, args.alias)
        credentials.save_file()


    @staticmethod
    def courses(_: argparse.Namespace):
        moodle = MoodleAPI()
        urls = URLHandler()
        moodle.open_url(urls.base())
        # Obtém o conteúdo HTML da página
        browser = moodle.browser
        html = browser.get_current_page() # type: ignore

        # Encontra todos os cards de cursos (ajuste o seletor conforme necessário)
        course_cards = html.select('div.card[data-courseid]') # type: ignore

        # Extrai informações dos cursos
        courses: list[dict[str, str]] = []
        for card in course_cards: # type: ignore
            course_id = card['data-courseid'] # type: ignore
            link = card.find('a')['href'] # type: ignore
            title = card.find('h4', class_='card-title').text.strip() # type: ignore
            courses.append({
                'id': course_id,
                'title': title,
                'link': link
            })

        title_pad = max([len(c['title']) for c in courses])

        # Exibe os cursos encontrados
        for course in courses:
            print(f"Course ID: {course['id'].ljust(4)} - {course['title'].ljust(title_pad)} - Link: {course['link']}")

        # Fecha o navegador
        browser.close()

        credentials = Credentials.load_credentials()
        print("\nCurrent courses alias setted: ")
        for alias, course in credentials.course_alias.items():
            print(f"  {alias} -> {course}")
        if len(credentials.course_alias) == 0:
            print("  No aliases set")


        
    @staticmethod
    def check_and_set_for_add_update(args: argparse.Namespace, param: TaskParameters) -> bool:
        if args.course is None:
            print("course index not defined")
            print("use --course <course id>")
            return False

        credentials = Credentials.load_credentials()
        credentials.set_remote(args.remote)
        credentials.folder_db = args.folder
        credentials.set_course(args.course)

        param.duedate = "0" if args.duedate is None else args.duedate
        param.maxfiles = 3 if args.maxfiles is None else int(args.maxfiles)
        param.info = True
        param.exec = True

        if args.visible is not None:
            param.visible = True if args.visible == 1 else False

        return True

    @staticmethod
    def add(args: argparse.Namespace):
        param = TaskParameters()
        
        if (args.remote is None and args.folder is None) or (args.remote is not None and args.folder is not None):
            print("you must set remote database OR local folder")
            print("use --remote fup | ed | poo")
            print("or  --folder <local base folder>")
            return
        
        if not Actions.check_and_set_for_add_update(args, param):
            return
        
        if args.follow is not None:
            if not os.path.exists(args.follow):
                print("Persistence file not found")
                return
            if len(args.targets) != 0:
                print("Persistence file and targets are mutually exclusive")
                return
            
        action_list: list[Task] = []
        if args.follow is not None:
            try:
                lines = open(args.follow).read().splitlines()
                for line in lines:
                    task = Task()
                    task.rebuild(line)
                    task.set_param(param)
                    action_list.append(task)
            except Exception as e:
                print("Error reading persistence file", args.follow)
                print(e)
                return
        else:
            for target in args.targets:
                task = Task()
                section: int = 0
                if args.section is not None:
                    section = args.section
                if ":" in target:
                    section, label = target.split(":")
                    task.set_section(int(section))
                    task.set_label(label)
                else:
                    task.set_label(target)
                    if args.section is not None:
                        task.set_section(args.section)
                task.set_drafts(args.drafts)
                task.set_param(param)
                task.set_status(Task.TODO)
                action_list.append(task)
            
        if args.create is not None:
            open(args.create, "w").write("\n".join([x.serialize() for x in action_list]))
            print("Persistence file created: " + args.create)
            print("You can use --follow", args.create)
            return


        n_threads: int = 1 if args.threads is None else args.threads
        print("Threads: " + str(n_threads))

        structure: Structure = StructureLoader.load(None)
        
        lock = threading.Lock()
        def worker(task: Task):
            if task.status == Task.DONE or task.status == Task.SKIP:
                return
            section = int(task.section)
            if n_threads == 1:
                print("- Start " + str(task.label))
                print("    -", str(task))
            else:
                log_file: str = os.path.join(".log", task.label)
                if not os.path.exists(".log"):
                    os.mkdir(".log")
                task.set_log(Log(log_file))
                print("- Start " + str(task.label) + " with log file: " + log_file)
            add = Add(task).set_section(section).set_structure(structure)
            add.execute()
            print("- Finish " + str(task.label))
            if args.follow is not None:
                with lock:
                    with open(args.follow, "w") as f:
                        f.write("\n".join([x.serialize() for x in action_list]) + "\n")

        with ThreadPoolExecutor(max_workers=n_threads) as executor:
            executor.map(worker, action_list)


    @staticmethod
    def update(args: argparse.Namespace):
        param = TaskParameters()
        if args.info:
            if (args.remote is None and args.folder is None) or (args.remote is not None and args.folder is not None):
                print("--info requires a source")
                print("you must set remote database OR local folder")
                print("use --remote fup | ed | poo")
                print("or  --folder <local base folder>")
                return

        if not Actions.check_and_set_for_add_update(args, param):
            return
        
        if all([x is None for x in [args.drafts, args.duedate, args.maxfiles, args.info, args.exec, args.visible]]):
            print("Nothing to update, please provide at least one action(--info, --duedate, --visible, ...")
            return
                
        if args.drafts is not None and args.info is None:
            print("Drafts only available with --info")
            return

        structure: Structure = StructureLoader.load()

        if args.follow is None:
            item_list: list[Task] = Update.load_itens(args.all, args.section, args.id, args.label, structure)
        else:
            if not os.path.exists(args.follow):
                print("Persistence file not found")
                return
            try:
                lines = open(args.follow).read().splitlines()
                item_list = []
                for line in lines:
                    task = Task()
                    task.rebuild(line)
                    item_list.append(task)
            except Exception as e:
                print("Error reading persistence file", args.follow)
                print(e)
                return
        if len(item_list) == 0:
            print("No item found / selected")
            return
        
        if args.create is not None:
            tasks: list[Task] = []
            for item in item_list:
                task = Task()
                task.set_label(item.label)
                task.set_id(item.id)
                task.set_section(item.section)
                task.set_drafts(args.drafts)
                task.set_param(param)
                task.set_status(Task.TODO)
                task.set_title(item.title)
                tasks.append(task)
            open(args.create, "w").write("\n".join([x.serialize() for x in tasks]))
            print("Persistence file created: " + args.create)
            print("You can use --follow", args.create)
            return

        for task in item_list:
            print("- Updating: " + str(task))
            if task.label == "":
                print("    - Skipping: No label found")
                continue
            add = Add(task).set_structure(structure)
            add.execute()
            with open(args.follow, "w") as f:
                f.write("\n".join([x.serialize() for x in item_list]) + "\n")
        
        # lock = threading.Lock()

        # def worker(task: Task):
        #     if task.status == Task.DONE or task.status == Task.SKIP:
        #         return
        #     section = int(task.section)
        #     if n_threads == 1:
        #         print("- Start " + str(task.label))
        #         print("    -", str(task))
        #     else:
        #         log_file: str = os.path.join(".log", task.label)
        #         if not os.path.exists(".log"):
        #             os.mkdir(".log")
        #         task.set_log(Log(log_file))
        #         print("- Start " + str(task.label) + " with log file: " + log_file)
        #     add = Add(task).set_section(section).set_structure(structure)
        #     add.execute()
        #     print("- Finish " + str(task.label))
        #     if args.follow is not None:
        #         with lock:
        #             with open(args.follow, "w") as f:
        #                 f.write("\n".join([x.serialize() for x in action_list]) + "\n")

        # with ThreadPoolExecutor(max_workers=n_threads) as executor:
        #     executor.map(worker, action_list)

    @staticmethod
    def unpack_json(json_file: str):
        try:
            data = json.loads(open(json_file).read())
             
            folder: str = json_file[:-5] + "_" + data["title"].replace(" ", "_").lower().replace("[", "-").replace("]", "-").replace("(", "_").replace(")", "_")
            if os.path.exists(folder):
                os.remove(folder)
            os.mkdir(folder)
            description = data["description"]
            description_file = os.path.join(folder, "description.txt")
            open(description_file, "w").write(description)
            
            for f in data["upload"]:
                file_name: str = os.path.join(folder, f["name"])
                open(file_name, "w").write(f["contents"])
            for f in data["keep"]:
                file_name: str = os.path.join(folder, f["name"])
                open(file_name, "w").write(f["contents"])
            for f in data["required"]:
                file_name: str = os.path.join(folder, f["name"])
                open(file_name, "w").write(f["contents"])
            yaml_file: str = os.path.join(folder, "config.yaml")
            with open(yaml_file, "w") as y:
                y.write("upload:\n")
                for f in data["upload"]:
                    y.write("  - " + f'"{f["name"]}"\n')
                y.write("keep:\n")
                for f in data["keep"]:
                    y.write("  - " + f'"{f["name"]}"\n')
                y.write("required:\n")
                for f in data["required"]:
                    y.write("  - " + f'"{f["name"]}"\n')
                
        
        except Exception as e:
            print("Error unpacking json file", json_file)
            print(e)
            return

    @staticmethod
    def down(args: argparse.Namespace):
        if args.course is None:
            print("course index not defined")
            print("use --course <course id>")
            return
        else:
            credentials = Credentials.load_credentials()
            credentials.set_course(args.course)

        args_output: str = args.output

        api = MoodleAPI()
        structure = StructureLoader.load()
        item_list = Update.load_itens(args.all, args.section, args.id, args.label, structure)
        log = Log(None)
        i = 0
        while i < len(item_list):
            item = item_list[i]
            path = os.path.normpath(os.path.join(args_output, str(item.id) + ".json"))
            log.print("- Saving id " + str(item.id))
            log.print("    -", str(item))
            try:
                log.open()
                data = api.download(item.id)
                open(path, "w").write(str(data))
                Actions.unpack_json(path)
                i += 1
                log.done(": " + path)
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                log.fail(": timeout")

    @staticmethod
    def rm(args: argparse.Namespace):
        if args.course is None:
            print("course index not defined")
            print("use --course <course id>")
            return
        else:
            credentials = Credentials.load_credentials()
            credentials.set_course(args.course)

        structure = StructureLoader.load()
        item_list = Update.load_itens(args.all, args.section, args.id, args.label, structure)

        log = Log(None)
        i = 0
        while i < len(item_list):
            api = MoodleAPI()
            item = item_list[i]
            log.print("- Removing id " + str(item.id))
            log.print("    -" + str(item))
            try:
                log.open()
                api.delete(item.id)
                i += 1
                log.done()
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                log.fail(": timeout")

    @staticmethod
    def list(args: argparse.Namespace):
        if args.course is None:
            print("course index not defined")
            print("use --course <course id>")
            return
        else:
            credentials = Credentials.load_credentials()
            credentials.set_course(args.course)


        args_section: Optional[int] = args.section
        args_url: bool = args.url
        args_topic_only: bool = args.topic
        viewer = Viewer(args_url, args_topic_only)
        if args_section is not None:
            viewer.list_section(args_section)
        else:
            viewer.list_all()
