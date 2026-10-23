import requests
from terrain import Plain, Mountain, Pond, Road
from config import URL, HEADER

ID = ""
GET_MAP_CONFIG = ""
GET_MAP_STATUS = ""

HEIGHT = 0
WIDTH = 0
CELLS = []
SPOTS = []
DAY_STEPS = []

def get_map():
    global ID, GET_MAP_CONFIG, GET_MAP_STATUS, HEIGHT, WIDTH, CELLS, SPOTS, DAY_STEPS
    json_matches = requests.get(URL, headers=HEADER)
    if json_matches.status_code != 200:
        raise RuntimeError(
            f"Không thể kết nối API matches (HTTP {json_matches.status_code}): {json_matches.text}\n"
            "Vui lòng kiểm tra lại token trong file config.py!"
        )
    data = json_matches.json()
    matches = data.get('matches', [])
    if not matches:
        raise RuntimeError("Không có trận đấu nào đang khả dụng trong danh sách 'matches'!")

    ID = matches[0]['id']
    GET_MAP_CONFIG = f"{URL.rstrip('/')}/{ID}/config"
    GET_MAP_STATUS = f"{URL.rstrip('/')}/{ID}/status"

    cfg_res = requests.get(GET_MAP_CONFIG, headers=HEADER)
    if cfg_res.status_code != 200:
        raise RuntimeError(f"Lỗi lấy map config (HTTP {cfg_res.status_code}): {cfg_res.text}")
    get_map_config = cfg_res.json()

    CELLS = get_map_config["map"]["cells"]
    SPOTS = get_map_config.get("spots", [])
    DAY_STEPS = get_map_config.get("daySteps", [])
    HEIGHT = get_map_config["map"]["height"]
    WIDTH = get_map_config["map"]["width"]

    # Status có thể chưa mở nếu trận đấu chưa chính thức bắt đầu
    get_map_status = None
    try:
        st_res = requests.get(GET_MAP_STATUS, headers=HEADER)
        if st_res.status_code == 200:
            get_map_status = st_res.json()
    except Exception:
        pass

    return get_map_config, get_map_status


