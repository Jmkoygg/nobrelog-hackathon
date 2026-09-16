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
    mode: str,
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
                "mode": mode,
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
            "mode": mode,
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
