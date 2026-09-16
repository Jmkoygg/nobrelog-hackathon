from app.optimizer.vrp_solver import VrpOrder, VrpVehicle, solve_dispatch

DEPOT = "crateus"
CITY_A = "ipaporanga"
CITY_B = "poranga"
CITY_C = "ararenda"

# grade simples: depot no centro, 3 cidades a 50, 80 e 120 km, e entre elas
# distancias curtas (formando um "V" plausivel de estrada real).
DIST = {
    (DEPOT, CITY_A): 50, (CITY_A, DEPOT): 50,
    (DEPOT, CITY_B): 80, (CITY_B, DEPOT): 80,
    (DEPOT, CITY_C): 120, (CITY_C, DEPOT): 120,
    (CITY_A, CITY_B): 35, (CITY_B, CITY_A): 35,
    (CITY_A, CITY_C): 75, (CITY_C, CITY_A): 75,
    (CITY_B, CITY_C): 45, (CITY_C, CITY_B): 45,
}


def test_all_orders_served_when_capacity_allows():
    orders = [
        VrpOrder(id="o1", city_id=CITY_A, weight_kg=300, volume_m3=0.3, value=1000),
        VrpOrder(id="o2", city_id=CITY_B, weight_kg=400, volume_m3=0.4, value=1500),
        VrpOrder(id="o3", city_id=CITY_C, weight_kg=200, volume_m3=0.2, value=800),
    ]
    vehicles = [VrpVehicle(id="v1", capacity_kg=2000, capacity_m3=3.0)]

    result = solve_dispatch(orders=orders, vehicles=vehicles, depot_city_id=DEPOT, distance_km=DIST, time_limit_seconds=5)

    assert result.status == "solved"
    assert result.dropped == []
    served = {s.order_id for r in result.routes for s in r.stops}
    assert served == {"o1", "o2", "o3"}
    assert result.total_distance_km > 0


def test_drops_lowest_value_when_capacity_is_tight():
    # so cabe 1 dos 2 pedidos (kg). O de menor valor deve ser descartado.
    orders = [
        VrpOrder(id="caro", city_id=CITY_A, weight_kg=900, volume_m3=0.5, value=5000),
        VrpOrder(id="barato", city_id=CITY_B, weight_kg=900, volume_m3=0.5, value=100),
    ]
    vehicles = [VrpVehicle(id="v1", capacity_kg=1000, capacity_m3=3.0)]

    result = solve_dispatch(orders=orders, vehicles=vehicles, depot_city_id=DEPOT, distance_km=DIST, time_limit_seconds=5)

    served = {s.order_id for r in result.routes for s in r.stops}
    assert served == {"caro"}
    assert result.dropped[0][0] == "barato"


def test_splits_across_multiple_vehicles_when_one_is_not_enough():
    orders = [
        VrpOrder(id="o1", city_id=CITY_A, weight_kg=900, volume_m3=0.5, value=1000),
        VrpOrder(id="o2", city_id=CITY_B, weight_kg=900, volume_m3=0.5, value=1000),
    ]
    vehicles = [
        VrpVehicle(id="v1", capacity_kg=1000, capacity_m3=3.0),
        VrpVehicle(id="v2", capacity_kg=1000, capacity_m3=3.0),
    ]

    result = solve_dispatch(orders=orders, vehicles=vehicles, depot_city_id=DEPOT, distance_km=DIST, time_limit_seconds=5)

    served = {s.order_id for r in result.routes for s in r.stops}
    assert served == {"o1", "o2"}
    assert result.dropped == []
    used_vehicles = {r.vehicle_id for r in result.routes if r.stops}
    assert len(used_vehicles) == 2


def test_no_orders_returns_no_orders_status():
    result = solve_dispatch(orders=[], vehicles=[VrpVehicle(id="v1", capacity_kg=1000, capacity_m3=3.0)], depot_city_id=DEPOT, distance_km=DIST)
    assert result.status == "no_orders"
