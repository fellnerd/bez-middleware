import requests
import json
import os

class ApiClient:
    """REST API Client to Dimetrics"""

    ROOT_API_KEY = "OcEt1b4U.U45t2WRRFJy6kyXSXNkcotxVzXA10hiH" if os.getenv('API_KEY') == None else os.getenv('API_KEY')
    BASE_URL = os.getenv('DMX_HOST') 
    

    def __init__(self, base_url = BASE_URL) -> None:
        self.BASE_URL = base_url

    def fetch(self, service:str, resource:str, params = None, api_key = ROOT_API_KEY, callback = None):
        headers = {"Authorization":self.ROOT_API_KEY} if self.ROOT_API_KEY else None
        response = requests.get(url=f"{self.BASE_URL}/{service}/{resource}/", params=params, headers=headers)
        if callback:
            callback(response)
        if response.ok:
            return response.json()["results"]
        else:
            return None

    def get(self, service:str, resource:str, id:int, api_key = ROOT_API_KEY, callback = None):
        headers = {"Authorization":self.ROOT_API_KEY} if self.ROOT_API_KEY else None
        response = requests.get(url=f"{self.BASE_URL}/{service}/{resource}/{id}", headers=headers)
        if callback:
            callback(response)
        if response.ok:
            return response.json()
        else:
            return None

    def post(self, service:str, resource:str, data, api_key = ROOT_API_KEY, callback = None):
        headers = {"Authorization":self.ROOT_API_KEY, "Content-Type": "application/json"} if self.ROOT_API_KEY else None
        response = requests.post(url=f"{self.BASE_URL}/{service}/{resource}/", headers=headers, data= json.dumps(data))
        if callback:
            callback(response)
        return response.json()

    def update(self, service:str, resource:str, data, id:int, *args, api_key = ROOT_API_KEY, callback = None, **kwargs):
        headers = {"Authorization":self.ROOT_API_KEY, "Content-Type": "application/json"} if self.ROOT_API_KEY else None
        response = requests.put(url=f"{self.BASE_URL}/{service}/{resource}/{id}", headers=headers, data= json.dumps(data))
        if callback:
            callback(response, **kwargs)
        return response.json()

    def delete(self, service:str, resource:str, id:int, api_key = ROOT_API_KEY, callback = None):
        headers = {"Authorization":self.ROOT_API_KEY} if self.ROOT_API_KEY else None
        response = requests.delete(url=f"{self.BASE_URL}/{service}/{resource}/{id}", headers=headers)
        if callback:
            callback(response)
        return response.json()

