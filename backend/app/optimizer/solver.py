"""Mochila 0/1 com duas restricoes (kg e m3), resolvida exata com CP-SAT.

Cuidados que vieram direto do design revisado pelo time:
- inteiros, sem arredondar carga pra baixo: contribuicao do pedido
  arredonda pra CIMA, capacidade arredonda pra BAIXO;
- desempate (mais pedidos, depois mais valor) so roda se a etapa anterior
  provou otimo — nunca empilha estagio em cima de um resultado so viavel;
- FEASIBLE != OPTIMAL, e isso vai pro resultado explicitamente;
- validador roda separado do solver, em Decimal, e pode reprovar mesmo
  uma resposta que o CP-SAT deu como valida (defesa em profundidade).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal

from ortools.sat.python import cp_model

from app.optimizer.policy import PolicyInput, get_policy

_KG_TO_G = 1000
_M3_TO_CM3 = 1_000_000
_REAIS_TO_CENTS = 100


@dataclass
class OrderInput:
    id: str
    weight_kg: float
    volume_m3: float
    value: float


@dataclass
class OrderResult:
    id: str
    selected: bool
    reason: str | None = None


@dataclass
class SolveResult:
    status: str  # "optimal", "feasible_timeout", "empty_no_orders", "erro_solver"
    policy: str
    selected_ids: list[str] = field(default_factory=list)
    order_results: list[OrderResult] = field(default_factory=list)
    excluded_alone: list[OrderResult] = field(default_factory=list)
    total_weight_kg: Decimal = Decimal(0)
    total_volume_m3: Decimal = Decimal(0)
    total_value: Decimal = Decimal(0)
    occupancy_kg_pct: float = 0.0
    occupancy_m3_pct: float = 0.0
    wall_time_ms: int = 0
    seed: int = 0
    workers: int = 0
    validated: bool = False
    validation_errors: list[str] = field(default_factory=list)


def _ceil_scale(value: float, factor: int) -> int:
    return math.ceil(round(value * factor, 6) - 1e-6)


def _floor_scale(value: float, factor: int) -> int:
    return math.floor(round(value * factor, 6) + 1e-6)


def solve_axis_vehicle(
    orders: list[OrderInput],
    *,
    capacity_kg: float,
    capacity_m3: float,
    policy_name: str,
    time_limit_seconds: float = 10.0,
    seed: int = 42,
    workers: int = 8,
) -> SolveResult:
    policy_fn = get_policy(policy_name)
    capacity_kg_g = _floor_scale(capacity_kg, _KG_TO_G)
    capacity_m3_cm3 = _floor_scale(capacity_m3, _M3_TO_CM3)

    if not orders:
        return SolveResult(status="empty_no_orders", policy=policy_name)

    eligible: list[OrderInput] = []
    excluded_alone: list[OrderResult] = []
    for order in orders:
        w = _ceil_scale(order.weight_kg, _KG_TO_G)
        v = _ceil_scale(order.volume_m3, _M3_TO_CM3)
        if w > capacity_kg_g or v > capacity_m3_cm3:
            excluded_alone.append(
                OrderResult(id=order.id, selected=False, reason="pedido_excede_capacidade_sozinho")
            )
        else:
            eligible.append(order)

    if not eligible:
        # Nenhum pedido cabe sozinho: a selecao vazia e' a unica opcao e e'
        # trivialmente otima (nao ha restricao de selecao minima). Isto NAO
        # e' INFEASIBLE — o design foi explicito sobre nao confundir os dois.
        return validate_solution(
            SolveResult(
                status="optimal",
                policy=policy_name,
                selected_ids=[],
                excluded_alone=excluded_alone,
                order_results=excluded_alone,
            ),
            orders={o.id: o for o in orders},
            capacity_kg=capacity_kg,
            capacity_m3=capacity_m3,
        )

    weights_g = {o.id: _ceil_scale(o.weight_kg, _KG_TO_G) for o in eligible}
    volumes_cm3 = {o.id: _ceil_scale(o.volume_m3, _M3_TO_CM3) for o in eligible}
    values_cents = {o.id: _ceil_scale(o.value, _REAIS_TO_CENTS) for o in eligible}
    coefficients = {
        o.id: policy_fn(
            PolicyInput(
                weight_g=weights_g[o.id],
                volume_cm3=volumes_cm3[o.id],
                value_cents=values_cents[o.id],
                capacity_kg_g=capacity_kg_g,
                capacity_m3_cm3=capacity_m3_cm3,
            )
        )
        for o in eligible
    }

    total_wall_ms = 0

    def _new_model_with_vars() -> tuple[cp_model.CpModel, dict[str, cp_model.IntVar]]:
        model = cp_model.CpModel()
        x = {o.id: model.NewBoolVar(f"x_{o.id}") for o in eligible}
        model.Add(sum(weights_g[i] * x[i] for i in x) <= capacity_kg_g)
        model.Add(sum(volumes_cm3[i] * x[i] for i in x) <= capacity_m3_cm3)
        return model, x

    def _solve(model: cp_model.CpModel) -> tuple[cp_model.CpSolver, int]:
        nonlocal total_wall_ms
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        solver.parameters.num_search_workers = workers
        solver.parameters.random_seed = seed
        status = solver.Solve(model)
        total_wall_ms += int(solver.WallTime() * 1000)
        return solver, status

    # Estagio 1: objetivo principal da politica escolhida.
    model, x = _new_model_with_vars()
    model.Maximize(sum(coefficients[i] * x[i] for i in x))
    solver, status = _solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Este modelo sempre tem a selecao vazia como solucao viavel (nao ha
        # restricao de minimo), entao um status diferente de OPTIMAL/FEASIBLE
        # aqui indica erro do solver, nao uma resposta de negocio valida —
        # por isso nao rotulamos como "infeasible".
        return SolveResult(
            status="erro_solver",
            policy=policy_name,
            excluded_alone=excluded_alone,
            order_results=[OrderResult(id=i, selected=False, reason="modelo_sem_solucao") for i in x]
            + excluded_alone,
            wall_time_ms=total_wall_ms,
            seed=seed,
            workers=workers,
        )

    objective_value = int(solver.ObjectiveValue())
    proved_optimal = status == cp_model.OPTIMAL
    selected_ids = {i for i in x if solver.Value(x[i]) == 1}

    # Estagio 2 (desempate por numero de pedidos) so roda se o estagio 1
    # provou otimo — nunca empilhamos desempate sobre resultado so viavel.
    if proved_optimal:
        model2, x2 = _new_model_with_vars()
        model2.Add(sum(coefficients[i] * x2[i] for i in x2) == objective_value)
        model2.Maximize(sum(x2[i] for i in x2))
        solver2, status2 = _solve(model2)
        if status2 == cp_model.OPTIMAL:
            count_value = int(solver2.ObjectiveValue())
            selected_ids = {i for i in x2 if solver2.Value(x2[i]) == 1}

            # Estagio 3 (desempate por valor total) so roda se o estagio 2
            # tambem provou otimo.
            model3, x3 = _new_model_with_vars()
            model3.Add(sum(coefficients[i] * x3[i] for i in x3) == objective_value)
            model3.Add(sum(x3[i] for i in x3) == count_value)
            model3.Maximize(sum(values_cents[i] * x3[i] for i in x3))
            solver3, status3 = _solve(model3)
            if status3 == cp_model.OPTIMAL:
                selected_ids = {i for i in x3 if solver3.Value(x3[i]) == 1}

    # Motivo de nao-selecao pros que ficaram de fora do modelo (nao dos
    # excluidos sozinhos, ja marcados acima).
    remaining_kg = capacity_kg_g - sum(weights_g[i] for i in selected_ids)
    remaining_m3 = capacity_m3_cm3 - sum(volumes_cm3[i] for i in selected_ids)
    order_results = []
    for order in eligible:
        if order.id in selected_ids:
            order_results.append(OrderResult(id=order.id, selected=True))
            continue
        if weights_g[order.id] > remaining_kg or volumes_cm3[order.id] > remaining_m3:
            reason = "nao_cabe_no_espaco_restante_desta_combinacao"
        else:
            reason = "nao_incluido_na_combinacao_calculada"
        order_results.append(OrderResult(id=order.id, selected=False, reason=reason))

    result = SolveResult(
        status="optimal" if proved_optimal else "feasible_timeout",
        policy=policy_name,
        selected_ids=sorted(selected_ids),
        order_results=order_results + excluded_alone,
        excluded_alone=excluded_alone,
        wall_time_ms=total_wall_ms,
        seed=seed,
        workers=workers,
    )
    return validate_solution(
        result,
        orders={o.id: o for o in orders},
        capacity_kg=capacity_kg,
        capacity_m3=capacity_m3,
    )


def validate_solution(
    result: SolveResult,
    *,
    orders: dict[str, OrderInput],
    capacity_kg: float,
    capacity_m3: float,
) -> SolveResult:
    """Recalcula tudo em Decimal, independente do CP-SAT. Se algo nao
    bater, o plano nao pode ser emitido — quem chama deve checar `validated`."""
    errors: list[str] = []

    if len(result.selected_ids) != len(set(result.selected_ids)):
        errors.append("IDs de pedido duplicados na selecao.")

    total_weight = Decimal(0)
    total_volume = Decimal(0)
    total_value = Decimal(0)
    for oid in result.selected_ids:
        order = orders.get(oid)
        if order is None:
            errors.append(f"Pedido selecionado {oid} nao existe no lote de entrada.")
            continue
        total_weight += Decimal(str(order.weight_kg))
        total_volume += Decimal(str(order.volume_m3))
        total_value += Decimal(str(order.value))

    cap_kg = Decimal(str(capacity_kg))
    cap_m3 = Decimal(str(capacity_m3))
    if total_weight > cap_kg:
        errors.append(f"Peso total {total_weight} kg excede capacidade {cap_kg} kg.")
    if total_volume > cap_m3:
        errors.append(f"Volume total {total_volume} m3 excede capacidade {cap_m3} m3.")

    result.total_weight_kg = total_weight
    result.total_volume_m3 = total_volume
    result.total_value = total_value
    result.occupancy_kg_pct = float(total_weight / cap_kg * 100) if cap_kg else 0.0
    result.occupancy_m3_pct = float(total_volume / cap_m3 * 100) if cap_m3 else 0.0
    result.validated = not errors
    result.validation_errors = errors
    return result
