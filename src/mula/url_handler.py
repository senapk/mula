from .credentials import Credentials


class URLHandler:
    def __init__(self):
        self.credentials: Credentials = Credentials.load_credentials()
        self._url_base: str = self.credentials.url

    def get_course_id(self) -> str:
        return self.credentials.get_course()

    def __str__(self):
        return self._url_base + ":" + self.get_course_id()

    def base(self):
        return self._url_base

    def course(self):
        return self._url_base + "/course/view.php?id=" + self.get_course_id()

    def login(self):
        return self._url_base + '/login/index.php'

    def delete_action(self):
        return self._url_base + "/course/mod.php"

    def delete_vpl(self, qid: int):
        return self.delete_action() + "?sr=0&delete=" + str(qid)

    def keep_files(self, qid: int):
        return self._url_base + '/mod/vpl/forms/executionkeepfiles.php?id=' + str(qid)

    def new_vpl(self, section: int):
        return self._url_base + "/course/modedit.php?add=vpl&type=&course=" + self.get_course_id() + "&section=" + \
               str(section) + "&return=0&sr=0 "

    def view_vpl(self, qid: int):
        return self._url_base + '/mod/vpl/view.php?id=' + str(qid)

    def update_vpl(self, qid: int):
        return self._url_base + '/course/modedit.php?update=' + str(qid)

    def new_test(self, qid: int):
        return self._url_base + "/mod/vpl/forms/testcasesfile.php?id=" + str(qid) + "&edit=3"

    # def test_save(self, id: int):
    #     return self._url_base + "/mod/vpl/forms/testcasesfile.json.php?id=" + str(id) + "&action=save"

    def execution_files(self, qid: int):
        return self._url_base + '/mod/vpl/forms/executionfiles.json.php?id=' + str(qid) + '&action=save'

    def required_files(self, qid: int):
        return self._url_base + '/mod/vpl/forms/requiredfiles.json.php?id=' + str(qid) + '&action=save'

    def execution_options(self, qid: int):
        return self._url_base + "/mod/vpl/forms/executionoptions.php?id=" + str(qid)

    @staticmethod
    def parse_id(url: str) -> str:
        return url.split("id=")[1].split("&")[0]

    @staticmethod
    def parse_id_from_update(url: str) -> str:
        return url.split("update=")[1]

    @staticmethod
    def is_vpl_url(url: str) -> bool:
        return '/mod/vpl/view.php?id=' in url
