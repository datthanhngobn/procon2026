import json
import os
from typing import List, Union, Optional
import requests

from config import URL, HEADER
import get_map


def _resolve_match_id(match_id: Optional[str] = None) -> str:
    """
    Xác định match_id được truyền vào hoặc lấy từ get_map.ID.
    """
    if match_id:
        return str(match_id).strip()

    if getattr(get_map, "ID", None):
        return str(get_map.ID).strip()

    raise ValueError(
        "Chưa có match_id! Vui lòng truyền match_id vào hàm hoặc gọi get_map() trước."
    )


def _load_data_if_filepath(data: Union[list, str]) -> list:
    """
    Nếu data là đường dẫn file JSON, đọc file và parse JSON.
    Nếu data đã là list thì giữ nguyên.
    """
    if isinstance(data, str):
        if not os.path.exists(data):
            raise FileNotFoundError(f"Không tìm thấy file JSON: {data}")
        with open(data, "r", encoding="utf-8") as f:
            return json.load(f)
    return data


def validate_config(agents_config: list, num_agents: Optional[int] = None) -> (bool, str):
    """
    Kiểm tra tính hợp lệ của cấu hình tác nhân (config) theo quy định trong PDF:
    - Phải là một mảng 1 chiều chứa các số nguyên.
    - Mỗi phần tử chỉ được mang giá trị {0, 1}:
        0: Xe tuần tra (patrol car)
        1: Xe tiếp nhiên liệu (supply car)
    - Nếu có num_agents: số phần tử phải bằng số lượng agent.
    """
    if not isinstance(agents_config, list):
        return False, "Cấu hình tác nhân phải là một danh sách (list)."

    if num_agents is not None and len(agents_config) != num_agents:
        return False, f"Số phần tử ({len(agents_config)}) không khớp với số agent ({num_agents})."

    for idx, val in enumerate(agents_config):
        if not isinstance(val, int) or val not in (0, 1):
            return False, f"Phần tử thứ {idx} có giá trị {val} không hợp lệ. Chỉ chấp nhận 0 hoặc 1."

    return True, "Hợp lệ"


def validate_answer(answer_data: list, num_agents: Optional[int] = None) -> (bool, str):
    """
    Kiểm tra tính hợp lệ cơ bản của kế hoạch hành động (answer) theo quy định trong PDF:
    - Phải là mảng 2 chiều (danh sách hành động cho từng agent).
    - Mỗi hành động là một số nguyên:
        <= -1 : Chờ (ví dụ -15 là chờ 15 step).
        0 ~ 5 : Hướng di chuyển (0: trên-trái, 1: trên-phải, 2: phải, 3: dưới-phải, 4: dưới-trái, 5: trái).
    - Nếu có num_agents: số hàng phải khớp với số agent.
    """
    if not isinstance(answer_data, list):
        return False, "Kế hoạch hành động phải là danh sách 2 chiều (list of lists)."

    if num_agents is not None and len(answer_data) != num_agents:
        return False, f"Số lượng danh sách hành động ({len(answer_data)}) không khớp với số agent ({num_agents})."

    for agent_idx, actions in enumerate(answer_data):
        if not isinstance(actions, list):
            return False, f"Hành động của agent {agent_idx} phải là một danh sách các số nguyên."

        for step_idx, act in enumerate(actions):
            if not isinstance(act, int):
                return False, f"Agent {agent_idx}, bước {step_idx}: '{act}' không phải số nguyên."
            if not (act <= -1 or 0 <= act <= 5):
                return False, (
                    f"Agent {agent_idx}, bước {step_idx}: giá trị {act} không hợp lệ. "
                    "Chỉ chấp nhận số <= -1 (chờ) hoặc 0..5 (hướng di chuyển)."
                )

    return True, "Hợp lệ"


def submit_config(
    agents_config: Union[List[int], str],
    match_id: Optional[str] = None,
    num_agents: Optional[int] = None
) -> requests.Response:
    """
    Nộp cấu hình loại tác nhân trước khi trận đấu bắt đầu.

    Endpoint: POST /api/game/matches/{match_id}/agents
    Quy cách JSON (Theo PDF trang 3):
        Mảng 1 chiều, ví dụ: [0, 1, 0, 1]
        0: Xe tuần tra (巡回車)
        1: Xe tiếp nhiên liệu (補給車)

    :param agents_config: List các số nguyên {0, 1} hoặc đường dẫn tới file .json
    :param match_id: Mã trận đấu (nếu None sẽ lấy từ get_map.ID)
    :param num_agents: Số lượng agent dự kiến để kiểm tra tính hợp lệ (tùy chọn)
    :return: requests.Response từ máy chủ
    """
    actual_match_id = _resolve_match_id(match_id)
    payload = _load_data_if_filepath(agents_config)

    # Kiểm tra tính hợp lệ trước khi gửi
    is_valid, reason = validate_config(payload, num_agents)
    if not is_valid:
        print(f"[CẢNH BÁO FORMAT] Cấu hình không đúng định dạng PDF: {reason}")

    endpoint = f"{URL.rstrip('/')}/{actual_match_id}/agents"
    print(f"\n[GỬI CONFIG] Đang nộp loại tác nhân lên: {endpoint}")
    print(f"Payload (JSON): {json.dumps(payload)}")

    response = requests.post(endpoint, json=payload, headers=HEADER)

    print(f"HTTP Status: {response.status_code}")
    try:
        res_json = response.json()
        print(f"Phản hồi từ máy chủ: {json.dumps(res_json, ensure_ascii=False, indent=2)}")
    except Exception:
        print(f"Phản hồi dạng text: {response.text}")

    if response.status_code == 200:
        print("=> Nộp cấu hình tác nhân THÀNH CÔNG!")
    else:
        print(f"=> Nộp cấu hình THẤT BẠI (Mã lỗi {response.status_code})")

    return response


def submit_answer(
    actions: Union[List[List[int]], str],
    match_id: Optional[str] = None,
    num_agents: Optional[int] = None
) -> requests.Response:
    """
    Nộp kế hoạch hành động trong thời gian quy định của mỗi ngày thi đấu.

    Endpoint: POST /api/game/matches/{match_id}/answer
    Quy cách JSON (Theo PDF trang 3):
        Mảng 2 chiều, mỗi phần tử là mảng hành động của 1 agent.
        Ví dụ:
        [
            [-15],
            [0, 1, -10]
        ]
        - Số <= -1: Thời gian chờ (ví dụ -15 là chờ 15 bước).
        - Số 0 ~ 5: Hướng di chuyển lục giác:
            0: Trên - Trái
            1: Trên - Phải
            2: Phải
            3: Dưới - Phải
            4: Dưới - Trái
            5: Trái

    :param actions: List 2D các số nguyên hoặc đường dẫn tới file .json
    :param match_id: Mã trận đấu (nếu None sẽ lấy từ get_map.ID)
    :param num_agents: Số lượng agent dự kiến để kiểm tra tính hợp lệ (tùy chọn)
    :return: requests.Response từ máy chủ
    """
    actual_match_id = _resolve_match_id(match_id)
    payload = _load_data_if_filepath(actions)

    # Kiểm tra tính hợp lệ trước khi gửi
    is_valid, reason = validate_answer(payload, num_agents)
    if not is_valid:
        print(f"[CẢNH BÁO FORMAT] Kế hoạch không đúng định dạng PDF: {reason}")

    endpoint = f"{URL.rstrip('/')}/{actual_match_id}/answer"
    print(f"\n[GỬI ANSWER] Đang nộp câu trả lời lên: {endpoint}")
    print(f"Payload (JSON): {json.dumps(payload)}")

    response = requests.post(endpoint, json=payload, headers=HEADER)

    print(f"HTTP Status: {response.status_code}")
    try:
        res_json = response.json()
        print(f"Phản hồi từ máy chủ: {json.dumps(res_json, ensure_ascii=False, indent=2)}")
    except Exception:
        print(f"Phản hồi dạng text: {response.text}")

    if response.status_code == 200:
        print("=> Nộp câu trả lời THÀNH CÔNG!")
    else:
        print(f"=> Nộp câu trả lời THẤT BẠI (Mã lỗi {response.status_code})")

    return response


def save_json_file(data: Union[list, dict], filepath: str) -> None:
    """Lưu dữ liệu ra file JSON phục vụ lưu trữ hoặc nộp sau."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Đã lưu file: {filepath}")

