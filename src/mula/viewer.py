from .url_handler import URLHandler
from .structure_loader import StructureLoader


# formatting structure to list
class Viewer:
    def __init__(self, show_url: bool, topic_only: bool):
        self.url_handler = URLHandler()
        self.structure = StructureLoader.load()
        self.show_url = show_url
        self.topic_only = topic_only

    def list_section(self, index: int):
        print("- %02d. %s" % (index, self.structure.section_labels[index]))
        if self.topic_only:
            return
        for item in self.structure.get_itens(section=index):
            if self.show_url:
                url = self.url_handler.view_vpl(item.id)
                print('    - %d: [%s](%s)' % (item.id, item.title, url))
            else:
                print('    - %d: %s' % (item.id, item.title))

    def list_all(self):
        for i in range(self.structure.get_number_of_sections()):
            self.list_section(i)
