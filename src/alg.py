import heapq
from terrain import Plain, Mountain, Road, Pond

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
