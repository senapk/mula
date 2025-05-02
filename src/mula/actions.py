from .add import Add
from .structure_loader import StructureLoader
from .update import Update
from .moodle_api import MoodleAPI
from .bar import Bar
from .viewer import Viewer
from .param import CommonParam
import argparse
from .credentials import Credentials
from .url_handler import URLHandler

import json
from typing import Optional

import os


class Actions:

    @staticmethod
    def auth(_args: argparse.Namespace):
        credentials = Credentials.load_credentials()
        credentials.fill_empty()
        credentials.save_auth()


    @staticmethod
    def courses(_args: argparse.Namespace):
        moodle = MoodleAPI()
        urls = URLHandler()
        moodle.open_url(urls.base())
        # Obtém o conteúdo HTML da página
        browser = moodle.browser
        html = browser.get_current_page()

        # Encontra todos os cards de cursos (ajuste o seletor conforme necessário)
        course_cards = html.select('div.card[data-courseid]')

        # Extrai informações dos cursos
        courses = []
        for card in course_cards:
            course_id = card['data-courseid']
            link = card.find('a')['href']
            title = card.find('h4', class_='card-title').text.strip()
            courses.append({
                'id': course_id,
                'title': title,
                'link': link
            })

        title_pad = max([len(c['title']) for c in courses])

        # Exibe os cursos encontrados
        for i, course in enumerate(courses, 1):
            print(f"Course ID: {course['id'].ljust(4)} - {course['title'].ljust(title_pad)} - Link: {course['link']}")

        # Fecha o navegador
        browser.close()

    @staticmethod
    def add(args: argparse.Namespace):
        if args.remote is None:
            print("remote database not defined")
            print("use --remote fup | ed | poo")
            return
        elif args.course is None:
            print("course index not defined")
            print("use --course <course id>")
            return
        else:
            credentials = Credentials.load_credentials()
            credentials.set_remote(args.remote)
            credentials.course = args.course
    
        param = CommonParam()
        param.duedate = "0" if args.duedate is None else args.duedate
        param.maxfiles = 3 if args.maxfiles is None else int(args.maxfiles)
        param.info = True
        param.exec = True
        param.drafts = args.drafts

        if args.local:
            param.local = True

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
    def update(args: argparse.Namespace):
        if args.remote is None:
            print("remote database not defined")
            print("use --remote fup | ed | poo")
            return
        elif args.course is None:
            print("course index not defined")
            print("use --course <course id>")
            return
        else:
            credentials = Credentials.load_credentials()
            credentials.set_remote(args.remote)
            credentials.course = args.course

        
        param = CommonParam()
        param.duedate = args.duedate
        param.maxfiles = args.maxfiles
        param.info = args.info
        param.exec = args.exec
        param.drafts = args.drafts

        if not args.duedate and not args.maxfiles and not args.info and not args.exec and not args.visible:
            print("Nothing to update, please provide at least one action(--content, --duedate, --visible, ...")
            return

        if args.local:
            param.local = True

        if args.visible is not None:
            param.visible = True if args.visible == 1 else False


        structure = StructureLoader.load()
        item_list = Update.load_itens(args.all, args.section, args.id, args.label, structure)

        if len(item_list) == 0:
            print("No item found / selected")
            return

        Update.from_remote(item_list, param, structure)

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
            credentials.course = args.course

        args_output: str = args.output

        api = MoodleAPI()
        structure = StructureLoader.load()
        item_list = Update.load_itens(args.all, args.section, args.id, args.label, structure)

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
                Actions.unpack_json(path)
                i += 1
                Bar.done(": " + path)
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                Bar.fail(": timeout")

    @staticmethod
    def rm(args: argparse.Namespace):
        if args.course is None:
            print("course index not defined")
            print("use --course <course id>")
            return
        else:
            credentials = Credentials.load_credentials()
            credentials.course = args.course

        structure = StructureLoader.load()
        item_list = Update.load_itens(args.all, args.section, args.id, args.label, structure)

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
    def list(args: argparse.Namespace):
        if args.course is None:
            print("course index not defined")
            print("use --course <course id>")
            return
        else:
            credentials = Credentials.load_credentials()
            credentials.course = args.course


        args_section: Optional[int] = args.section
        args_url: bool = args.url
        args_topic_only: bool = args.topic
        viewer = Viewer(args_url, args_topic_only)
        if args_section is not None:
            viewer.list_section(args_section)
        else:
            viewer.list_all()
