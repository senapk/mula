from typing import List
from .structure import Structure
from .moodle_api import MoodleAPI
from .log import Log
from .url_handler import URLHandler
from .task import Task


class StructureLoader:
    @staticmethod
    def load(log: Log | None = None) -> Structure:
        if log is None:
            log = Log(None)
        api = MoodleAPI()
        log.print("- Loading course structure")
        log.open()
        log.send("load")
        api.open_url(api.urlHandler.course())
        # while True:

        #         break
        #     except Exception as _e:
        #         print(type(_e))  # debug
        #         print(_e)
        #         log.send("!", 0)
        #         api = MoodleAPI()

        log.send("parse")
        soup = api.browser.page  # BeautifulSoup(api.browser.response().read(), 'html.parser')
        topics = soup.find('ul', {'class:', 'topics'})
        if topics is None:
            print("\nfail: course not found")
            exit(1)
        section_item_list = StructureLoader._make_entries_by_section(soup, topics.contents)
        section_labels: List[str] = StructureLoader._make_section_labels(topics.contents)
        log.done()
        log.print(soup.title.string)
        return Structure(section_item_list, section_labels)

    @staticmethod
    def _make_section_labels(childrens) -> List[str]:
        return [section['aria-label'] for section in childrens]

    @staticmethod
    def _make_entries_by_section(soup, childrens) -> List[List[Task]]:
        output: List[List[Task]] = []
        for section_index, section in enumerate(childrens):
            comp = ' > div.content > ul > li > div > div.mod-indent-outer > div > div.activityinstance > a'
            activities = soup.select('#' + section['id'] + comp)
            section_entries: List[Task] = []
            for activity in activities:
                if not URLHandler.is_vpl_url(activity['href']):
                    continue
                qid: int = int(URLHandler.parse_id(activity['href']))
                title: str = activity.get_text().replace(' Laboratório Virtual de Programação', '')
                section_entries.append(Task().set_section(section_index).set_id(qid).set_title(title).set_label_from_title())
            output.append(section_entries)
        return output
