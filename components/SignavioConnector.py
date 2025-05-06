import requests
from datetime import datetime

class AuthenticationError(Exception):
    pass

class UploadError(Exception):
    pass

class ExportError(Exception):
    pass

class SignavioConnector:
    def __init__(self, system_instance, workspace_id, target_directory):
        self.system_instance = system_instance
        self.workspace_id = workspace_id
        self.target_directory = target_directory
        self.auth_token= ""
        self.cookies = {}
        self.file_name = ""

    def authenticate(self, user_name, password):
        url = self.system_instance + "/p/login"
        data = {"name": user_name, "password": password, "tokenonly": "true", "tenant": self.workspace_id}

        login_response = requests.post(url, data)

        if login_response.status_code != 200:
            raise AuthenticationError(
                {"status": login_response.status_code, "content": login_response.content}
            )
        
        self.auth_token = login_response.content.decode("utf-8")

        self.cookies = {"JSESSIONID": login_response.cookies["JSESSIONID"], "LBROUTEID": login_response.cookies["LBROUTEID"]}

    def import_model(self, bpmn):
        headers = {'Accept': 'application/json', 'x-signavio-id':  self.auth_token}
        url = self.system_instance + "/p/bpmn2_0-import"
        self.file_name = "process_"+ datetime.now().strftime("%Y%m%d_%H%M%S")
        files = {"bpmn2_0file": (self.file_name +".bpmn", bpmn, "application/xml")}
        data = {"filename": self.file_name +".bpmn", "directory": self.target_directory}

        upload_response = requests.post(url, headers=headers, cookies=self.cookies, files=files, data=data)

        if not upload_response.ok:
            raise UploadError(
                {"status": upload_response.status_code, "content": upload_response.content}
            )
        
    def export_model(self):
        headers = {'Accept': 'application/json', 'x-signavio-id':  self.auth_token}
        url = self.system_instance + "/p/directory/" + self.target_directory
        list_response = requests.get(url, headers=headers, cookies=self.cookies)
        if not list_response.ok:
            raise ExportError(
                {"status": list_response.status_code, "content": list_response.content}
            )
        models = list_response.json()

        model_id = None
        for model in models:
            if model.get("rel") == "mod":
                name = model.get("rep", {}).get("name")
                if name == self.file_name:
                    href = model.get("href", "")
                    model_id = href.split('/')[-1]
                    break
        if not model_id:
            raise ExportError(
                {"status": 400, "content": "Model not found"}
            )
        
        model_url = self.system_instance + "/p/model/" + model_id

        model_response = requests.get(model_url, headers=headers, cookies=self.cookies)
        model_details = model_response.json()
        revision_id = None
        for entry in model_details:
            if entry.get("rel") == "info":
                revision_path = entry.get("rep", {}).get("revision")
                if revision_path:
                    revision_id = revision_path.split("/")[-1]
                    break
        if not revision_id:
            raise ExportError({"status": 400, "content": "Failed to get revision ID"})
        
        png_url = self.system_instance + "/p/revision/" + revision_id + "/png"
        png_response = requests.get(png_url, headers=headers, cookies=self.cookies)

        if not png_response.ok:
            raise ExportError({
                "status": png_response.status_code, "content": png_response.content
            })
        
        return png_response.content
