import requests
from terrain import Plain, Mountain, Pond, Road

URL = "https://procon26.haui.ac.vn/api/game/matches/"
HEADER = {
    "x-api-token": "procon_101dad2d1f3047e5887b0a5b8f886441"
}
ID : str
GET_MAP_CONFIG : str
GET_MAP_STATUS : str

HEIGHT : int
WIDTH : int
CELLS : list

def get_map() :
    json_matches = requests.get(URL, headers = HEADER)
    data = json_matches.json()
    ID = data['matches'][0]['id']
    GET_MAP_CONFIG = URL + ID + "/config"
    GET_MAP_STATUS = URL + ID + "/status"
    get_map_config = requests.get(GET_MAP_CONFIG, headers = HEADER).json()
    get_map_status = requests.get(GET_MAP_STATUS, headers = HEADER).json()

    CELLS = get_map_config["map"]["cells"]

    print(CELLS)

def parse_response() :
    ...
