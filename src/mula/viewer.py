from .url_handler import URLHandler
from .structure_loader import StructureLoader
from .text import Text

# formatting structure to list
class Viewer:
    def __init__(self, show_url: bool, topic_only: bool):
        self.url_handler = URLHandler()
        self.structure = StructureLoader.load()
        self.show_url = show_url
        self.topic_only = topic_only

    def list_section(self, index: int, connection: bool = False):
        section_title = self.structure.section_labels[index]
        prefix = "├─" if connection else "└─"
        print(Text.format('{*}',f"{prefix} {index:02d}. {section_title}"))
        
        itens = self.structure.get_itens(section=index)
        if self.topic_only or not itens:
            return
        
        last_id = itens[-1].id
        for item in itens:
            is_last = item.id == last_id
            prefix = "├─" if not is_last else "└─"
            if connection:
                prefix = Text.format("{*}","│") + Text.format('{m}',f"    {prefix}{item.id:05d}─ ")
            else:
                prefix = Text.format('{m}',f"     {prefix}{item.id:05d}─ ")
            
            if self.show_url:
                url = self.url_handler.view_vpl(item.id)
                print(prefix + f"[{item.title}]({url})")
            else:
                print(prefix + f"{item.title}")

    def list_all(self):
        last_section_number = self.structure.get_number_of_sections() - 1
        for i in range(self.structure.get_number_of_sections()):
            if i == last_section_number:
                self.list_section(i)
                return                
            self.list_section(i, connection=True)
