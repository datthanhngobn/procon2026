import sys
import json
import time
import requests

from config import URL, HEADER
from get_map import get_map
import get_map as gm_module
from submit import submit_config, submit_answer, validate_config, validate_answer
from alg import solve_daily_actions


def decide_agent_types(map_config: dict) -> list:
    """
    Tự động quyết định cấu hình loại xe [0: Tuần tra, 1: Tiếp tế]
    dựa trên kích thước map, fuelLimits và tổng số daySteps.

    Quy tắc giá trị:
        0: Xe tuần tra - ăn điểm udon
        1: Xe tiếp nhiên liệu - tiếp xăng cho xe tuần tra
    """
    map_info = map_config.get("map", {})
    width = map_info.get("width", 8)
    height = map_info.get("height", 8)
    fuel_limit = map_config.get("fuelLimits", 20)
    day_steps_list = map_config.get("daySteps", [50])
    agents = map_config.get("agents", [])
    num_agents = len(agents)

    if num_agents == 0:
        raise ValueError("Danh sách agents trong map_config rỗng!")

    total_steps = sum(day_steps_list)
    num_days = len(day_steps_list)
    map_diagonal = (width + height) // 2

    # 1 bình xăng đi được trung bình bao nhiêu step (trung bình 1 fuel ~ 1.5 step)
    max_steps_single_tank = fuel_limit * 1.5

    # Tỉ lệ thâm hụt nhiên liệu (Fuel Exhaustion Ratio)
    fer = total_steps / max_steps_single_tank if max_steps_single_tank > 0 else 999.0

    print("--------------------------------------------------")
    print("[PHÂN TÍCH THÔNG SỐ TRẬN ĐẤU]")
    print(f" - Kích thước bản đồ: {width} x {height} (Bán kính ~ {map_diagonal} ô)")
    print(f" - Số lượng xe của đội: {num_agents} xe")
    print(f" - Giới hạn nhiên liệu 1 bình: {fuel_limit} fuel")
    print(f" - Số ngày thi đấu: {num_days} ngày | Các ngày: {day_steps_list}")
    print(f" - Tổng số step cả giải: {total_steps} step")
    print(f" - Ước tính 1 bình xăng đi được: ~{int(max_steps_single_tank)} step")
    print(f" - Chỉ số thâm hụt nhiên liệu (FER): {fer:.2f}")
    print("--------------------------------------------------")

    # TRƯỜNG HỢP 1: Step nhỏ (FER <= 1.1)
    if fer <= 1.1:
        print("[CHIẾN THUẬT] STEP NHỎ (FER <= 1.1)")
        print("   => Toàn bộ xe tuần tra (0). Tối đa hóa số lượng xe đi ăn Udon.")
        return [0] * num_agents

    # TRƯỜNG HỢP 2: Step trung bình (1.1 < FER <= 2.5) hoặc số xe ít (<= 3 xe)
    if fer <= 2.5 or num_agents <= 3:
        print("[CHIẾN THUẬT] STEP TRUNG BÌNH (1.1 < FER <= 2.5)")
        print("   => 1 xe tiếp tế (1) ở cuối danh sách, các xe còn lại là xe tuần tra (0).")
        config = [0] * num_agents
        config[-1] = 1
        return config

    # TRƯỜNG HỢP 3: Step lớn & Map rộng (FER > 2.5)
    print("[CHIẾN THUẬT] STEP LỚN & MAP RỘNG (FER > 2.5)")
    print("   => Ghép cặp xen kẽ xe tuần tra (0) và xe tiếp tế (1).")
    config = []
    for i in range(num_agents):
        # Xen kẽ: 0, 1, 0, 1...
        config.append(i % 2)
    return config


def run_config_pipeline(map_config=None) -> list:
    """
    Quy trình nộp cấu hình loại xe trước trận đấu:
    1. Gọi API lấy cấu hình bản đồ từ máy chủ (nếu map_config chưa có).
    2. Phân tích thông số map để quyết định mảng loại xe.
    3. Nộp cấu hình (POST .../agents) lên máy chủ.
    """
    print("==================================================")
    print("   PROCON 2026: QUY TRÌNH NỘP CẤU HÌNH BAN ĐẦU    ")
    print("==================================================")

    if map_config is None:
        print("\n[BƯỚC 1] Đang gọi API lấy thông tin trận đấu từ server...")
        try:
            map_config, _ = get_map()
        except Exception as e:
            print(f"Không thể lấy dữ liệu từ server: {e}")
            return None

    match_id = gm_module.ID
    print(f"Mã trận đấu (Match ID): {match_id}")

    # 2. Quyết định loại xe
    print("\n[BƯỚC 2] Tính toán cấu hình xe tối ưu...")
    chosen_config = decide_agent_types(map_config)
    num_agents = len(map_config.get("agents", []))

    # 3. Nộp cấu hình
    print("\n[BƯỚC 3] Đang nộp cấu hình lên máy chủ (POST .../agents)...")
    res = submit_config(
        agents_config=chosen_config,
        match_id=match_id,
        num_agents=num_agents
    )

    if res.status_code == 200:
        print("\nHOÀN THÀNH: Đã nộp cấu hình xe thành công!")
    else:
        print(f"\nMáy chủ phản hồi mã lỗi: {res.status_code}")

    return chosen_config


def run_daily_pipeline(game_state: dict = None) -> list:
    """
    Quy trình tính toán và nộp kế hoạch cho ngày hiện tại:
    1. Lấy map_config và match_status mới nhất từ máy chủ.
    2. Chạy thuật toán solve_daily_actions() để tìm hướng đi tối ưu cho mọi agent.
    3. Nộp kết quả lên máy chủ qua submit_answer().
    """
    if game_state is None:
        game_state = {}

    print("==================================================")
    print("      PROCON 2026: LẬP KẾ HOẠCH & NỘP ANSWER      ")
    print("==================================================")

    print("\n[BƯỚC 1] Lấy dữ liệu trận đấu và ngày hiện tại từ server...")
    try:
        map_config, match_status = get_map()
    except Exception as e:
        print(f"Không thể kết nối server: {e}")
        return None

    match_id = gm_module.ID
    if match_status is None:
        print("Chưa có thông tin match_status từ máy chủ (trận đấu có thể chưa bắt đầu)!")
        return None

    current_day = match_status.get("day", 0)
    print(f"Đang ở Ngày thi đấu thứ: {current_day}")

    # 2. Chạy thuật toán giải quyết cho tất cả các agent
    print("\n[BƯỚC 2] Đang chạy thuật toán tối ưu hóa đường đi...")
    all_actions = solve_daily_actions(
        map_config=map_config,
        match_status=match_status,
        game_state=game_state
    )

    num_agents = len(match_status.get("agents", []))
    print(f"Đã tạo kế hoạch hành động ({num_agents} xe):")
    for idx, act in enumerate(all_actions):
        print(f"   - Xe {idx}: {act}")

    # Kiểm tra tính hợp lệ trước khi nộp
    is_valid, msg = validate_answer(all_actions, num_agents=num_agents)
    if not is_valid:
        print(f"Kế hoạch không hợp lệ: {msg}")
        return all_actions

    # 3. Nộp câu trả lời lên server
    print("\n[BƯỚC 3] Nộp câu trả lời lên máy chủ (POST .../answer)...")
    res = submit_answer(
        actions=all_actions,
        match_id=match_id,
        num_agents=num_agents
    )

    if res.status_code == 200:
        print(f"\nHOÀN THÀNH: Đã nộp thành công câu trả lời cho Ngày {current_day}!")
    else:
        print(f"\nLỗi khi nộp câu trả lời (Mã {res.status_code})")

    return all_actions


if __name__ == "__main__":
    # Lưu trạng thái các loại udon đã ăn trong cả trận đấu
    match_game_state = {
        "visited_brands_all_time": set()
    }

    # 1. Chạy bước nộp config ban đầu trước trận đấu
    run_config_pipeline()

    # 2. Chạy bước tính toán và nộp answer cho ngày hiện tại
    # run_daily_pipeline(match_game_state)
