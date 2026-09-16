"""Etapa 2 do desafio: cruzar item x catalogo de produto e converter para
kg/m3. A regra de conversao mora no cadastro do produto (sale_unit,
load_unit, conversion_factor, weight_kg, volume_m3) — este modulo nao sabe
o que e "piso" ou "cimento", so aplica a mesma conta pra qualquer produto
configurado assim. Isso e' o que deixa o catalogo trocavel sem mexer aqui.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_ROUNDING_EPSILON = 1e-6


@dataclass
class ItemCubagem:
    matched_product_id: str | None
    computed_weight_kg: float | None
    computed_volume_m3: float | None
    conversion_note: str
    issue: str | None  # None, "produto_sem_ficha" ou "unidade_ausente"


def compute_item_cubagem(
    *,
    quantity_sold: float,
    sale_unit: str | None,
    product: dict | None,
) -> ItemCubagem:
    if not sale_unit:
        return ItemCubagem(
            matched_product_id=product.get("id") if product else None,
            computed_weight_kg=None,
            computed_volume_m3=None,
            conversion_note="unidade de venda ausente no item",
            issue="unidade_ausente",
        )

    if product is None:
        return ItemCubagem(
            matched_product_id=None,
            computed_weight_kg=None,
            computed_volume_m3=None,
            conversion_note="codigo do produto nao encontrado no catalogo",
            issue="produto_sem_ficha",
        )

    weight_per_unit = product.get("weight_kg")
    volume_per_unit = product.get("volume_m3")
    if weight_per_unit is None or volume_per_unit is None:
        return ItemCubagem(
            matched_product_id=product["id"],
            computed_weight_kg=None,
            computed_volume_m3=None,
            conversion_note="produto no catalogo sem peso/volume por unidade de carga",
            issue="produto_sem_ficha",
        )

    conversion_factor = product.get("conversion_factor") or 1.0
    load_unit = product.get("load_unit") or sale_unit

    if conversion_factor <= 0:
        return ItemCubagem(
            matched_product_id=product["id"],
            computed_weight_kg=None,
            computed_volume_m3=None,
            conversion_note="fator de conversao invalido (<= 0) cadastrado para o produto",
            issue="produto_sem_ficha",
        )

    raw_units = quantity_sold / conversion_factor
    rounded_units = math.ceil(raw_units - _ROUNDING_EPSILON)
    is_exact = abs(raw_units - round(raw_units)) < 1e-3

    weight = rounded_units * weight_per_unit
    volume = rounded_units * volume_per_unit

    if load_unit == sale_unit and abs(conversion_factor - 1.0) < 1e-9:
        note = f"{quantity_sold:g} {sale_unit} x {weight_per_unit:g} kg/{load_unit} = {weight:g} kg"
    elif is_exact:
        note = (
            f"{quantity_sold:g} {sale_unit} / {conversion_factor:g} {sale_unit} por {load_unit} "
            f"= {rounded_units:g} {load_unit} (exato) -> {weight:g} kg / {volume:g} m3"
        )
    else:
        note = (
            f"{quantity_sold:g} {sale_unit} / {conversion_factor:g} = {raw_units:.4f} {load_unit} "
            f"-> arredondado para cima para {rounded_units:g} {load_unit} "
            f"(nao descartamos fracao de caixa) -> {weight:g} kg / {volume:g} m3"
        )

    return ItemCubagem(
        matched_product_id=product["id"],
        computed_weight_kg=weight,
        computed_volume_m3=volume,
        conversion_note=note,
        issue=None,
    )
