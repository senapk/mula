from mula.credentials import Credentials
from mula.log import Log
from mula.publish import Publish
from mula.structure import Structure
from mula.structure_loader import StructureLoader
from mula.task import Task, TaskParameters


import argparse
import os
import threading
from concurrent.futures import ThreadPoolExecutor


class Add:
    @staticmethod
    def validate_args(args: argparse.Namespace):
        if (args.remote is None and args.folder is None) or (args.remote is not None and args.folder is not None):
            print("you must set remote database OR local folder")
            print("use --remote fup | ed | poo")
            print("or  --folder <local base folder>")
            return False

        if args.course is None:
            print("course index not defined")
            print("use --course <course id>")
            return False

        if args.follow is not None:
            if not os.path.exists(args.follow):
                print("Persistence file not found")
                return False
            if len(args.targets) != 0:
                print("Persistence file and targets are mutually exclusive")
                return False
        return True

    @staticmethod
    def load_tasks_from_follow(follow: str, param: TaskParameters):
        task_list: list[Task] = []
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
    def load_from_args(args: argparse.Namespace, param: TaskParameters):
        task_list: list[Task] = []
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
                task.set_section(section)
            task.set_drafts(args.drafts)
            task.set_param(param)
            task.set_status(Task.TODO)
            task_list.append(task)
        return task_list

    @staticmethod
    def add(args: argparse.Namespace):
        if not Add.validate_args(args):
            return

        credentials = Credentials.load_credentials()
        credentials.set_remote(args.remote)
        credentials.folder_db = args.folder
        credentials.set_course(args.course)

        param = TaskParameters()
        param.duedate = "0" if args.duedate is None else args.duedate
        param.maxfiles = 5 if args.maxfiles is None else int(args.maxfiles)
        param.info = True
        param.exec = True
        if args.visible is not None:
            param.visible = True if args.visible == 1 else False

        task_list: list[Task] = []
        if args.follow is not None:
            task_list = Add.load_tasks_from_follow(args.follow, param)
        else:
            task_list = Add.load_from_args(args, param)

        follow: str | None = args.follow
        # se mandou criar -> cria e para
        # ou mandou rodar sem follow -> cria default e continua
        if args.create is not None or follow is None:
            if follow is None:
                create: str = "follow.csv"
                if args.create is not None:
                    create = args.create
                follow = create
            else:
                create = args.follow

            open(create, "w").write("\n".join([x.serialize() for x in task_list]))
            if not args.create:
                print("Default persistence file created: " + create)
            else:
                print("Persistence file created: " + args.create)
                print("You can use --follow", args.create)
                return

        n_threads: int = 1 if args.threads is None else args.threads
        Add.execute(n_threads, task_list, follow)

    @staticmethod
    def execute(n_threads: int, action_list: list[Task], follow: str | None):
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
            add = Publish(task).set_section(section).set_structure(structure)
            add.execute()
            print("- Finish " + str(task.label))
            if follow is not None:
                with lock:
                    with open(follow, "w") as f:
                        f.write("\n".join([x.serialize() for x in action_list]) + "\n")

        with ThreadPoolExecutor(max_workers=n_threads) as executor:
            executor.map(worker, action_list)