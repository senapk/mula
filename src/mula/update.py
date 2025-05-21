from .publish import Publish
from .structure import Structure
from .moodle_api import MoodleAPI
from .log import Log
from .task import Task, TaskParameters
from .credentials import Credentials
from .structure_loader import StructureLoader
import os
import threading
from concurrent.futures import ThreadPoolExecutor
import argparse
from .text import Text

class Update:

    @staticmethod
    def any_action(args: argparse.Namespace):
        if args.info:
            return True
        if args.drafts is not None:
            return True
        if args.duedate is not None:
            return True
        if args.maxfiles is not None:
            return True
        if args.visible is not None:
            return True
        if args.exec:
            return True
        return False

    @staticmethod
    def load_tasks_from_follow(follow: str, param: TaskParameters):        
        task_list: list[Task] = []
        if not os.path.exists(follow):
            print("Persistence file not found")
            return task_list
        try:
            lines = open(follow).read().splitlines()
            for line in lines:
                task = Task()
                task.rebuild(line)
                task.set_param(param)
                task_list.append(task)
        except Exception as e:
            print("Error reading persistence file", follow)
            print(e)
        return task_list

    @staticmethod
    def create_persistence_file(create: str, drafts: str | None, task_list: list[Task], param: TaskParameters):
        for task in task_list:
            task.set_drafts(drafts)
            task.set_param(param)
            task.set_status(Task.TODO)
        open(create, "w").write("\n".join([x.serialize() for x in task_list]))

    @staticmethod
    def execute(n_threads: int | None, task_list: list[Task], structure: Structure, follow: str | None):
        lock = threading.Lock()
        

        def worker(task: Task):
            if task.status == Task.DONE or task.status == Task.SKIP:
                
                return
            if n_threads == 1:
                print(Text.format("{y}", "- Start " + str(task.id) + ": " + str(task.label) + " - " + str(task.title)))
            else:
                log_file: str = os.path.join(".log", str(task.id))
                if not os.path.exists(".log"):
                    os.mkdir(".log")
                task.set_log(Log(log_file))
                print("- Start " + str(task.id) + ": " + str(task.label) + " - " + str(task.title) + " with log file: " + log_file)
            add = Publish(task).set_structure(structure)
            add.execute()

            print("- Finish " + str(task.label))
            if follow is not None:
                with lock:
                    with open(follow, "w") as f:
                        f.write("\n".join([x.serialize() for x in task_list]) + "\n")
        with ThreadPoolExecutor(max_workers=n_threads) as executor:
            executor.map(worker, task_list)

    @staticmethod
    def validate_args(args: argparse.Namespace):
        if args.info:
            if args.remote is None and args.folder is None:
                print("--info requires a source")
                print("you must set remote database OR local folder")
                print("use --remote fup | ed | poo")
                print("or  --folder <local base folder>")
                return False

        if args.course is None:
            print(Text().addf("y", "course index not defined"))
            print(Text().addf("y", "use --course <course id>"))
            return False
        
        if not Update.any_action(args):
            print(Text().addf("y", "Nothing to update, please provide at least one action(--info, --duedate, --visible, ..."))
            return False
                
        if args.drafts is not None and args.info is None:
            print(Text().addf("y", "Drafts only available with --info"))
            return False

        if args.follow is None:
            if not args.all and (args.section is None and args.id is None and args.label is None):
                print(Text().addf("y", "You must provide at least one target [--all | --section ... | --id ... | --label ...]"))
                return False
        
        
        return True

    @staticmethod
    def update(args: argparse.Namespace):
        if not Update.validate_args(args):
            return

        credentials = Credentials.load_credentials()
        credentials.set_remote(args.remote)
        credentials.folder_db = args.folder
        credentials.set_course(args.course)

        param = TaskParameters()
        param.duedate = args.duedate
        param.maxfiles = args.maxfiles
        param.info = args.info
        param.exec = args.exec

        if args.visible is not None:
            param.visible = True if args.visible == 1 else False

        structure: Structure = StructureLoader.load()

        task_list: list[Task] = []
        if args.follow is not None:
            task_list = Update.load_tasks_from_follow(args.follow, param)
        else:
            task_list = Update.load_itens_from_structure(args.all, args.section, args.id, args.label, structure)

        follow: str | None = args.follow
        # se mandou criar -> cria e para
        # ou mandou rodar sem follow -> cria default e continua
        if args.create is not None or args.follow is None:
            if follow is None:
                create: str = "follow.csv"
                if args.create is not None:
                    create = args.create
                follow = create
            else:
                create = args.follow
            Update.create_persistence_file(create, args.drafts, task_list, param)
            if not args.create:
                print("Default persistence file created: " + create)
                print("Use --follow if you want to resume")
            else:
                print("Persistence file created: " + create)
                print("Use --follow to continue")
                return
        n_threads: int = args.threads if args.threads is not None else 1

         #se vc fornecesse uam label inexistente ele nao falava nada, perdi mt tempo nisso =(
        if(len(task_list) == 0):
            raise RuntimeError(f"****No labels found. Please check the arguments****")
        
        Update.execute(n_threads, task_list, structure, follow)

    @staticmethod
    def load_itens_from_structure(args_all: bool, args_section: list[int], args_ids: list[int], args_labels: list[str], structure: Structure):
        item_list: list[Task] = []
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
            # print(item_list)
        return item_list

    @staticmethod
    def exec_opt(item_list: list[Task], args_exec_options: bool):
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
