"""Politica de objetivo isolada do solver, de proposito: o time ainda vai
discutir o criterio (edital nao define formula), entao trocar de politica
nunca deve exigir mexer no modelo CP-SAT — so registrar uma funcao nova
aqui e apontar o nome no plano.

Todo policy recebe as grandezas ja escaladas para inteiro (gramas, cm3,
centavos) e devolve o coeficiente inteiro daquele pedido na funcao
objetivo. O motivo de escalar assim (V*w_i + W*v_i) esta documentado no
DESIGN-NOBRELOG.md secao 7: para um veiculo fixo, maximizar essa soma e
equivalente a maximizar 0.5*peso/W + 0.5*volume/V.
"""

from __future__ import annotations

from typing import Callable, NamedTuple


class PolicyInput(NamedTuple):
    weight_g: int
    volume_cm3: int
    value_cents: int
    capacity_kg_g: int
    capacity_m3_cm3: int


PolicyFn = Callable[[PolicyInput], int]


def _ocupacao_media_kg_m3(p: PolicyInput) -> int:
    return p.capacity_m3_cm3 * p.weight_g + p.capacity_kg_g * p.volume_cm3


def _valor_total(p: PolicyInput) -> int:
    return p.value_cents


POLICIES: dict[str, PolicyFn] = {
    "ocupacao_media_kg_m3": _ocupacao_media_kg_m3,
    "valor_total": _valor_total,
}

DEFAULT_POLICY = "ocupacao_media_kg_m3"


def get_policy(name: str) -> PolicyFn:
    try:
        return POLICIES[name]
    except KeyError as exc:
        raise ValueError(
            f"Politica de objetivo desconhecida: '{name}'. Opcoes: {sorted(POLICIES)}"
        ) from exc
