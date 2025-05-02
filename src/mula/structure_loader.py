from typing import List
from .structure import Structure
from .moodle_api import MoodleAPI
from .bar import Bar
from .url_handler import URLHandler
from .structure_item import StructureItem


class StructureLoader:
    @staticmethod
    def load() -> Structure:
        api = MoodleAPI()
        print("- Loading course structure")
        Bar.open()
        Bar.send("load")
        while True:
            try:
                api.open_url(api.urlHandler.course())
                break
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                Bar.send("!", 0)
                api = MoodleAPI()

        Bar.send("parse")
        soup = api.browser.page  # BeautifulSoup(api.browser.response().read(), 'html.parser')
        topics = soup.find('ul', {'class:', 'topics'})
        if topics is None:
            print("\nfail: course not found")
            exit()
        section_item_list = StructureLoader._make_entries_by_section(soup, topics.contents)
        section_labels: List[str] = StructureLoader._make_section_labels(topics.contents)
        Bar.done()
        print(soup.title.string)
        return Structure(section_item_list, section_labels)

    @staticmethod
    def _make_section_labels(childrens) -> List[str]:
        return [section['aria-label'] for section in childrens]

    @staticmethod
    def _make_entries_by_section(soup, childrens) -> List[List[StructureItem]]:
        output: List[List[StructureItem]] = []
        for section_index, section in enumerate(childrens):
            comp = ' > div.content > ul > li > div > div.mod-indent-outer > div > div.activityinstance > a'
            activities = soup.select('#' + section['id'] + comp)
            section_entries: List[StructureItem] = []
            for activity in activities:
                if not URLHandler.is_vpl_url(activity['href']):
                    continue
                qid: int = int(URLHandler.parse_id(activity['href']))
                title: str = activity.get_text().replace(' Laboratório Virtual de Programação', '')
                section_entries.append(StructureItem(section_index, qid, title))
            output.append(section_entries)
        return output
