"""Orquestra o despacho multi-veiculo: busca pedidos elegiveis do lote
inteiro (sem travar por eixo), veiculos ativos, cidades e distancias
cacheadas, roda o VRP, e persiste o resultado."""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from app.optimizer.vrp_solver import DispatchResult, VrpOrder, VrpVehicle, solve_dispatch
from app.services.parsing import normalize_city_key


class DispatchError(Exception):
    pass


def _reserved_order_ids(client: Client, org_id: str) -> set[str]:
    rows = client.table("reservations").select("order_id").eq("org_id", org_id).eq("status", "active").execute().data
    return {r["order_id"] for r in rows}


def build_dispatch(client: Client, *, org_id: str, user_id: str, batch_id: str) -> dict:
    all_cities = client.table("cities").select("*").eq("org_id", org_id).execute().data
    cities = [c for c in all_cities if c["lat"] is not None and c["lng"] is not None]
    if not cities:
        raise DispatchError("Nenhuma cidade com coordenada marcada no mapa ainda. Cadastre em Cadastros → Eixos e cidades.")
    depot = next((c for c in cities if c["is_depot"]), None)
    if depot is None:
        raise DispatchError("Nenhuma cidade com coordenada está marcada como depósito (ex.: Crateús).")

    city_by_name = {normalize_city_key(c["name"]): c for c in cities}

    dist_rows = client.table("city_distances").select("from_city_id, to_city_id, distance_km").eq("org_id", org_id).execute().data
    if not dist_rows:
        raise DispatchError("Matriz de distância vazia. Rode POST /cities/distances/rebuild antes de despachar.")
    distance_km = {(r["from_city_id"], r["to_city_id"]): float(r["distance_km"]) for r in dist_rows}

    vehicles_rows = client.table("vehicles").select("*").eq("org_id", org_id).eq("active", True).execute().data
    if not vehicles_rows:
        raise DispatchError("Nenhum veículo ativo cadastrado.")

    # so pedido ainda nao entregue entra como candidato — nao faz sentido despachar
    # algo que ja saiu.
    orders_rows = (
        client.table("orders")
        .select("id, external_id, city, value, weight_kg, volume_m3, delivered")
        .eq("org_id", org_id)
        .eq("batch_id", batch_id)
        .eq("data_status", "ready")
        .eq("delivered", False)
        .execute()
        .data
    )

    reserved = _reserved_order_ids(client, org_id)
    orders_rows = [o for o in orders_rows if o["id"] not in reserved]

    orders_by_id = {}
    vrp_orders: list[VrpOrder] = []
    skipped_no_city: list[str] = []
    for o in orders_rows:
        city = city_by_name.get(normalize_city_key(o["city"]))
        if city is None:
            skipped_no_city.append(o["id"])
            continue
        orders_by_id[o["id"]] = o
        vrp_orders.append(
            VrpOrder(id=o["id"], city_id=city["id"], weight_kg=float(o["weight_kg"]), volume_m3=float(o["volume_m3"]), value=float(o["value"] or 0))
        )

    vrp_vehicles = [VrpVehicle(id=v["id"], capacity_kg=float(v["capacity_kg"]), capacity_m3=float(v["capacity_m3"])) for v in vehicles_rows]

    result: DispatchResult = solve_dispatch(orders=vrp_orders, vehicles=vrp_vehicles, depot_city_id=depot["id"], distance_km=distance_km)

    run_row = (
        client.table("dispatch_runs")
        .insert(
            {
                "org_id": org_id,
                "batch_id": batch_id,
                "mode": "operacao",
                "status": "draft",
                "solver_status": result.status,
                "solver_wall_time_ms": result.wall_time_ms,
                "total_distance_km": result.total_distance_km,
                "total_value": sum(float(orders_by_id[s.order_id]["value"] or 0) for r in result.routes for s in r.stops),
                "created_by": user_id,
            }
        )
        .execute()
        .data[0]
    )

    assignment_rows = []
    for route in result.routes:
        for i, stop in enumerate(route.stops, start=1):
            order = orders_by_id[stop.order_id]
            assignment_rows.append(
                {
                    "org_id": org_id,
                    "dispatch_run_id": run_row["id"],
                    "order_id": stop.order_id,
                    "vehicle_id": route.vehicle_id,
                    "city": order["city"],
                    "stop_sequence": i,
                    "leg_distance_km": stop.leg_distance_km,
                    "value": order["value"],
                    "weight_kg": order["weight_kg"],
                    "volume_m3": order["volume_m3"],
                    "selected": True,
                }
            )
    for order_id, reason in result.dropped:
        order = orders_by_id[order_id]
        assignment_rows.append(
            {
                "org_id": org_id,
                "dispatch_run_id": run_row["id"],
                "order_id": order_id,
                "vehicle_id": None,
                "city": order["city"],
                "stop_sequence": None,
                "value": order["value"],
                "weight_kg": order["weight_kg"],
                "volume_m3": order["volume_m3"],
                "selected": False,
                "rejection_reason": reason,
            }
        )
    for order_id in skipped_no_city:
        order = orders_by_id.get(order_id) or next(o for o in orders_rows if o["id"] == order_id)
        assignment_rows.append(
            {
                "org_id": org_id,
                "dispatch_run_id": run_row["id"],
                "order_id": order_id,
                "vehicle_id": None,
                "city": order["city"],
                "stop_sequence": None,
                "value": order["value"],
                "weight_kg": order["weight_kg"],
                "volume_m3": order["volume_m3"],
                "selected": False,
                "rejection_reason": "cidade_sem_coordenada_cadastrada",
            }
        )

    if assignment_rows:
        client.table("dispatch_assignments").insert(assignment_rows).execute()

    return {
        "dispatch_run": run_row,
        "routes": len(result.routes),
        "orders_served": sum(len(r.stops) for r in result.routes),
        "orders_dropped": len(result.dropped) + len(skipped_no_city),
        "total_distance_km": result.total_distance_km,
    }


def cancel_dispatch(client: Client, *, org_id: str, dispatch_run_id: str) -> dict:
    client.table("reservations").update(
        {"status": "released", "released_at": datetime.now(timezone.utc).isoformat()}
    ).eq("dispatch_run_id", dispatch_run_id).eq("status", "active").execute()

    return (
        client.table("dispatch_runs")
        .update({"status": "cancelled"})
        .eq("id", dispatch_run_id)
        .execute()
        .data[0]
    )


def issue_dispatch(client: Client, *, org_id: str, dispatch_run_id: str) -> dict:
    run = client.table("dispatch_runs").select("*").eq("id", dispatch_run_id).single().execute().data
    if run["status"] != "draft":
        raise DispatchError(f"Rodada está '{run['status']}', só um rascunho pode ser emitido.")

    selected = (
        client.table("dispatch_assignments")
        .select("order_id, vehicle_id")
        .eq("dispatch_run_id", dispatch_run_id)
        .eq("selected", True)
        .execute()
        .data
    )
    if not selected:
        raise DispatchError("Nenhum pedido servido nesta rodada; nada para reservar.")

    reservation_rows = [
        {"org_id": org_id, "order_id": s["order_id"], "dispatch_run_id": dispatch_run_id, "status": "active"}
        for s in selected
    ]
    try:
        client.table("reservations").insert(reservation_rows).execute()
    except Exception as exc:  # noqa: BLE001
        raise DispatchError("Um ou mais pedidos já foram reservados por outro plano. Recalcule antes de emitir.") from exc

    return (
        client.table("dispatch_runs")
        .update({"status": "issued", "issued_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", dispatch_run_id)
        .execute()
        .data[0]
    )
