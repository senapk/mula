class StructureItem:
    def __init__(self, section: int, qid: int, title: str):
        self.section: int = section
        self.id: int = qid
        self.title: str = title
        self.label: str = StructureItem.parse_label(title)

    def __str__(self):
        return "section={}, id={}, label={}, title={}".format(self.section, self.id, self.label, self.title)

    # "@123 ABCDE..." -> 123
    # "" se não tiver label
    @staticmethod
    def parse_label(title) -> str:
        ttl_splt = title.strip().split(" ")
        for ttl in ttl_splt:
            if len(ttl) > 0 and ttl[0] == '@':
                return ttl[1:]
        return ""
