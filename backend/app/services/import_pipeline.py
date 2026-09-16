"""Etapa 1 do desafio (limpeza) + orquestracao da etapa 2 (cubagem) no
momento da importacao. Preserva o arquivo original em raw_rows, nunca
duplica pedido no reimport (idempotente por hash do arquivo), e nunca
imputa peso/volume zero para dado ausente.
"""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import date

from supabase import Client

from app.services import parsing
from app.services.cubagem import compute_item_cubagem


def _build_axis_lookup(client: Client, org_id: str) -> dict[str, str]:
    rows = (
        client.table("cities")
        .select("axis_id, name, city_aliases")
        .eq("org_id", org_id)
        .not_.is_("axis_id", "null")
        .execute()
        .data
    )
    lookup: dict[str, str] = {}
    for row in rows:
        lookup[parsing.normalize_city_key(row["name"])] = row["axis_id"]
        for alias in row.get("city_aliases") or []:
            lookup[parsing.normalize_city_key(alias)] = row["axis_id"]
    return lookup


def _build_product_lookup(client: Client, org_id: str) -> dict[str, dict]:
    rows = client.table("products").select("*").eq("org_id", org_id).execute().data
    return {row["code"].strip(): row for row in rows}


def import_csv(
    *,
    client: Client,
    org_id: str,
    user_id: str,
    file_bytes: bytes,
    filename: str,
    reference_date: date | None,
) -> dict:
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    existing = (
        client.table("import_batches")
        .select("id, summary, status")
        .eq("org_id", org_id)
        .eq("file_hash", file_hash)
        .execute()
    )
    if existing.data:
        batch = existing.data[0]
        return {
            "batch_id": batch["id"],
            "already_imported": True,
            "summary": batch["summary"],
        }

    batch_insert = (
        client.table("import_batches")
        .insert(
            {
                "org_id": org_id,
                "file_hash": file_hash,
                "filename": filename,
                "mode": "operacao",
                "reference_date": reference_date.isoformat() if reference_date else None,
                "status": "processing",
                "created_by": user_id,
            }
        )
        .execute()
    )
    batch_id = batch_insert.data[0]["id"]

    text = file_bytes.decode("utf-8-sig")
    sniffed_delimiter = ";" if text.split("\n", 1)[0].count(";") >= text.split("\n", 1)[0].count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=sniffed_delimiter)

    axis_lookup = _build_axis_lookup(client, org_id)
    product_lookup = _build_product_lookup(client, org_id)

    raw_rows: list[dict] = []
    order_rows: list[dict] = []
    order_row_by_external_id: dict[str, dict] = {}
    item_rows: list[dict] = []
    issue_rows: list[dict] = []

    counts = {"total": 0, "excluded": 0, "pending": 0, "ready": 0}

    for row_number, row in enumerate(reader, start=1):
        raw_rows.append({"org_id": org_id, "batch_id": batch_id, "row_number": row_number, "raw_data": row})
        counts["total"] += 1

        external_id = (row.get("Pedido") or row.get("PEDIDO") or "").strip()
        if not external_id:
            continue

        city_raw = row.get("Cidade") or row.get("CIDADE") or ""
        logistics_status = row.get("Logistica") or row.get("LOGISTICA")
        delivery_status = row.get("Situacao_CSV_Entrega") or row.get("STATUS DA ENTREGA")
        order_status = row.get("Situacao") or row.get("SITUACAO")
        value = parsing.parse_br_number(row.get("Valor_Pedido") or row.get("VALOR DO PEDIDO"))
        parsed_date = parsing.parse_br_date(row.get("Data") or row.get("DATA"))
        delivered = parsing.is_delivered(logistics_status=logistics_status, delivery_status=delivery_status)

        excl_reason = parsing.exclusion_reason(
            city=city_raw, logistics_status=logistics_status, delivery_status=delivery_status
        )

        order = {
            "org_id": org_id,
            "batch_id": batch_id,
            "external_id": external_id,
            "mode": "operacao",
            "city": parsing.normalize_city(city_raw),
            "axis_id": None,
            "logistics_status": logistics_status,
            "order_status": order_status,
            "order_date": parsed_date.value.isoformat() if parsed_date.value else None,
            "order_date_raw": parsed_date.raw,
            "order_date_flagged": parsed_date.flagged,
            "delivered": delivered,
            "value": value,
            "excluded_reason": excl_reason,
            "weight_kg": None,
            "volume_m3": None,
            "data_status": "excluded" if excl_reason else "pending",
        }

        if excl_reason:
            counts["excluded"] += 1
            order_rows.append(order)
            order_row_by_external_id[external_id] = order
            continue

        if parsed_date.flagged:
            issue_rows.append(
                {
                    "org_id": org_id,
                    "issue_type": "data_inconsistente",
                    "description": f"Pedido {external_id}: data '{parsed_date.raw}' — {parsed_date.note}.",
                    "status": "open",
                    "_external_id": external_id,
                }
            )

        axis_id = axis_lookup.get(parsing.normalize_city_key(order["city"]))
        if axis_id is None:
            issue_rows.append(
                {
                    "org_id": org_id,
                    "issue_type": "cidade_sem_eixo",
                    "description": f"Pedido {external_id}: cidade '{order['city']}' sem eixo associado no cadastro.",
                    "status": "open",
                    "_external_id": external_id,
                }
            )
        order["axis_id"] = axis_id

        items = parsing.parse_itens_resumo(row.get("Itens_Resumo") or row.get("ITENS"))
        order_items_computed: list[dict] = []
        all_resolved = bool(items)
        total_weight = 0.0
        total_volume = 0.0

        for item in items:
            product = product_lookup.get(item.code) if item.code else None
            result = compute_item_cubagem(quantity_sold=item.quantity, sale_unit=item.unit, product=product)
            order_items_computed.append(
                {
                    "org_id": org_id,
                    "product_code": item.code,
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "matched_product_id": result.matched_product_id,
                    "computed_weight_kg": result.computed_weight_kg,
                    "computed_volume_m3": result.computed_volume_m3,
                    "conversion_note": result.conversion_note,
                }
            )
            if result.issue is not None:
                all_resolved = False
                issue_rows.append(
                    {
                        "org_id": org_id,
                        "product_code": item.code or None,
                        "issue_type": result.issue,
                        "description": f"Pedido {external_id}, item '{item.description}': {result.conversion_note}.",
                        "status": "open",
                        "_external_id": external_id,
                    }
                )
            elif all_resolved:
                total_weight += result.computed_weight_kg or 0.0
                total_volume += result.computed_volume_m3 or 0.0

        # Eixo deixou de ser trava obrigatoria: o despacho multi-veiculo usa
        # a cidade (coordenada real), nao o agrupamento de eixo. Cidade sem
        # eixo mapeado ainda vira issue informativa (linha acima), mas nao
        # bloqueia o pedido — quem bloqueia e' cubagem incompleta.
        if all_resolved:
            order["weight_kg"] = round(total_weight, 4)
            order["volume_m3"] = round(total_volume, 6)
            order["data_status"] = "ready"
            counts["ready"] += 1
        else:
            counts["pending"] += 1

        order_rows.append(order)
        order_row_by_external_id[external_id] = order
        for item_row in order_items_computed:
            item_row["_external_id"] = external_id  # resolvido para order_id apos o insert
        item_rows.extend(order_items_computed)

    if raw_rows:
        client.table("raw_rows").insert(raw_rows).execute()

    inserted_orders = client.table("orders").insert(order_rows).execute().data if order_rows else []
    order_id_by_external_id = {o["external_id"]: o["id"] for o in inserted_orders}

    for item_row in item_rows:
        item_row["order_id"] = order_id_by_external_id.get(item_row.pop("_external_id"))
    item_rows = [r for r in item_rows if r["order_id"]]
    if item_rows:
        client.table("order_items").insert(item_rows).execute()

    for issue_row in issue_rows:
        issue_row["order_id"] = order_id_by_external_id.get(issue_row.pop("_external_id"))
    if issue_rows:
        client.table("issues").insert(issue_rows).execute()

    summary = {
        "total_linhas": counts["total"],
        "excluidos": counts["excluded"],
        "pendentes": counts["pending"],
        "disponiveis": counts["ready"],
    }
    client.table("import_batches").update({"status": "done", "summary": summary}).eq("id", batch_id).execute()

    return {"batch_id": batch_id, "already_imported": False, "summary": summary}


def _get_or_create_manual_batch(client: Client, org_id: str, user_id: str, name: str | None = None) -> str:
    """Pedido montado a mao pela tela mora num lote escolhido pela pessoa
    (por nome) — ou no lote padrao "Pedidos montados na tela" se nenhum nome
    for informado — assim ele passa pelo mesmo pipeline (cubagem, pendencia,
    disponibilidade) que um pedido importado, sem precisar de um CSV por
    tras. O nome vira chave de busca (sem acento/maiuscula) pra reaproveitar
    o mesmo lote em pedidos seguintes em vez de criar um novo toda hora."""
    batch_name = (name or "").strip()
    if batch_name:
        file_hash = f"manual:{parsing.normalize_city_key(batch_name)}"
    else:
        batch_name = "Pedidos montados na tela"
        file_hash = "pedidos-manuais"  # chave legada, mantida p/ nao duplicar o lote padrao ja existente

    existing = (
        client.table("import_batches")
        .select("id")
        .eq("org_id", org_id)
        .eq("file_hash", file_hash)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]

    batch = (
        client.table("import_batches")
        .insert(
            {
                "org_id": org_id,
                "file_hash": file_hash,
                "filename": batch_name,
                "mode": "operacao",
                "status": "done",
                "summary": {"total_linhas": 0, "excluidos": 0, "pendentes": 0, "disponiveis": 0},
                "created_by": user_id,
            }
        )
        .execute()
        .data[0]
    )
    return batch["id"]


def create_manual_order(
    client: Client,
    *,
    org_id: str,
    user_id: str,
    city_id: str,
    value: float,
    items: list[dict],
    batch_id: str | None = None,
    batch_name: str | None = None,
) -> dict:
    """items: lista de {"product_code": str, "quantity": float}. Mesma
    cubagem do import — pedido monta e some da lista de disponivel do
    mesmo jeito se algum item nao tiver ficha.

    Cidade vem por `city_id` (selecionada do cadastro, nao digitada) —
    assim o eixo e' o que ja esta gravado na cidade, sem depender de
    normalizacao/match de texto pra achar o eixo certo.

    Lote de destino: se `batch_id` for informado, usa esse lote existente
    (precisa pertencer a mesma org); senao, encontra-ou-cria um lote pelo
    `batch_name` (ou o lote padrao, se nenhum nome vier)."""
    if not items:
        raise ValueError("Pedido precisa de pelo menos um item.")

    city_row = client.table("cities").select("name, axis_id").eq("org_id", org_id).eq("id", city_id).execute()
    if not city_row.data:
        raise ValueError("Cidade informada nao existe no cadastro.")
    normalized_city = city_row.data[0]["name"]
    axis_id = city_row.data[0]["axis_id"]

    if batch_id:
        existing_batch = (
            client.table("import_batches").select("id").eq("org_id", org_id).eq("id", batch_id).execute()
        )
        if not existing_batch.data:
            raise ValueError("Lote informado nao existe.")
    else:
        batch_id = _get_or_create_manual_batch(client, org_id, user_id, name=batch_name)
    product_lookup = _build_product_lookup(client, org_id)

    # id sequencial legivel, unico dentro do lote manual (constraint e'
    # org_id+batch_id+external_id, nao precisa ser globalmente unico).
    count_existing = (
        client.table("orders").select("id", count="exact").eq("org_id", org_id).eq("batch_id", batch_id).execute()
    )
    external_id = f"MANUAL-{(count_existing.count or 0) + 1:04d}"

    order_items_computed = []
    all_resolved = True
    total_weight = 0.0
    total_volume = 0.0
    issue_rows = []

    for item in items:
        code = (item.get("product_code") or "").strip()
        quantity = float(item.get("quantity") or 0)
        product = product_lookup.get(code)
        sale_unit = product["sale_unit"] if product else None
        result = compute_item_cubagem(quantity_sold=quantity, sale_unit=sale_unit, product=product)
        order_items_computed.append(
            {
                "org_id": org_id,
                "product_code": code,
                "description": product["description"] if product else code,
                "quantity": quantity,
                "unit": sale_unit,
                "matched_product_id": result.matched_product_id,
                "computed_weight_kg": result.computed_weight_kg,
                "computed_volume_m3": result.computed_volume_m3,
                "conversion_note": result.conversion_note,
            }
        )
        if result.issue is not None:
            all_resolved = False
            issue_rows.append(
                {
                    "org_id": org_id,
                    "product_code": code or None,
                    "issue_type": result.issue,
                    "description": f"Pedido {external_id}, item '{code}': {result.conversion_note}.",
                    "status": "open",
                }
            )
        elif all_resolved:
            total_weight += result.computed_weight_kg or 0.0
            total_volume += result.computed_volume_m3 or 0.0

    if axis_id is None:
        issue_rows.append(
            {
                "org_id": org_id,
                "issue_type": "cidade_sem_eixo",
                "description": f"Pedido {external_id}: cidade '{normalized_city}' sem eixo associado no cadastro.",
                "status": "open",
            }
        )

    order = {
        "org_id": org_id,
        "batch_id": batch_id,
        "external_id": external_id,
        "mode": "operacao",
        "city": normalized_city,
        "axis_id": axis_id,
        "logistics_status": "MANUAL",
        "order_status": "Montado na tela",
        "order_date": date.today().isoformat(),
        "order_date_raw": date.today().isoformat(),
        "order_date_flagged": False,
        "delivered": False,
        "value": value,
        "excluded_reason": None,
        "weight_kg": round(total_weight, 4) if all_resolved else None,
        "volume_m3": round(total_volume, 6) if all_resolved else None,
        "data_status": "ready" if all_resolved else "pending",
    }

    inserted_order = client.table("orders").insert(order).execute().data[0]

    for item_row in order_items_computed:
        item_row["order_id"] = inserted_order["id"]
    if order_items_computed:
        client.table("order_items").insert(order_items_computed).execute()

    for issue_row in issue_rows:
        issue_row["order_id"] = inserted_order["id"]
    if issue_rows:
        client.table("issues").insert(issue_rows).execute()

    batch = client.table("import_batches").select("summary").eq("id", batch_id).single().execute().data
    summary = dict(batch["summary"] or {})
    summary["total_linhas"] = (summary.get("total_linhas") or 0) + 1
    key = "disponiveis" if all_resolved else "pendentes"
    summary[key] = (summary.get(key) or 0) + 1
    client.table("import_batches").update({"summary": summary}).eq("id", batch_id).execute()

    return inserted_order
