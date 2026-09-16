"""Cadastro de cidades (eixo + coordenada) e cache da matriz de distancia
real de estrada. Uma cidade so precisa existir (nome); eixo e coordenada
sao opcionais e independentes um do outro — cidade pode ter eixo sem
coordenada ainda (bloqueia so o despacho multi-veiculo, nao a montagem de
carga por eixo), ou coordenada sem eixo (cidade avulsa).

A matriz de distancia e' calculada uma vez contra o OSRM (motor de rotas
aberto) e guardada no banco — a demonstracao ao vivo do time nao depende
de internet no momento da montagem de carga, so no momento de recalcular
o cache (uma acao explicita, nao automatica a cada clique)."""

from __future__ import annotations

import itertools

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import Client

from app.core.auth import user_scoped_client
from app.services.org import require_org_id

router = APIRouter(tags=["geografia"])

OSRM_TABLE_URL = "https://router.project-osrm.org/table/v1/driving/{coords}"


class CityIn(BaseModel):
    name: str
    axis_id: str | None = None
    lat: float | None = None
    lng: float | None = None
    is_depot: bool = False
    sort_order: int = 0
    city_aliases: list[str] = []


@router.get("/cities")
def list_cities(client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    return client.table("cities").select("*").eq("org_id", org_id).order("name").execute().data


@router.post("/cities")
def create_city(body: CityIn, client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    # so manda os campos que o chamador realmente informou (exclude_unset):
    # isso e' o que faz "adicionar cidade X neste eixo" (so envia nome +
    # eixo) reaproveitar uma cidade existente sem apagar coordenada/outros
    # campos que ela ja tinha e este request nao mencionou.
    row = {**body.model_dump(exclude_unset=True), "org_id": org_id}
    return client.table("cities").upsert(row, on_conflict="org_id,name").execute().data[0]


@router.patch("/cities/{city_id}")
def update_city(city_id: str, body: CityIn, client: Client = Depends(user_scoped_client)):
    # mesmo cuidado do POST: so toca no que veio no corpo da requisicao.
    return client.table("cities").update(body.model_dump(exclude_unset=True)).eq("id", city_id).execute().data[0]


@router.delete("/cities/{city_id}")
def delete_city(city_id: str, client: Client = Depends(user_scoped_client)):
    client.table("cities").delete().eq("id", city_id).execute()
    return {"deleted": True}


@router.post("/cities/distances/rebuild")
def rebuild_distance_matrix(client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    all_cities = client.table("cities").select("id, name, lat, lng").eq("org_id", org_id).execute().data
    cities = [c for c in all_cities if c["lat"] is not None and c["lng"] is not None]
    if len(cities) < 2:
        raise HTTPException(
            422,
            f"Só {len(cities)} de {len(all_cities)} cidades cadastradas têm coordenada no mapa. "
            "Marque pelo menos 2 (incluindo o depósito) antes de calcular distâncias.",
        )

    coords = ";".join(f"{c['lng']},{c['lat']}" for c in cities)
    url = OSRM_TABLE_URL.format(coords=coords) + "?annotations=distance,duration"

    try:
        resp = httpx.get(url, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"OSRM indisponível agora: {exc}. Tente de novo mais tarde.") from exc

    if data.get("code") != "Ok":
        raise HTTPException(502, f"OSRM retornou erro: {data.get('message', data.get('code'))}")

    distances = data["distances"]  # metros
    durations = data["durations"]  # segundos

    rows = []
    for i, j in itertools.product(range(len(cities)), repeat=2):
        if i == j:
            continue
        d = distances[i][j]
        t = durations[i][j]
        if d is None or t is None:
            continue
        rows.append(
            {
                "org_id": org_id,
                "from_city_id": cities[i]["id"],
                "to_city_id": cities[j]["id"],
                "distance_km": round(d / 1000, 3),
                "duration_min": round(t / 60, 2),
                "source": "osrm",
            }
        )

    if rows:
        client.table("city_distances").upsert(rows, on_conflict="org_id,from_city_id,to_city_id").execute()

    return {"cities": len(cities), "cities_sem_coordenada": len(all_cities) - len(cities), "pairs_computed": len(rows)}


@router.get("/cities/distances")
def list_distances(client: Client = Depends(user_scoped_client), org_id: str = Depends(require_org_id)):
    return (
        client.table("city_distances")
        .select("*, from:from_city_id(name), to:to_city_id(name)")
        .eq("org_id", org_id)
        .execute()
        .data
    )
