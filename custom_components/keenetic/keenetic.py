from hashlib import md5, sha256
from json import loads

from requests import Session


class ConnectedDevice:
    def __init__(self, dictionary):
        self.__dict__ = {
            key.replace("-", "_"): value for key, value in dictionary.items()
        }


class Router:
    def __init__(self, username="admin", password="", host="192.168.1.1", port=80):
        self.__session = Session()
        self.__endpoint = f"http://{host}:{port}"
        self.__username = username
        self.__password = password
        self.__auth(username, password)

    def __auth(self, username, password):
        response = self.get("/auth")
        if response.status_code == 401:
            realm = response.headers["X-NDM-Realm"]
            password = f"{username}:{realm}:{password}"
            password = md5(password.encode("utf-8"))
            challenge = response.headers["X-NDM-Challenge"]
            password = challenge + password.hexdigest()
            password = sha256(password.encode("utf-8")).hexdigest()
            response = self.post("/auth", {"login": username, "password": password})
        return response.status_code == 200

    @property
    def is_authenticated(self):
        return self.__auth(self.__username, self.__password)

    def get(self, address, params={}):
        return self.__session.get(self.__endpoint + address, params=params)

    def post(self, address, data):
        return self.__session.post(self.__endpoint + address, json=data)

    @property
    def connected_devices(self):
        response = self.get("/rci/show/ip/hotspot")
        if response.ok:
            devices = loads(response.text)["host"]
            return list(
                filter(lambda device: device.active, map(ConnectedDevice, devices))
            )
        else:
            return []
