from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import Client

from app.core.auth import AuthedUser, require_user, user_scoped_client
from app.optimizer.policy import DEFAULT_POLICY
from app.services import romaneio
from app.services.org import require_org_id

router = APIRouter(prefix="/plans", tags=["planos"])


class SolveRequest(BaseModel):
    axis_id: str
    vehicle_id: str
    batch_id: str
    mode: str
    policy: str = DEFAULT_POLICY


@router.post("/solve")
def solve(
    body: SolveRequest,
    client: Client = Depends(user_scoped_client),
    org_id: str = Depends(require_org_id),
    user: AuthedUser = Depends(require_user),
):
    return romaneio.build_draft_plan(
        client,
        org_id=org_id,
        user_id=user.user_id,
        axis_id=body.axis_id,
        vehicle_id=body.vehicle_id,
        batch_id=body.batch_id,
        mode=body.mode,
        policy_name=body.policy,
    )


@router.get("")
def list_plans(client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    return client.table("plans").select("*, axes(name), vehicles(name)").eq("org_id", org_id).order(
        "created_at", desc=True
    ).execute().data


@router.get("/{plan_id}")
def get_plan(plan_id: str, client: Client = Depends(user_scoped_client)):
    plan = client.table("plans").select("*, axes(name), vehicles(name)").eq("id", plan_id).single().execute().data
    orders = (
        client.table("plan_orders")
        .select("*, orders(external_id, city)")
        .eq("plan_id", plan_id)
        .order("stop_sequence")
        .execute()
        .data
    )
    return {"plan": plan, "orders": orders}


class StopsUpdate(BaseModel):
    order_sequence: list[str]  # lista de order_id na ordem desejada


@router.patch("/{plan_id}/stops")
def update_stops(plan_id: str, body: StopsUpdate, client: Client = Depends(user_scoped_client)):
    plan = client.table("plans").select("status").eq("id", plan_id).single().execute().data
    if plan["status"] != "draft":
        raise HTTPException(409, "Sequencia so pode ser ajustada em um plano rascunho.")
    for i, order_id in enumerate(body.order_sequence, start=1):
        client.table("plan_orders").update({"stop_sequence": i}).eq("plan_id", plan_id).eq(
            "order_id", order_id
        ).execute()
    return {"updated": True}


@router.post("/{plan_id}/issue")
def issue(plan_id: str, client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    try:
        return romaneio.issue_plan(client, org_id=org_id, plan_id=plan_id)
    except romaneio.PlanConflictError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/{plan_id}/cancel")
def cancel(plan_id: str, client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    return romaneio.cancel_plan(client, org_id=org_id, plan_id=plan_id)
