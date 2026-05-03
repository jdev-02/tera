from __future__ import annotations

import heapq
import math
from collections import deque
from dataclasses import dataclass
from itertools import count
from typing import Callable, Hashable, Iterable, Mapping, Sequence

Node = Hashable
Graph = Mapping[Node, Sequence[tuple[Node, float]]]
GridPoint = tuple[int, int]
Grid = Sequence[Sequence[float | int | None]]


@dataclass(frozen=True)
class RasterCostResult:
    distance: list[list[float]]
    predecessor: dict[GridPoint, GridPoint]
    sources: tuple[GridPoint, ...]


def reconstruct_path(
    predecessor: Mapping[Node, Node],
    start: Node,
    goal: Node,
) -> list[Node]:
    if start == goal:
        return [start]
    if goal not in predecessor:
        return []

    path = [goal]
    cursor = goal
    while cursor != start:
        cursor = predecessor[cursor]
        path.append(cursor)
    path.reverse()
    return path


def dijkstra(
    graph: Graph,
    start: Node,
    goal: Node | None = None,
) -> tuple[dict[Node, float], dict[Node, Node]]:
    distances: dict[Node, float] = {start: 0.0}
    predecessor: dict[Node, Node] = {}
    heap: list[tuple[float, int, Node]] = []
    tie = count()
    heapq.heappush(heap, (0.0, next(tie), start))

    while heap:
        current_cost, _index, node = heapq.heappop(heap)
        if current_cost > distances.get(node, math.inf):
            continue
        if goal is not None and node == goal:
            break
        for neighbor, edge_cost in graph.get(node, ()):
            if edge_cost < 0:
                raise ValueError("Dijkstra requires non-negative edge costs.")
            next_cost = current_cost + float(edge_cost)
            if next_cost < distances.get(neighbor, math.inf):
                distances[neighbor] = next_cost
                predecessor[neighbor] = node
                heapq.heappush(heap, (next_cost, next(tie), neighbor))

    return distances, predecessor


def astar(
    graph: Graph,
    start: Node,
    goal: Node,
    heuristic: Callable[[Node, Node], float] | None = None,
) -> tuple[list[Node], float]:
    estimate = heuristic or (lambda _node, _goal: 0.0)
    g_score: dict[Node, float] = {start: 0.0}
    predecessor: dict[Node, Node] = {}
    heap: list[tuple[float, int, Node]] = []
    tie = count()
    heapq.heappush(heap, (estimate(start, goal), next(tie), start))

    while heap:
        _f_score, _index, node = heapq.heappop(heap)
        if node == goal:
            return reconstruct_path(predecessor, start, goal), g_score[node]
        for neighbor, edge_cost in graph.get(node, ()):
            if edge_cost < 0:
                raise ValueError("A* requires non-negative edge costs.")
            tentative = g_score[node] + float(edge_cost)
            if tentative < g_score.get(neighbor, math.inf):
                predecessor[neighbor] = node
                g_score[neighbor] = tentative
                heapq.heappush(
                    heap,
                    (tentative + estimate(neighbor, goal), next(tie), neighbor),
                )

    return [], math.inf


def multi_source_dijkstra(
    graph: Graph,
    sources: Iterable[Node],
    goals: set[Node] | None = None,
) -> tuple[dict[Node, float], dict[Node, Node], Node | None]:
    distances: dict[Node, float] = {}
    predecessor: dict[Node, Node] = {}
    heap: list[tuple[float, int, Node]] = []
    tie = count()

    for source in sources:
        distances[source] = 0.0
        heapq.heappush(heap, (0.0, next(tie), source))

    reached_goal: Node | None = None
    while heap:
        current_cost, _index, node = heapq.heappop(heap)
        if current_cost > distances.get(node, math.inf):
            continue
        if goals and node in goals:
            reached_goal = node
            break
        for neighbor, edge_cost in graph.get(node, ()):
            if edge_cost < 0:
                raise ValueError("Dijkstra requires non-negative edge costs.")
            next_cost = current_cost + float(edge_cost)
            if next_cost < distances.get(neighbor, math.inf):
                distances[neighbor] = next_cost
                predecessor[neighbor] = node
                heapq.heappush(heap, (next_cost, next(tie), neighbor))

    return distances, predecessor, reached_goal


def path_cost(graph: Graph, path: Sequence[Node]) -> float:
    if len(path) < 2:
        return 0.0
    total = 0.0
    for left, right in zip(path, path[1:]):
        for neighbor, edge_cost in graph.get(left, ()):
            if neighbor == right:
                total += float(edge_cost)
                break
        else:
            return math.inf
    return total


def yens_k_shortest_paths(
    graph: Graph,
    start: Node,
    goal: Node,
    k: int,
    heuristic: Callable[[Node, Node], float] | None = None,
) -> list[tuple[list[Node], float]]:
    first_path, first_cost = astar(graph, start, goal, heuristic)
    if not first_path:
        return []

    accepted: list[tuple[list[Node], float]] = [(first_path, first_cost)]
    candidates: list[tuple[float, int, list[Node]]] = []
    tie = count()

    for kth in range(1, max(1, k)):
        previous_path = accepted[kth - 1][0]
        for spur_index in range(len(previous_path) - 1):
            spur_node = previous_path[spur_index]
            root_path = previous_path[: spur_index + 1]
            root_nodes = set(root_path[:-1])
            removed_edges: set[tuple[Node, Node]] = set()

            for path, _cost in accepted:
                if len(path) > spur_index and path[: spur_index + 1] == root_path:
                    removed_edges.add((path[spur_index], path[spur_index + 1]))

            def graph_view(node: Node) -> Sequence[tuple[Node, float]]:
                edges = []
                for neighbor, edge_cost in graph.get(node, ()):
                    if (node, neighbor) in removed_edges:
                        continue
                    if neighbor in root_nodes:
                        continue
                    edges.append((neighbor, edge_cost))
                return edges

            spur_graph: Graph = _GraphView(graph_view)
            spur_path, spur_cost = astar(spur_graph, spur_node, goal, heuristic)
            if not spur_path:
                continue
            total_path = root_path[:-1] + spur_path
            if any(total_path == path for path, _cost in accepted):
                continue
            total_cost = path_cost(graph, root_path) + spur_cost
            heapq.heappush(candidates, (total_cost, next(tie), total_path))

        if not candidates:
            break
        cost, _index, path = heapq.heappop(candidates)
        accepted.append((path, cost))

    return accepted[:k]


class _GraphView(Mapping[Node, Sequence[tuple[Node, float]]]):
    def __init__(self, getter: Callable[[Node], Sequence[tuple[Node, float]]]) -> None:
        self._getter = getter

    def __getitem__(self, key: Node) -> Sequence[tuple[Node, float]]:
        return self._getter(key)

    def __iter__(self):
        return iter(())

    def __len__(self) -> int:
        return 0

    def get(self, key: Node, default=None):  # type: ignore[override]
        return self._getter(key)


def raster_cost_distance(
    cost_grid: Grid,
    starts: Iterable[GridPoint],
    *,
    diagonal: bool = True,
) -> RasterCostResult:
    rows = len(cost_grid)
    cols = len(cost_grid[0]) if rows else 0
    distances = [[math.inf for _col in range(cols)] for _row in range(rows)]
    predecessor: dict[GridPoint, GridPoint] = {}
    heap: list[tuple[float, int, GridPoint]] = []
    tie = count()
    source_points = tuple(starts)

    for row, col in source_points:
        if _is_passable(cost_grid, row, col):
            distances[row][col] = 0.0
            heapq.heappush(heap, (0.0, next(tie), (row, col)))

    while heap:
        current_cost, _index, point = heapq.heappop(heap)
        row, col = point
        if current_cost > distances[row][col]:
            continue
        for neighbor in _grid_neighbors(row, col, rows, cols, diagonal=diagonal):
            nr, nc = neighbor
            if not _is_passable(cost_grid, nr, nc):
                continue
            step_distance = math.sqrt(2.0) if nr != row and nc != col else 1.0
            cell_cost = (float(cost_grid[row][col]) + float(cost_grid[nr][nc])) / 2.0
            next_cost = current_cost + cell_cost * step_distance
            if next_cost < distances[nr][nc]:
                distances[nr][nc] = next_cost
                predecessor[neighbor] = point
                heapq.heappush(heap, (next_cost, next(tie), neighbor))

    return RasterCostResult(distances, predecessor, source_points)


def backtrack_least_cost_path(
    result: RasterCostResult,
    target: GridPoint,
) -> list[GridPoint]:
    row, col = target
    if row < 0 or col < 0 or row >= len(result.distance) or col >= len(result.distance[row]):
        return []
    if not math.isfinite(result.distance[row][col]):
        return []

    path = [target]
    cursor = target
    while cursor not in result.sources:
        if cursor not in result.predecessor:
            return []
        cursor = result.predecessor[cursor]
        path.append(cursor)
    path.reverse()
    return path


def derive_terrain_layers(
    elevation_grid: Grid,
    *,
    cell_size_m: float,
) -> dict[str, list[list[float]]]:
    rows = len(elevation_grid)
    cols = len(elevation_grid[0]) if rows else 0
    slope = [[0.0 for _col in range(cols)] for _row in range(rows)]
    aspect = [[0.0 for _col in range(cols)] for _row in range(rows)]
    roughness = [[0.0 for _col in range(cols)] for _row in range(rows)]
    tpi = [[0.0 for _col in range(cols)] for _row in range(rows)]
    curvature = [[0.0 for _col in range(cols)] for _row in range(rows)]

    for row in range(rows):
        for col in range(cols):
            center = _safe_elevation(elevation_grid, row, col)
            left = _safe_elevation(elevation_grid, row, max(0, col - 1))
            right = _safe_elevation(elevation_grid, row, min(cols - 1, col + 1))
            up = _safe_elevation(elevation_grid, max(0, row - 1), col)
            down = _safe_elevation(elevation_grid, min(rows - 1, row + 1), col)
            dzdx = (right - left) / (2.0 * cell_size_m)
            dzdy = (down - up) / (2.0 * cell_size_m)
            slope[row][col] = math.degrees(math.atan(math.hypot(dzdx, dzdy)))
            aspect[row][col] = (math.degrees(math.atan2(dzdy, -dzdx)) + 360.0) % 360.0

            neighbors = [
                _safe_elevation(elevation_grid, nr, nc)
                for nr in range(max(0, row - 1), min(rows, row + 2))
                for nc in range(max(0, col - 1), min(cols, col + 2))
            ]
            roughness[row][col] = max(neighbors) - min(neighbors)
            tpi[row][col] = center - (sum(neighbors) / len(neighbors))
            curvature[row][col] = (left + right + up + down - 4.0 * center) / (
                cell_size_m**2
            )

    return {
        "slope_degrees": slope,
        "aspect_degrees": aspect,
        "roughness_m": roughness,
        "topographic_position_index_m": tpi,
        "curvature": curvature,
    }


def build_walking_cost_surface(
    slope_degrees: Grid,
    *,
    landcover_grid: Sequence[Sequence[str | int | None]] | None = None,
    hazard_mask: Sequence[Sequence[bool]] | None = None,
    max_slope_deg: float = 35.0,
) -> list[list[float]]:
    rows = len(slope_degrees)
    cols = len(slope_degrees[0]) if rows else 0
    costs = [[math.inf for _col in range(cols)] for _row in range(rows)]

    for row in range(rows):
        for col in range(cols):
            slope = float(slope_degrees[row][col] or 0)
            if hazard_mask and hazard_mask[row][col]:
                continue
            if slope > max_slope_deg:
                continue
            multiplier = 1.0 + (slope / 22.0) ** 2
            if landcover_grid:
                multiplier *= _landcover_multiplier(landcover_grid[row][col])
            costs[row][col] = multiplier
    return costs


def flow_direction_d8(elevation_grid: Grid, *, cell_size_m: float) -> list[list[GridPoint | None]]:
    rows = len(elevation_grid)
    cols = len(elevation_grid[0]) if rows else 0
    directions: list[list[GridPoint | None]] = [[None for _col in range(cols)] for _row in range(rows)]

    for row in range(rows):
        for col in range(cols):
            current = _safe_elevation(elevation_grid, row, col)
            best_drop = 0.0
            best_neighbor: GridPoint | None = None
            for nr, nc in _grid_neighbors(row, col, rows, cols, diagonal=True):
                distance = math.sqrt(2.0) * cell_size_m if nr != row and nc != col else cell_size_m
                drop = (current - _safe_elevation(elevation_grid, nr, nc)) / distance
                if drop > best_drop:
                    best_drop = drop
                    best_neighbor = (nr, nc)
            directions[row][col] = best_neighbor
    return directions


def flow_accumulation_d8(elevation_grid: Grid, *, cell_size_m: float) -> list[list[int]]:
    directions = flow_direction_d8(elevation_grid, cell_size_m=cell_size_m)
    rows = len(directions)
    cols = len(directions[0]) if rows else 0
    indegree = [[0 for _col in range(cols)] for _row in range(rows)]
    accumulation = [[1 for _col in range(cols)] for _row in range(rows)]

    for row in range(rows):
        for col in range(cols):
            downstream = directions[row][col]
            if downstream:
                indegree[downstream[0]][downstream[1]] += 1

    queue: deque[GridPoint] = deque(
        (row, col)
        for row in range(rows)
        for col in range(cols)
        if indegree[row][col] == 0
    )

    while queue:
        row, col = queue.popleft()
        downstream = directions[row][col]
        if downstream is None:
            continue
        dr, dc = downstream
        accumulation[dr][dc] += accumulation[row][col]
        indegree[dr][dc] -= 1
        if indegree[dr][dc] == 0:
            queue.append((dr, dc))

    return accumulation


def viewshed(
    elevation_grid: Grid,
    observer: GridPoint,
    *,
    cell_size_m: float,
    observer_height_m: float = 2.0,
    target_height_m: float = 1.5,
    max_radius_cells: int | None = None,
) -> list[list[bool]]:
    rows = len(elevation_grid)
    cols = len(elevation_grid[0]) if rows else 0
    visible = [[False for _col in range(cols)] for _row in range(rows)]
    observer_row, observer_col = observer
    observer_elev = _safe_elevation(elevation_grid, observer_row, observer_col) + observer_height_m

    for row in range(rows):
        for col in range(cols):
            radius = max(abs(row - observer_row), abs(col - observer_col))
            if max_radius_cells is not None and radius > max_radius_cells:
                continue
            visible[row][col] = _has_line_of_sight(
                elevation_grid,
                (observer_row, observer_col),
                (row, col),
                observer_elev,
                target_height_m,
            )
    return visible


def isochrone_masks(
    distance_grid: Sequence[Sequence[float]],
    thresholds: Sequence[float],
) -> dict[float, list[list[bool]]]:
    return {
        float(threshold): [
            [math.isfinite(value) and value <= threshold for value in row]
            for row in distance_grid
        ]
        for threshold in thresholds
    }


def radial_sar_sectors(
    center_lat: float,
    center_lon: float,
    radius_m: float,
    sector_count: int,
    *,
    start_bearing_deg: float = 0.0,
    arc_steps_per_sector: int = 8,
) -> dict[str, object]:
    if sector_count <= 0:
        raise ValueError("sector_count must be positive.")

    features = []
    width = 360.0 / sector_count
    for index in range(sector_count):
        start = start_bearing_deg + index * width
        end = start + width
        coordinates = [[center_lon, center_lat]]
        for step in range(arc_steps_per_sector + 1):
            bearing = start + (end - start) * (step / arc_steps_per_sector)
            lat, lon = _destination_point(center_lat, center_lon, bearing, radius_m)
            coordinates.append([lon, lat])
        coordinates.append([center_lon, center_lat])
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "sector": index + 1,
                    "bearing_start_deg": start % 360.0,
                    "bearing_end_deg": end % 360.0,
                    "radius_m": radius_m,
                },
                "geometry": {"type": "Polygon", "coordinates": [coordinates]},
            }
        )

    return {"type": "FeatureCollection", "features": features}


def sar_probability_surface(
    rows: int,
    cols: int,
    last_known: GridPoint,
    *,
    sigma_cells: float = 6.0,
    travel_cost: Sequence[Sequence[float]] | None = None,
    attraction_points: Sequence[GridPoint] | None = None,
) -> list[list[float]]:
    if rows <= 0 or cols <= 0:
        return []

    lk_row, lk_col = last_known
    attraction_points = attraction_points or ()
    probabilities = [[0.0 for _col in range(cols)] for _row in range(rows)]
    total = 0.0

    for row in range(rows):
        for col in range(cols):
            distance_cells = math.hypot(row - lk_row, col - lk_col)
            probability = math.exp(-(distance_cells**2) / (2.0 * sigma_cells**2))
            if travel_cost:
                cost = travel_cost[row][col]
                probability *= 0.0 if not math.isfinite(cost) else 1.0 / (1.0 + cost)
            for point in attraction_points:
                probability += 0.25 * math.exp(
                    -(math.hypot(row - point[0], col - point[1]) ** 2)
                    / (2.0 * (sigma_cells / 2.0) ** 2)
                )
            probabilities[row][col] = probability
            total += probability

    if total <= 0:
        return probabilities
    return [[value / total for value in row] for row in probabilities]


def score_route(
    *,
    normalized_time: float,
    normalized_energy: float,
    hazard_exposure: float,
    data_uncertainty: float,
    resource_value: float = 0.0,
    rescue_visibility: float = 0.0,
    weights: Mapping[str, float] | None = None,
) -> float:
    route_weights = {
        "time": 0.25,
        "energy": 0.2,
        "risk": 0.35,
        "uncertainty": 0.15,
        "resource": 0.03,
        "rescue": 0.02,
    }
    if weights:
        route_weights.update(weights)
    return (
        route_weights["time"] * normalized_time
        + route_weights["energy"] * normalized_energy
        + route_weights["risk"] * hazard_exposure
        + route_weights["uncertainty"] * data_uncertainty
        - route_weights["resource"] * resource_value
        - route_weights["rescue"] * rescue_visibility
    )


def algorithm_catalog() -> list[dict[str, object]]:
    return [
        {
            "id": "graph_dijkstra",
            "purpose": "Default shortest path on local road/trail graph.",
            "inputs": ["GeoPackage/SQLite graph edges", "edge_cost"],
            "outputs": ["least_cost_path", "distance_or_time"],
        },
        {
            "id": "graph_astar",
            "purpose": "Goal-directed graph routing with admissible distance heuristic.",
            "inputs": ["graph edges", "node coordinates", "heuristic"],
            "outputs": ["least_cost_path", "route_cost"],
        },
        {
            "id": "multi_source_dijkstra",
            "purpose": "Nearest target among water, shelter, road, trail, or signal candidates.",
            "inputs": ["graph edges", "candidate node set"],
            "outputs": ["nearest_candidate", "access_path"],
        },
        {
            "id": "yen_k_shortest_paths",
            "purpose": "Fastest, safest, and easiest alternatives when graph routes differ.",
            "inputs": ["graph edges", "source/destination", "k"],
            "outputs": ["ranked_route_alternatives"],
        },
        {
            "id": "raster_cost_distance",
            "purpose": "Off-road and hybrid movement over slope/landcover/hazard cost rasters.",
            "inputs": ["COG cost raster", "start cells"],
            "outputs": ["cumulative_cost_raster", "predecessor_grid"],
        },
        {
            "id": "least_cost_backtrack",
            "purpose": "Recover least-cost route geometry from cumulative raster output.",
            "inputs": ["cumulative_cost_raster", "predecessor_grid", "target cell"],
            "outputs": ["least_cost_cell_path"],
        },
        {
            "id": "terrain_derivatives",
            "purpose": "Generate slope, aspect, roughness, and TPI from Esri/DEM COGs.",
            "inputs": ["DEM COG"],
            "outputs": ["slope_degrees", "aspect_degrees", "roughness", "tpi", "curvature"],
        },
        {
            "id": "flow_accumulation_d8",
            "purpose": "Drainage and likely water reasoning from DEM cells.",
            "inputs": ["DEM COG"],
            "outputs": ["flow_direction", "flow_accumulation"],
        },
        {
            "id": "viewshed",
            "purpose": "Line-of-sight, signal, open-sky, and observation checks.",
            "inputs": ["DEM COG", "observer cell", "antenna heights"],
            "outputs": ["visible_cell_mask"],
        },
        {
            "id": "isochrone_masks",
            "purpose": "Reachable area masks from travel-time or cost surfaces.",
            "inputs": ["cumulative_cost_raster", "thresholds"],
            "outputs": ["reachable_area_masks"],
        },
        {
            "id": "sar_sector_partition",
            "purpose": "Radial SAR sectors for hasty search planning.",
            "inputs": ["center", "radius", "sector_count"],
            "outputs": ["GeoJSON sector polygons"],
        },
        {
            "id": "sar_probability_surface",
            "purpose": "Normalized probability-of-area grid from last known position and travel cost.",
            "inputs": ["last_known_cell", "sigma", "travel_cost", "attraction_points"],
            "outputs": ["probability_grid"],
        },
        {
            "id": "route_score",
            "purpose": "Separate time, energy, risk, uncertainty, resource, and rescue visibility scoring.",
            "inputs": ["route metrics", "mission weights"],
            "outputs": ["comparable route score"],
        },
    ]


def _grid_neighbors(
    row: int,
    col: int,
    rows: int,
    cols: int,
    *,
    diagonal: bool,
) -> Iterable[GridPoint]:
    offsets = (
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
    )
    if diagonal:
        offsets = (
            *offsets,
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        )
    for dr, dc in offsets:
        nr = row + dr
        nc = col + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            yield nr, nc


def _is_passable(grid: Grid, row: int, col: int) -> bool:
    value = grid[row][col]
    return value is not None and math.isfinite(float(value)) and float(value) > 0


def _safe_elevation(grid: Grid, row: int, col: int) -> float:
    value = grid[row][col]
    if value is None:
        return 0.0
    return float(value)


def _landcover_multiplier(value: str | int | None) -> float:
    lookup = {
        "road": 0.5,
        "trail": 0.6,
        "open": 1.0,
        "grass": 1.0,
        "shrub": 1.4,
        "forest": 1.6,
        "dense_brush": 2.8,
        "wetland": 4.5,
        "water": math.inf,
        11: math.inf,
        21: 0.8,
        41: 1.6,
        42: 1.6,
        43: 1.7,
        52: 1.4,
        90: 4.5,
        95: 4.5,
    }
    return float(lookup.get(value, 1.2))


def _has_line_of_sight(
    elevation_grid: Grid,
    observer: GridPoint,
    target: GridPoint,
    observer_elev: float,
    target_height_m: float,
) -> bool:
    if observer == target:
        return True

    start_row, start_col = observer
    target_row, target_col = target
    target_elev = _safe_elevation(elevation_grid, target_row, target_col) + target_height_m
    steps = max(abs(target_row - start_row), abs(target_col - start_col))

    for step in range(1, steps):
        fraction = step / steps
        row = round(start_row + (target_row - start_row) * fraction)
        col = round(start_col + (target_col - start_col) * fraction)
        terrain_elev = _safe_elevation(elevation_grid, row, col)
        line_elev = observer_elev + (target_elev - observer_elev) * fraction
        if terrain_elev > line_elev:
            return False
    return True


def _destination_point(
    lat: float,
    lon: float,
    bearing_deg: float,
    distance_m: float,
) -> tuple[float, float]:
    radius_m = 6_371_000.0
    bearing = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    angular = distance_m / radius_m
    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular)
        + math.cos(lat1) * math.sin(angular) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular) * math.cos(lat1),
        math.cos(angular) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), ((math.degrees(lon2) + 540.0) % 360.0) - 180.0
