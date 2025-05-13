from mula.task import Task
from .publish import Publish
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
        item_list = Update.load_itens_from_structure(args.all, args.section, args.id, args.label, structure)
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
        item_list: list[Task] = Update.load_itens_from_structure(args.all, args.section, args.id, args.label, structure)

        log = Log(None)
        i = 0
        while i < len(item_list):
            api = MoodleAPI().set_task(item_list[i])
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
