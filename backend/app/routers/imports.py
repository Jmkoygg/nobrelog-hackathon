from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from supabase import Client

from app.core.auth import AuthedUser, require_user, user_scoped_client
from app.services import import_pipeline
from app.services.org import require_org_id

router = APIRouter(tags=["importacao"])


@router.post("/imports")
async def create_import(
    file: UploadFile = File(...),
    mode: str = Form(...),
    reference_date: str | None = Form(None),
    client: Client = Depends(user_scoped_client),
    org_id: str = Depends(require_org_id),
    user: AuthedUser = Depends(require_user),
):
    if mode not in ("simulacao_historica", "operacao"):
        raise HTTPException(422, "mode deve ser 'simulacao_historica' ou 'operacao'.")

    ref_date = date.fromisoformat(reference_date) if reference_date else None
    file_bytes = await file.read()

    return import_pipeline.import_csv(
        client=client,
        org_id=org_id,
        user_id=user.user_id,
        file_bytes=file_bytes,
        filename=file.filename or "arquivo.csv",
        mode=mode,
        reference_date=ref_date,
    )


@router.get("/batches")
def list_batches(client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    return (
        client.table("import_batches")
        .select("*")
        .eq("org_id", org_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )


@router.get("/batches/{batch_id}/orders")
def list_batch_orders(
    batch_id: str,
    status: str | None = None,
    search: str | None = None,
    client: Client = Depends(user_scoped_client),
):
    query = client.table("orders").select("*").eq("batch_id", batch_id)
    if status:
        query = query.eq("data_status", status)
    result = query.order("external_id").execute().data
    if search:
        needle = search.strip().upper()
        result = [o for o in result if needle in (o["external_id"] + " " + (o["city"] or "")).upper()]
    return result


@router.get("/batches/{batch_id}/issues")
def list_batch_issues(batch_id: str, client: Client = Depends(user_scoped_client)):
    order_ids = [o["id"] for o in client.table("orders").select("id").eq("batch_id", batch_id).execute().data]
    if not order_ids:
        return []
    return (
        client.table("issues")
        .select("*")
        .in_("order_id", order_ids)
        .eq("status", "open")
        .execute()
        .data
    )


class IssueResolution(BaseModel):
    resolution: dict
    reprocess: bool = True


@router.patch("/issues/{issue_id}")
def resolve_issue(
    issue_id: str,
    body: IssueResolution,
    client: Client = Depends(user_scoped_client),
    user: AuthedUser = Depends(require_user),
):
    from datetime import datetime, timezone

    updated = (
        client.table("issues")
        .update(
            {
                "status": "resolved",
                "resolution": body.resolution,
                "resolved_by": user.user_id,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", issue_id)
        .execute()
        .data[0]
    )
    return {
        "issue": updated,
        "note": (
            "Correcao registrada. Reprocessamento automatico do pedido afetado "
            "ainda nao esta implementado nesta versao — recalcule a carga apos "
            "corrigir o cadastro correspondente (produto/eixo)."
        ),
    }
