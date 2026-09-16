from __future__ import annotations

from fastapi import Depends, HTTPException
from supabase import Client

from app.core.auth import user_scoped_client


def require_org_id(client: Client = Depends(user_scoped_client)) -> str:
    """Organizacao do usuario autenticado. MVP assume uma org por usuario
    (times compartilham via convite — ver bootstrap_organization /
    accept_org_invite nas migrations); nao inventamos org nenhuma aqui."""
    result = client.table("memberships").select("org_id").limit(1).execute()
    if not result.data:
        raise HTTPException(
            status_code=409,
            detail=(
                "Usuario ainda nao pertence a nenhuma organizacao. "
                "Chame POST /orgs/bootstrap (primeiro acesso) ou "
                "POST /orgs/accept-invite (convite de um colega)."
            ),
        )
    return result.data[0]["org_id"]
