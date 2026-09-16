"""Emite e cancela planos de carga (romaneio) ja existentes.

Planos novos nao sao mais criados por este servico — a montagem de carga
foi unificada no despacho multi-veiculo (`app.services.dispatch`), que
substitui o fluxo antigo de "eixo + veiculo fixos". O que resta aqui e'
so o ciclo de vida de planos ja emitidos no passado: emitir/cancelar um
rascunho existente, e servir o snapshot pra reimpressao (nunca reescrito
depois de emitido — por isso a versao de cada cadastro usado fica
guardada em `plans.snapshot`).
"""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client


class PlanConflictError(Exception):
    """Pedido ja reservado em outro plano ativo, ou entrada mudou desde o calculo."""


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
