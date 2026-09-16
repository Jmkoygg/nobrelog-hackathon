"""Monta, emite e cancela planos de carga (romaneio).

Ponto central: o snapshot gravado no plano no momento da emissao e o que
sera impresso para sempre. Editar veiculo/produto depois nao reescreve um
romaneio ja emitido — e por isso guardamos versao de cada cadastro usado
e o snapshot inteiro em `plans.snapshot`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from app.optimizer.solver import OrderInput, SolveResult, solve_axis_vehicle
from app.services.parsing import normalize_city_key


class PlanConflictError(Exception):
    """Pedido ja reservado em outro plano ativo, ou entrada mudou desde o calculo."""


def _active_reserved_order_ids(client: Client, org_id: str) -> set[str]:
    rows = (
        client.table("reservations")
        .select("order_id")
        .eq("org_id", org_id)
        .eq("status", "active")
        .execute()
        .data
    )
    return {r["order_id"] for r in rows}


def eligible_orders(client: Client, *, org_id: str, axis_id: str, batch_id: str, mode: str) -> list[dict]:
    query = (
        client.table("orders")
        .select("id, external_id, city, value, weight_kg, volume_m3, delivered")
        .eq("org_id", org_id)
        .eq("axis_id", axis_id)
        .eq("batch_id", batch_id)
        .eq("data_status", "ready")
    )
    if mode == "operacao":
        query = query.eq("delivered", False)
    orders = query.execute().data

    reserved = _active_reserved_order_ids(client, org_id)
    return [o for o in orders if o["id"] not in reserved]


def build_draft_plan(
    client: Client,
    *,
    org_id: str,
    user_id: str,
    axis_id: str,
    vehicle_id: str,
    batch_id: str,
    mode: str,
    policy_name: str,
) -> dict:
    vehicle = client.table("vehicles").select("*").eq("id", vehicle_id).single().execute().data
    orders = eligible_orders(client, org_id=org_id, axis_id=axis_id, batch_id=batch_id, mode=mode)

    solve_input = [
        OrderInput(id=o["id"], weight_kg=float(o["weight_kg"]), volume_m3=float(o["volume_m3"]), value=float(o["value"] or 0))
        for o in orders
    ]
    result: SolveResult = solve_axis_vehicle(
        solve_input,
        capacity_kg=float(vehicle["capacity_kg"]),
        capacity_m3=float(vehicle["capacity_m3"]),
        policy_name=policy_name,
    )

    orders_by_id = {o["id"]: o for o in orders}
    stop_sequence = _resolve_stop_sequence(client, org_id=org_id, axis_id=axis_id, selected_orders=[
        orders_by_id[oid] for oid in result.selected_ids
    ])

    plan_row = (
        client.table("plans")
        .insert(
            {
                "org_id": org_id,
                "axis_id": axis_id,
                "vehicle_id": vehicle_id,
                "batch_id": batch_id,
                "mode": mode,
                "status": "draft",
                "objective_policy": policy_name,
                "solver_status": result.status,
                "solver_wall_time_ms": result.wall_time_ms,
                "solver_seed": result.seed,
                "solver_workers": result.workers,
                "input_versions": {"vehicle_id": vehicle_id, "vehicle_version": vehicle["version"]},
                "snapshot": {
                    "vehicle": vehicle,
                    "validated": result.validated,
                    "validation_errors": result.validation_errors,
                },
                "total_weight_kg": str(result.total_weight_kg),
                "total_volume_m3": str(result.total_volume_m3),
                "total_value": str(result.total_value),
                "created_by": user_id,
            }
        )
        .execute()
        .data[0]
    )

    plan_order_rows = []
    for order_result in result.order_results:
        order = orders_by_id.get(order_result.id)
        if order is None:
            continue
        plan_order_rows.append(
            {
                "org_id": org_id,
                "plan_id": plan_row["id"],
                "order_id": order_result.id,
                "selected": order_result.selected,
                "rejection_reason": order_result.reason,
                "city": order["city"],
                "stop_sequence": stop_sequence.get(order_result.id),
                "value": order["value"],
                "weight_kg": order["weight_kg"],
                "volume_m3": order["volume_m3"],
            }
        )
    if plan_order_rows:
        client.table("plan_orders").insert(plan_order_rows).execute()

    return {
        "plan": plan_row,
        "solver_status": result.status,
        "validated": result.validated,
        "validation_errors": result.validation_errors,
        "occupancy_kg_pct": result.occupancy_kg_pct,
        "occupancy_m3_pct": result.occupancy_m3_pct,
        "selected_count": len(result.selected_ids),
        "candidate_count": len(orders),
    }


def _resolve_stop_sequence(client: Client, *, org_id: str, axis_id: str, selected_orders: list[dict]) -> dict[str, int]:
    cities = (
        client.table("cities")
        .select("name, sort_order")
        .eq("org_id", org_id)
        .eq("axis_id", axis_id)
        .order("sort_order")
        .execute()
        .data
    )
    order_in_route = {normalize_city_key(c["name"]): i for i, c in enumerate(cities)}
    ranked = sorted(
        selected_orders,
        key=lambda o: (order_in_route.get(normalize_city_key(o["city"]), len(order_in_route)), o["external_id"]),
    )
    return {o["id"]: i + 1 for i, o in enumerate(ranked)}


def issue_plan(client: Client, *, org_id: str, plan_id: str) -> dict:
    plan = client.table("plans").select("*").eq("id", plan_id).single().execute().data
    if plan["status"] != "draft":
        raise PlanConflictError(f"Plano esta '{plan['status']}', so um rascunho pode ser emitido.")

    vehicle = client.table("vehicles").select("id, version").eq("id", plan["vehicle_id"]).single().execute().data
    expected_version = plan["input_versions"].get("vehicle_version")
    if vehicle["version"] != expected_version:
        raise PlanConflictError(
            "A ficha do veiculo mudou desde o calculo deste plano. Recalcule antes de emitir."
        )

    selected = (
        client.table("plan_orders")
        .select("order_id")
        .eq("plan_id", plan_id)
        .eq("selected", True)
        .execute()
        .data
    )
    if not selected:
        raise PlanConflictError("Nenhum pedido selecionado neste plano; nada para reservar/emitir.")

    reservation_rows = [
        {"org_id": org_id, "order_id": s["order_id"], "plan_id": plan_id, "status": "active"}
        for s in selected
    ]
    try:
        client.table("reservations").insert(reservation_rows).execute()
    except Exception as exc:  # a unique violation do Postgres vira excecao aqui
        raise PlanConflictError(
            "Um ou mais pedidos deste plano ja foram reservados por outro plano ativo. "
            "Recalcule a carga antes de emitir."
        ) from exc

    updated = (
        client.table("plans")
        .update({"status": "issued", "issued_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", plan_id)
        .execute()
        .data[0]
    )
    return updated


def cancel_plan(client: Client, *, org_id: str, plan_id: str) -> dict:
    client.table("reservations").update(
        {"status": "released", "released_at": datetime.now(timezone.utc).isoformat()}
    ).eq("plan_id", plan_id).eq("status", "active").execute()

    return (
        client.table("plans")
        .update({"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", plan_id)
        .execute()
        .data[0]
    )
