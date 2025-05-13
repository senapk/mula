from typing import List, Dict, Optional
from .structure_item import StructureItem


# save course structure: sections, ids, titles
class Structure:
    def __init__(self, section_item_list: List[List[StructureItem]], section_labels: List[str]):
        self.section_item_list: List[List[StructureItem]] = section_item_list
        self.section_labels: List[str] = section_labels
        # redundant info
        self.ids_dict: Dict[int, StructureItem] = self._make_ids_dict()

    def add_entry(self, section: int, qid: int, title: str):
        if qid not in self.ids_dict.keys():
            item = StructureItem(section, qid, title)
            self.section_item_list[section].append(item)
            self.ids_dict[qid] = item

    def search_by_label(self, label: str, section: Optional[int] = None) -> List[StructureItem]:
        if label == "" :
            return []
        if section is None:
            return [item for item in self.ids_dict.values() if item.label == label]
        if section < 0 or section >= len(self.section_item_list):
            return []
        return [item for item in self.section_item_list[section] if item.label == label]

    def get_id_list(self, section: Optional[int] = None) -> List[int]:
        if section is None:
            return list(self.ids_dict.keys())
        return [item.id for item in self.section_item_list[section]]

    def get_itens(self, section: Optional[int] = None) -> List[StructureItem]:
        if section is None:
            return list(self.ids_dict.values())
        return self.section_item_list[section]

    def get_item(self, qid: int) -> StructureItem:
        return self.ids_dict[qid]

    def has_id(self, qid: int, section: Optional[int] = None) -> bool:
        if section is None:
            return qid in self.ids_dict.keys()
        return qid in self.get_id_list(section)

    def rm_item(self, qid: int):
        if self.has_id(qid):
            item = self.ids_dict[qid]
            del self.ids_dict[qid]
            new_section_list = [item for item in self.section_item_list[item.section] if item.id != qid]
            self.section_item_list[item.section] = new_section_list

    def get_number_of_sections(self):
        return len(self.section_labels)

    def _make_ids_dict(self) -> Dict[int, StructureItem]:
        entries: Dict[int, StructureItem] = {}
        for item_list in self.section_item_list:
            for item in item_list:
                entries[item.id] = item
        return entries
