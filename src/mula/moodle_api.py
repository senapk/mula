from .credentials import Credentials
from .url_handler import URLHandler
import mechanicalsoup
from .json_tools import JsonVPL, JsonFile
from typing import Optional, Any, List
from .log import Log
import json
from .task import Task

class MoodleAPI:
    default_timeout: int = 10

    def __init__(self):
        self.task: Task | None = None
        self.credentials = Credentials.load_credentials()
        self.urlHandler = URLHandler()
        self.browser = mechanicalsoup.StatefulBrowser(user_agent='MechanicalSoup')
        self.browser.set_user_agent('Mozilla/5.0')
        self._login()

    def set_task(self, task: Task):
        self.task = task
        return self
    
    def get_task(self):
        if self.task is None:
            raise Exception("Task not set")
        return self.task

    def open_url(self, url: str, data_files: Optional[Any] = None):
        if MoodleAPI.default_timeout != 0:
            if data_files is None:
                self.browser.open(url, timeout=MoodleAPI.default_timeout)
            else:
                self.browser.open(url, timeout=MoodleAPI.default_timeout, data=data_files)
        else:
            if data_files is None:
                self.browser.open(url)
            else:
                self.browser.open(url, data=data_files)

    def _login(self):
        self.browser.open(self.urlHandler.login())
        self.browser.select_form(nr=0)
        self.browser['username'] = self.credentials.username
        self.browser['password'] = self.credentials.password
        self.browser.submit_selected()
        if self.browser.get_url() == self.urlHandler.login():
            print("Erro de login, verifique login e senha")
            exit(0)

    def delete(self, qid: int):
        self.get_task().log.send("load")
        self.open_url(self.urlHandler.delete_vpl(qid))
        self.get_task().log.send("submit")
        self.browser.select_form(nr=0)
        self.browser.submit_selected()

    def download(self, vplid: int) -> JsonVPL:
        url = self.urlHandler.view_vpl(vplid)
        self.get_task().log.send("open")
        self.open_url(url)
        self.get_task().log.send("parse")
        soup = self.browser.page
        arqs = soup.findAll('h4', {'id': lambda value: value and value.startswith("fileid")})
        title = soup.find('a', {'href': self.browser.get_url()}).get_text()
        try:
            descr = soup.find('div', {'class': 'box py-3 generalbox'}).find('div', {'class': 'no-overflow'}).get_text()
        except AttributeError:
            descr = ""

        vpl = JsonVPL(title, descr)
        for arq in arqs:
            cont = soup.find('pre', {'id': 'code' + arq.get('id')})
            file = JsonFile(name=arq.get_text(), contents=cont.get_text())
            if arq.find_previous_sibling('h2').get_text() == "Arquivos requeridos":
                vpl.required.append(file)
            else:
                vpl.upload.append(file)
        return vpl

    def set_duedate_field_in_form(self, duedate: Optional[str]):
        if duedate is None:  # unchange default
            return

        if duedate == "0":  # disable
            self.browser["duedate[enabled]"] = False
            return
        self.browser["duedate[enabled]"] = True
        year, month, day, hour, minute = duedate.split(":")

        self.browser["duedate[year]"] = year
        self.browser["duedate[month]"] = str(int(month))  # tranform 05 to 5
        self.browser["duedate[day]"] = str(int(day))
        self.browser["duedate[hour]"] = str(int(hour))
        self.browser["duedate[minute]"] = str(int(minute))

    def update_duedate_only(self, url: str, duedate: Optional[str] = None):
        self.get_task().log.send("duedate")
        self.open_url(url)
        self.browser.select_form(nr=0)
        self.set_duedate_field_in_form(duedate)
        self.browser.form.choose_submit("submitbutton")
        self.browser.submit_selected()

    def send_basic_info(self, url: str, vpl: Optional[JsonVPL]) -> int:
        self.open_url(url)
        param = self.get_task().param
        self.browser.select_form(nr=0)

        if vpl is not None and param.info == True:
            self.get_task().log.send("description")
            self.browser['name'] = vpl.title
            self.browser['introeditor[text]'] = vpl.description
    
        if param.visible is not None:
            self.get_task().log.send("visible")
            self.browser['visible'] = '1' if param.visible else '0'

        if param.duedate is not None:
            self.get_task().log.send("duedate")
            self.set_duedate_field_in_form(param.duedate)

        if param.maxfiles is not None and vpl is not None:
            self.get_task().log.send("maxfiles")
            self.browser['maxfiles'] = max(len(vpl.keep), int(param.maxfiles))
    
        self.browser.form.choose_submit("submitbutton")
        self.browser.submit_selected()

        if url.find("update") != -1:
            qid = URLHandler.parse_id_from_update(url)
        else:
            url2 = self.browser.get_url()
            qid = URLHandler.parse_id(url2)
        return int(qid)

    def set_keep(self, qid: int, keep_size: int):
        self.open_url(self.urlHandler.keep_files(qid))
        self.browser.select_form(nr=0)
        for index in range(4, 4 + keep_size):
            self.browser["keepfile" + str(index)] = "1"
        self.browser.submit_selected()
        
    def _send_vpl_files(self, url: str, vpl_files: List[JsonFile]):
        params = {'files': vpl_files, 'comments': ''}
        files = json.dumps(params, default=self.__dumper, indent=2)
        self.open_url(url, files)

    def get_removed_files(old: JsonVPL, new: JsonVPL) -> dict:
        def removed_names(old_list, new_list):
            new_names = {f.name for f in new_list}
            return [f.name for f in old_list if f.name not in new_names]

        removed = {
            'upload': removed_names(old.upload, new.upload),
            'required': removed_names(old.required, new.required),
            'keep': removed_names(old.keep, new.keep),
            'drafts': {}
        }

        for draft_name, old_files in old.drafts.items():
            new_files = new.drafts.get(draft_name, [])
            removed['drafts'][draft_name] = removed_names(old_files, new_files)

        return removed

    def send_files(self, vpl: JsonVPL, qid: int):
        self._send_vpl_files(self.urlHandler.execution_files(qid), vpl.keep + vpl.upload)  # don't change this order

        if len(vpl.required) > 0:
            self._send_vpl_files(self.urlHandler.required_files(qid), vpl.required)

        diferenca = self.get_removed_files(self.download(qid),vpl)

        self.set_keep(qid,0)

    def set_execution_options(self, qid: int):

        self.open_url(self.urlHandler.execution_options(qid))

        self.browser.select_form(nr=0)

        self.browser['run'] = "1"
        self.browser['debug'] = "1"
        self.browser['evaluate'] = "1"
        # self.browser.submit()
        #
        # self.browser.select_form(action='executionoptions.php')
        self.browser['automaticgrading'] = "1"
        self.browser.submit_selected()



    @staticmethod
    def __dumper(obj):
        try:
            return obj.to_json()
        except AttributeError:
            return obj.__dict__
