"""Motor de despacho multi-veiculo: decide, ao mesmo tempo, quais pedidos
entram, em qual caminhao, e em que ordem de visita — usando distancia real
de estrada (matriz cacheada do OSRM) em vez de eixo fixo.

Diferenca deliberada de politica em relacao ao solver.py (mochila de um
veiculo/um eixo): ali o criterio padrao e' ocupacao (kg+m3); aqui, como a
decisao de "quem fica de fora" e' por pedido individual dentro de uma rota
inteira, o criterio de prioridade quando falta capacidade para todos e'
valor comercial do pedido — mais facil de justificar numa rotina com N
veiculos e paradas do que ocupacao agregada. Vale o time validar esse
criterio; trocar so muda o calculo do "penalty" abaixo, nao a estrutura.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

_KG_TO_G = 1000
_M3_TO_CM3 = 1_000_000
_REAIS_TO_CENTS = 100
_KM_TO_M = 1000


@dataclass
class VrpOrder:
    id: str
    city_id: str
    weight_kg: float
    volume_m3: float
    value: float


@dataclass
class VrpVehicle:
    id: str
    capacity_kg: float
    capacity_m3: float


@dataclass
class RouteStop:
    order_id: str
    city_id: str
    leg_distance_km: float


@dataclass
class VehicleRoute:
    vehicle_id: str
    stops: list[RouteStop] = field(default_factory=list)
    total_distance_km: float = 0.0


@dataclass
class DispatchResult:
    status: str  # "solved" | "no_solution" | "no_orders"
    routes: list[VehicleRoute] = field(default_factory=list)
    dropped: list[tuple[str, str]] = field(default_factory=list)  # (order_id, motivo)
    total_distance_km: float = 0.0
    wall_time_ms: int = 0


def solve_dispatch(
    *,
    orders: list[VrpOrder],
    vehicles: list[VrpVehicle],
    depot_city_id: str,
    distance_km: dict[tuple[str, str], float],
    time_limit_seconds: int = 20,
) -> DispatchResult:
    if not orders:
        return DispatchResult(status="no_orders")
    if not vehicles:
        return DispatchResult(status="no_solution")

    # nó 0 = depósito; nós 1..N = pedidos (uma cidade pode ter vários nós,
    # um por pedido — a distância entre eles é ~0, o que é correto).
    node_city = [depot_city_id] + [o.city_id for o in orders]
    num_nodes = len(node_city)

    def dist_m(city_a: str, city_b: str) -> int:
        if city_a == city_b:
            return 0
        km = distance_km.get((city_a, city_b))
        if km is None:
            # par sem distancia cacheada: penaliza pesado em vez de quebrar
            # o solver, e sinaliza no log — indica que falta rodar o
            # rebuild da matriz para essas cidades.
            return 10_000_000
        return round(km * _KM_TO_M)

    manager = pywrapcp.RoutingIndexManager(num_nodes, len(vehicles), 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return dist_m(node_city[from_node], node_city[to_node])

    transit_idx = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    weights_g = [0] + [round(o.weight_kg * _KG_TO_G) for o in orders]
    volumes_cm3 = [0] + [round(o.volume_m3 * _M3_TO_CM3) for o in orders]

    def weight_callback(from_index):
        return weights_g[manager.IndexToNode(from_index)]

    def volume_callback(from_index):
        return volumes_cm3[manager.IndexToNode(from_index)]

    weight_cb_idx = routing.RegisterUnaryTransitCallback(weight_callback)
    routing.AddDimensionWithVehicleCapacity(
        weight_cb_idx, 0, [round(v.capacity_kg * _KG_TO_G) for v in vehicles], True, "Weight"
    )

    volume_cb_idx = routing.RegisterUnaryTransitCallback(volume_callback)
    routing.AddDimensionWithVehicleCapacity(
        volume_cb_idx, 0, [round(v.capacity_m3 * _M3_TO_CM3) for v in vehicles], True, "Volume"
    )

    # pedido pode ficar de fora, mas custa caro (valor do pedido) — so vale
    # a pena descartar quando a capacidade de fato nao permite incluir.
    for i, order in enumerate(orders):
        node_index = manager.NodeToIndex(i + 1)
        penalty = round(order.value * _REAIS_TO_CENTS) * 1000
        routing.AddDisjunction([node_index], penalty)

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_params.time_limit.FromSeconds(time_limit_seconds)

    solution = routing.SolveWithParameters(search_params)
    wall_time_ms = routing.solver().WallTime()

    if solution is None:
        return DispatchResult(status="no_solution", wall_time_ms=wall_time_ms)

    routes: list[VehicleRoute] = []
    visited_nodes: set[int] = set()
    total_distance_km = 0.0

    for v_idx, vehicle in enumerate(vehicles):
        index = routing.Start(v_idx)
        route = VehicleRoute(vehicle_id=vehicle.id)
        prev_node = manager.IndexToNode(index)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != 0:
                visited_nodes.add(node)
                order = orders[node - 1]
                leg_km = dist_m(node_city[prev_node], node_city[node]) / _KM_TO_M
                route.stops.append(RouteStop(order_id=order.id, city_id=order.city_id, leg_distance_km=leg_km))
                route.total_distance_km += leg_km
            prev_node = node
            index = solution.Value(routing.NextVar(index))
        if route.stops:
            routes.append(route)
            total_distance_km += route.total_distance_km

    dropped = [
        (orders[node - 1].id, "sem_capacidade_disponivel_na_frota")
        for node in range(1, num_nodes)
        if node not in visited_nodes
    ]

    return DispatchResult(
        status="solved",
        routes=routes,
        dropped=dropped,
        total_distance_km=round(total_distance_km, 2),
        wall_time_ms=wall_time_ms,
    )
