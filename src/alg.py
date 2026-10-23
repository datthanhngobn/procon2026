import heapq
from terrain import Plain, Mountain, Road, Pond
from get_map import CELLS

INF = float('inf')

# Mã địa hình theo API: 0 đồng bằng, 1 đường bộ, 2 núi, 3 ao
PLAIN, ROAD, MOUNTAIN, POND = 0, 1, 2, 3

# Bảng 1 của đề: (step, fuel_need) khi RỜI ô thuộc địa hình đó
BASE_COST = {
    PLAIN    : (2, 1),
    MOUNTAIN : (3, 2),
    POND     : (INF, INF),
}
# Đường bộ: step phụ thuộc trạng thái (0 thông thoáng, 1 đông đúc, 2 ùn tắc), fuel luôn = 2
ROAD_STEP = {0 : 1, 1 : 2, 2 : 4}
ROAD_FUEL = 2


def get_neighbors(node_index, width, height) -> list :
    """
    Tìm các ô lân cận của một ô trong bản đồ lục giác
    Sử dụng hệ tọa độ "even-r" (hàng chẵn thụt lề phải, theo Hình 1 của đề)
    Map đặt hệ tọa độ từ 0
    """
    r = node_index // width
    c = node_index % width

    # Độ lệch (dr, dc) theo đúng thứ tự mã hướng của API:
    # [0: trên trái, 1: trên phải, 2: phải, 3: dưới phải, 4: dưới trái, 5: trái]
    if r % 2 == 0 :
        # Hàng chẵn (thụt phải): hàng trên/dưới lệch về bên phải
        d = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (0, -1)]
    else :
        # Hàng lẻ: hàng trên/dưới lệch về bên trái
        d = [(-1, -1), (-1, 0), (0, 1), (1, 0), (1, -1), (0, -1)]

    neighbors = []
    for dr, dc in d :
        nr, nc = r + dr, c + dc
        if 0 <= nr < height and 0 <= nc < width :
            neighbors.append(nr * width + nc)
        else :
            # Ngoài bản đồ -> None, để vị trí trong list luôn ứng đúng hướng
            neighbors.append(None)

    # Map trả về định dạng list [trên trái, trên phải, phải, dưới phải, dưới trái, trái]
    # => neighbors[k] chính là ô đến khi gửi lệnh di chuyển k lên API
    return neighbors


def flatten_cells(cells) -> list :
    """
    Chuyển "cells" 2 chiều từ API thành list 1 chiều để khớp với node index
    terrain[r * width + c] = cells[r][c]
    """
    return [t for row in cells for t in row]


def build_adj(terrain, width, height) -> list :
    """
    Dựng danh sách kề (cách A) - chỉ cần gọi 1 lần đầu trận vì địa hình không đổi
    adj[u] luôn có 6 phần tử theo mã hướng API, None = ngoài map hoặc là ao
    Ô ao cũng có adj (toàn None) để index không bị lệch
    """
    adj = []
    for u in range(width * height) :
        row = []
        for v in get_neighbors(u, width, height) :
            if v is not None and terrain[v] != POND :
                row.append(v)
            else :
                row.append(None)
        adj.append(row)
    return adj


def build_cost(terrain) -> list :
    """
    Dựng list chi phí ban đầu: cost[i] = (step, fuel_need) khi rời ô i
    Ngày 1 mọi đường đều thông thoáng
    """
    cost = []
    for t in terrain :
        if t == ROAD :
            cost.append((ROAD_STEP[0], ROAD_FUEL))
        else :
            cost.append(BASE_COST[t])
    return cost


def update_traffic(cost, traffics) -> None :
    """
    Cập nhật step của các ô đường theo "traffics" mà API trả về mỗi ngày
    traffics = [{"pos": int, "status": 0|1|2}, ...]
    Ghi đè trực tiếp lên cost (giữ qua các ngày)
    """
    for t in traffics :
        cost[t["pos"]] = (ROAD_STEP[t["status"]], ROAD_FUEL)


def dijkstra(src, adj, cost) :
    """
    Tìm đường đi ngắn nhất (theo step) từ src tới mọi ô
    Nếu 2 đường bằng step thì ưu tiên đường tốn ít fuel hơn

    Lưu ý: chi phí cạnh u -> v = cost[u] (tính theo ô ĐANG ĐỨNG, đúng luật đề)

    Trả về:
        dist_step[v] : tổng step nhỏ nhất từ src tới v (INF nếu không tới được)
        dist_fuel[v] : tổng fuel tương ứng với đường đi đó
        parent[v]    : ô liền trước v trên đường đi (-1 nếu không có)
        parent_dir[v]: mã hướng API đã dùng để đi từ parent[v] sang v
    """
    n = len(adj)
    dist_step = [INF] * n
    dist_fuel = [INF] * n
    parent = [-1] * n
    parent_dir = [-1] * n

    dist_step[src] = 0
    dist_fuel[src] = 0
    pq = [(0, 0, src)]

    while pq :
        d_step, d_fuel, u = heapq.heappop(pq)

        # Bỏ qua bản ghi cũ trong heap
        if (d_step, d_fuel) > (dist_step[u], dist_fuel[u]) :
            continue

        step_u, fuel_u = cost[u]

        for k, v in enumerate(adj[u]) :
            # Cách A: None xử lý chung cho cả mép map và ao
            if v is None :
                continue

            nd_step = d_step + step_u
            nd_fuel = d_fuel + fuel_u

            if (nd_step, nd_fuel) < (dist_step[v], dist_fuel[v]) :
                dist_step[v] = nd_step
                dist_fuel[v] = nd_fuel
                parent[v] = u
                parent_dir[v] = k
                heapq.heappush(pq, (nd_step, nd_fuel, v))

    return dist_step, dist_fuel, parent, parent_dir


def get_path(src, dst, parent, parent_dir) :
    """
    Dựng lại đường đi từ kết quả dijkstra(src, ...)
    Trả về (cells, directions):
        cells      : [src, ..., dst] các ô đi qua
        directions : list mã hướng API (0..5) để gửi lệnh di chuyển
    Trả về (None, None) nếu không tới được dst
    """
    if src == dst :
        return [src], []
    if parent[dst] == -1 :
        return None, None

    cells = [dst]
    directions = []
    v = dst
    while v != src :
        directions.append(parent_dir[v])
        v = parent[v]
        cells.append(v)

    cells.reverse()
    directions.reverse()
    return cells, directions


def evaluate_spot(
    spot: dict,
    dist_step: int,
    dist_fuel: int,
    visited_brands_all_time: set,
    visited_brands_today: set,
    visited_spots_today: set,
) -> float:
    """
    Tính điểm ưu tiên cho một điểm udon theo các tiêu chí xếp hạng của cuộc thi:
    1. Ưu tiên 1 (+10000): Loại udon (brand) chưa từng thu thập trong toàn bộ giải đấu.
    2. Ưu tiên 2 (+2000): Loại udon chưa thu thập trong ngày hôm nay.
    3. Ưu tiên 3 (+200): Thu thập thêm phần udon (chưa ghé spot này trong ngày).
    4. Trừ điểm chi phí: Càng tốn ít step và fuel thì điểm càng cao.
    """
    pos = spot["pos"]
    brand = spot["brand"]
    stock = spot.get("stocks", 1)

    if stock <= 0 or pos in visited_spots_today:
        return -float("inf")

    score = 0.0

    # Tiêu chí 1: Brand chưa từng ăn
    if brand not in visited_brands_all_time:
        score += 10000.0

    # Tiêu chí 2: Brand chưa ăn trong ngày hôm nay
    if brand not in visited_brands_today:
        score += 2000.0

    # Tiêu chí 3: Tích lũy thêm phần udon
    score += 200.0

    # Trừ chi phí di chuyển (ưu tiên đường ngắn, tiết kiệm step và xăng)
    score -= dist_step * 2.0
    score -= dist_fuel * 1.0

    return score


def plan_patrol_agent_day(
    current_pos: int,
    current_fuel: int,
    day_steps: int,
    spots: list,
    adj: list,
    cost: list,
    visited_brands_all_time: set,
    visited_brands_today: set,
    visited_spots_today: set,
    has_companion_supply: bool = False,
) -> tuple:
    """
    Lập kế hoạch di chuyển tối ưu cho 1 xe tuần tra trong ngày.

    :return: (actions, final_pos, remaining_fuel)
    """
    curr = current_pos
    fuel = current_fuel
    remaining_steps = day_steps
    actions = []

    while True:
        # Chạy Dijkstra từ vị trí hiện tại đến mọi ô
        dist_step, dist_fuel, parent, parent_dir = dijkstra(curr, adj, cost)

        best_spot = None
        best_score = -float("inf")
        best_dirs = None

        for s in spots:
            t_pos = s["pos"]
            d_s = dist_step[t_pos]
            d_f = dist_fuel[t_pos]

            if d_s == INF or d_s > remaining_steps:
                continue

            # Nếu không có xe tiếp tế đi kèm, phải đảm bảo đủ xăng
            if not has_companion_supply and d_f > fuel:
                continue

            sc = evaluate_spot(
                spot=s,
                dist_step=d_s,
                dist_fuel=d_f,
                visited_brands_all_time=visited_brands_all_time,
                visited_brands_today=visited_brands_today,
                visited_spots_today=visited_spots_today,
            )

            if sc > best_score:
                _, dirs = get_path(curr, t_pos, parent, parent_dir)
                if dirs is not None:
                    best_score = sc
                    best_spot = s
                    best_dirs = dirs

        # Nếu không còn spot nào khả thi hoặc không đem lại điểm số
        if best_spot is None or best_score <= -1000:
            break

        # Thực hiện di chuyển đến best_spot
        actions.extend(best_dirs)
        remaining_steps -= dist_step[best_spot["pos"]]
        if not has_companion_supply:
            fuel -= dist_fuel[best_spot["pos"]]

        curr = best_spot["pos"]
        visited_spots_today.add(curr)
        visited_brands_today.add(best_spot["brand"])
        visited_brands_all_time.add(best_spot["brand"])

    # Bù số step còn lại trong ngày bằng lệnh CHỜ (âm)
    if remaining_steps > 0:
        actions.append(-remaining_steps)

    return actions, curr, fuel


def plan_move_towards(
    start_pos: int,
    target_pos: int,
    day_steps: int,
    adj: list,
    cost: list,
) -> tuple:
    """
    Điều khiển xe di chuyển về phía một ô đích (dùng cho xe tiếp tế đi hỗ trợ).
    Nếu đến đích mà còn dư step -> Chờ số step còn lại.
    Nếu không đủ step để đến tận nơi -> Đi xa nhất có thể dọc theo đường đi ngắn nhất.

    :return: (actions, final_pos)
    """
    if start_pos == target_pos:
        return [-day_steps], start_pos

    dist_step, _, parent, parent_dir = dijkstra(start_pos, adj, cost)
    _, directions = get_path(start_pos, target_pos, parent, parent_dir)

    if directions is None or len(directions) == 0:
        return [-day_steps], start_pos

    actions = []
    curr = start_pos
    steps_used = 0

    for d in directions:
        step_cost, _ = cost[curr]
        if steps_used + step_cost > day_steps:
            break
        actions.append(d)
        steps_used += step_cost
        curr = adj[curr][d]

    remaining_steps = day_steps - steps_used
    if remaining_steps > 0:
        actions.append(-remaining_steps)

    return actions, curr


def solve_daily_actions(
    map_config: dict,
    match_status: dict,
    game_state: dict = None,
) -> list:
    """
    Hàm tổng thể điều phối toàn bộ các Agent (tuần tra & tiếp tế) trong một ngày thi đấu.

    Tự động áp dụng:
    - Loại của từng xe (0: Tuần tra, 1: Tiếp tế)
    - Ghép cặp hỗ trợ nếu có xe tiếp tế
    - Tránh trùng lặp tiệm udon và tối đa hóa các loại udon thu thập được.

    :param map_config: Dữ liệu cấu hình bản đồ từ server
    :param match_status: Dữ liệu trạng thái ngày hôm nay từ server
    :param game_state: Trạng thái xuyên suốt giải đấu (lưu các loại udon đã ăn)
    :return: all_agents_actions (List mảng 2 chiều sẵn sàng nộp lên server)
    """
    if game_state is None:
        game_state = {}

    if "visited_brands_all_time" not in game_state:
        game_state["visited_brands_all_time"] = set()

    visited_brands_all_time = game_state["visited_brands_all_time"]
    visited_brands_today = set()
    visited_spots_today = set()

    map_info = map_config.get("map", {})
    width = map_info.get("width", 8)
    height = map_info.get("height", 8)
    cells = map_info.get("cells", [])
    terrain = flatten_cells(cells)
    spots = map_config.get("spots", [])

    day = match_status.get("day", 0)
    day_steps_list = map_config.get("daySteps", [50])
    day_steps = day_steps_list[day] if day < len(day_steps_list) else day_steps_list[-1]

    # Xây dựng đồ thị và cập nhật tình trạng giao thông ngày hôm nay
    adj = build_adj(terrain, width, height)
    cost = build_cost(terrain)
    traffics = match_status.get("traffics", [])
    if traffics:
        update_traffic(cost, traffics)

    agents = match_status.get("agents", [])
    num_agents = len(agents)

    # Khởi tạo kết quả cho từng xe
    all_agents_actions = [None] * num_agents
    final_positions = [None] * num_agents

    # Xác định danh sách xe tuần tra và xe tiếp tế
    patrol_indices = [i for i, a in enumerate(agents) if a.get("kind", 0) == 0]
    supply_indices = [i for i, a in enumerate(agents) if a.get("kind", 0) == 1]

    # KỊCH BẢN 1: CÓ GHÉP CẶP (Số xe tiếp tế tương đương xe tuần tra, ví dụ [0, 1, 0, 1])
    if len(supply_indices) > 0 and len(supply_indices) == len(patrol_indices):
        for p_idx, s_idx in zip(patrol_indices, supply_indices):
            p_agent = agents[p_idx]
            s_agent = agents[s_idx]

            # Nếu 2 xe đang ở cùng 1 ô -> Đi cùng nhau (xe tuần tra có vô hạn xăng)
            if p_agent["pos"] == s_agent["pos"]:
                p_actions, p_final, _ = plan_patrol_agent_day(
                    current_pos=p_agent["pos"],
                    current_fuel=p_agent.get("fuel", 20),
                    day_steps=day_steps,
                    spots=spots,
                    adj=adj,
                    cost=cost,
                    visited_brands_all_time=visited_brands_all_time,
                    visited_brands_today=visited_brands_today,
                    visited_spots_today=visited_spots_today,
                    has_companion_supply=True,
                )
                all_agents_actions[p_idx] = p_actions
                all_agents_actions[s_idx] = list(p_actions)  # Xe tiếp tế đi y hệt để giữ cùng ô
                final_positions[p_idx] = p_final
                final_positions[s_idx] = p_final
            else:
                # Nếu chưa ở cùng ô (như đầu ngày 1) -> Xe tuần tra đi theo xăng riêng, xe tiếp tế tiến lại gần
                p_actions, p_final, _ = plan_patrol_agent_day(
                    current_pos=p_agent["pos"],
                    current_fuel=p_agent.get("fuel", 20),
                    day_steps=day_steps,
                    spots=spots,
                    adj=adj,
                    cost=cost,
                    visited_brands_all_time=visited_brands_all_time,
                    visited_brands_today=visited_brands_today,
                    visited_spots_today=visited_spots_today,
                    has_companion_supply=False,
                )
                s_actions, s_final = plan_move_towards(
                    start_pos=s_agent["pos"],
                    target_pos=p_final,
                    day_steps=day_steps,
                    adj=adj,
                    cost=cost,
                )
                all_agents_actions[p_idx] = p_actions
                all_agents_actions[s_idx] = s_actions
                final_positions[p_idx] = p_final
                final_positions[s_idx] = s_final

    # KỊCH BẢN 2: 1 XE TIẾP TẾ DUY NHẤT (Ví dụ [0, 0, 0, 1]) HOẶC 100% TUẦN TRA ([0, 0, 0, 0])
    else:
        # Lập kế hoạch cho tất cả các xe tuần tra trước
        for p_idx in patrol_indices:
            p_agent = agents[p_idx]
            p_actions, p_final, _ = plan_patrol_agent_day(
                current_pos=p_agent["pos"],
                current_fuel=p_agent.get("fuel", 20),
                day_steps=day_steps,
                spots=spots,
                adj=adj,
                cost=cost,
                visited_brands_all_time=visited_brands_all_time,
                visited_brands_today=visited_brands_today,
                visited_spots_today=visited_spots_today,
                has_companion_supply=False,
            )
            all_agents_actions[p_idx] = p_actions
            final_positions[p_idx] = p_final

        # Xe tiếp tế (nếu có) sẽ đi hỗ trợ xe tuần tra đang có ít xăng nhất
        for s_idx in supply_indices:
            s_agent = agents[s_idx]
            # Tìm xe tuần tra có lượng xăng ít nhất
            target_patrol_idx = min(
                patrol_indices,
                key=lambda idx: agents[idx].get("fuel", 20),
                default=None,
            )
            if target_patrol_idx is not None:
                target_pos = final_positions[target_patrol_idx]
                s_actions, _ = plan_move_towards(
                    start_pos=s_agent["pos"],
                    target_pos=target_pos,
                    day_steps=day_steps,
                    adj=adj,
                    cost=cost,
                )
            else:
                s_actions = [-day_steps]

            all_agents_actions[s_idx] = s_actions

    # Đảm bảo mọi xe đều có danh sách hành động hợp lệ
    for i in range(num_agents):
        if all_agents_actions[i] is None:
            all_agents_actions[i] = [-day_steps]

    return all_agents_actions

