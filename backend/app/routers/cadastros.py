"""CRUD de frota, eixos/cidades e produtos. Tudo editavel pela API — nada
disso e constante de negocio no codigo, conforme decidido com o time."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import Client

from app.core.auth import user_scoped_client
from app.services.org import require_org_id

router = APIRouter(tags=["cadastros"])


# ---------------------------------------------------------------- veiculos
class VehicleIn(BaseModel):
    name: str
    capacity_kg: float
    capacity_m3: float
    active: bool = True
    source: str | None = None
    spec_date: str | None = None


@router.get("/vehicles")
def list_vehicles(client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    return client.table("vehicles").select("*").eq("org_id", org_id).order("name").execute().data


@router.post("/vehicles")
def create_vehicle(body: VehicleIn, client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    row = {**body.model_dump(), "org_id": org_id}
    return client.table("vehicles").insert(row).execute().data[0]


@router.patch("/vehicles/{vehicle_id}")
def update_vehicle(vehicle_id: str, body: VehicleIn, client: Client = Depends(user_scoped_client)):
    current = client.table("vehicles").select("version").eq("id", vehicle_id).single().execute().data
    row = {**body.model_dump(), "version": current["version"] + 1}
    return client.table("vehicles").update(row).eq("id", vehicle_id).execute().data[0]


# -------------------------------------------------------------------- eixos
# Cidades (com ou sem coordenada, com ou sem eixo) moram em /cities —
# ver app/routers/geo.py. Aqui so o cadastro do eixo em si; a listagem
# devolve as cidades embutidas (mesma tabela unificada), pra tela mostrar
# eixo -> cidades sem precisar de uma segunda chamada.
class AxisIn(BaseModel):
    name: str


@router.get("/axes")
def list_axes(client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    return client.table("axes").select("*, cities(*)").eq("org_id", org_id).order("name").execute().data


@router.post("/axes")
def create_axis(body: AxisIn, client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    row = {**body.model_dump(), "org_id": org_id}
    return client.table("axes").insert(row).execute().data[0]


# ----------------------------------------------------------------- produtos
class ProductIn(BaseModel):
    code: str
    description: str | None = None
    sale_unit: str | None = None
    load_unit: str | None = None
    conversion_factor: float | None = 1.0
    weight_kg: float | None = None
    volume_m3: float | None = None
    weight_range_min: float | None = None
    weight_range_max: float | None = None
    volume_range_min: float | None = None
    volume_range_max: float | None = None
    source: str | None = None
    is_estimated: bool = False


@router.get("/products")
def list_products(client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    return client.table("products").select("*").eq("org_id", org_id).order("code").execute().data


@router.post("/products")
def upsert_product(body: ProductIn, client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    row = {**body.model_dump(), "org_id": org_id}
    return (
        client.table("products")
        .upsert(row, on_conflict="org_id,code")
        .execute()
        .data[0]
    )


@router.patch("/products/{product_id}")
def update_product(product_id: str, body: ProductIn, client: Client = Depends(user_scoped_client)):
    current = client.table("products").select("version").eq("id", product_id).single().execute().data
    row = {**body.model_dump(), "version": current["version"] + 1}
    return client.table("products").update(row).eq("id", product_id).execute().data[0]
