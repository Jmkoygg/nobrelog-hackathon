from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import Client

from app.core.auth import AuthedUser, require_user, user_scoped_client
from app.services import dispatch as dispatch_service
from app.services.org import require_org_id

router = APIRouter(prefix="/dispatch", tags=["despacho multi-veiculo"])


class DispatchRequest(BaseModel):
    batch_id: str
    mode: str = "simulacao_historica"


@router.post("/solve")
def solve(
    body: DispatchRequest,
    client: Client = Depends(user_scoped_client),
    org_id: str = Depends(require_org_id),
    user: AuthedUser = Depends(require_user),
):
    try:
        return dispatch_service.build_dispatch(client, org_id=org_id, user_id=user.user_id, batch_id=body.batch_id, mode=body.mode)
    except dispatch_service.DispatchError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/{dispatch_run_id}")
def get_dispatch(dispatch_run_id: str, client: Client = Depends(user_scoped_client)):
    run = client.table("dispatch_runs").select("*").eq("id", dispatch_run_id).single().execute().data
    assignments = (
        client.table("dispatch_assignments")
        .select("*, orders(external_id, city), vehicles(name)")
        .eq("dispatch_run_id", dispatch_run_id)
        .order("vehicle_id")
        .order("stop_sequence")
        .execute()
        .data
    )
    return {"run": run, "assignments": assignments}


@router.get("")
def list_dispatches(client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    return client.table("dispatch_runs").select("*").eq("org_id", org_id).order("created_at", desc=True).execute().data


@router.post("/{dispatch_run_id}/issue")
def issue(dispatch_run_id: str, client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    try:
        return dispatch_service.issue_dispatch(client, org_id=org_id, dispatch_run_id=dispatch_run_id)
    except dispatch_service.DispatchError as exc:
        raise HTTPException(409, str(exc)) from exc
