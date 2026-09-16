from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import Client

from app.core.auth import user_scoped_client

router = APIRouter(prefix="/orgs", tags=["organizacoes"])


class BootstrapRequest(BaseModel):
    name: str


class InviteAcceptRequest(BaseModel):
    code: str


@router.post("/bootstrap")
def bootstrap(body: BootstrapRequest, client: Client = Depends(user_scoped_client)):
    org_id = client.rpc("bootstrap_organization", {"org_name": body.name}).execute().data
    return {"org_id": org_id}


@router.post("/auto-join")
def auto_join(client: Client = Depends(user_scoped_client)):
    """MVP de instancia unica: todo usuario cai automaticamente na (unica)
    organizacao da operacao — sem tela, sem convite. Cria na primeira vez,
    junta nas seguintes. Front chama isso sozinho, sem perguntar nada."""
    org_id = client.rpc("auto_join_organization", {}).execute().data
    return {"org_id": org_id}


@router.post("/invite")
def create_invite(org_id: str, client: Client = Depends(user_scoped_client)):
    code = client.rpc("create_org_invite", {"target_org": org_id}).execute().data
    return {"code": code}


@router.post("/accept-invite")
def accept_invite(body: InviteAcceptRequest, client: Client = Depends(user_scoped_client)):
    org_id = client.rpc("accept_org_invite", {"invite_code": body.code}).execute().data
    return {"org_id": org_id}


@router.get("/me")
def my_org(client: Client = Depends(user_scoped_client)):
    memberships = client.table("memberships").select("org_id, role, organizations(name)").execute().data
    return {"memberships": memberships}
