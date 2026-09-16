import itertools

from app.optimizer.solver import OrderInput, solve_axis_vehicle


def test_exactly_at_limit_is_accepted():
    order = OrderInput(id="A", weight_kg=1700.0, volume_m3=2.18, value=1000.0)
    result = solve_axis_vehicle([order], capacity_kg=1700.0, capacity_m3=2.18, policy_name="valor_total")
    assert result.validated, result.validation_errors
    assert result.selected_ids == ["A"]


def test_one_unit_above_limit_is_rejected_not_truncated():
    # 1700,001 kg nao pode virar 1700 por arredondamento — tem que ficar de fora.
    order = OrderInput(id="A", weight_kg=1700.001, volume_m3=2.18, value=1000.0)
    result = solve_axis_vehicle([order], capacity_kg=1700.0, capacity_m3=2.18, policy_name="valor_total")
    assert result.selected_ids == []
    assert result.order_results[0].reason == "pedido_excede_capacidade_sozinho"


def test_no_order_fits_alone_is_optimal_empty_not_infeasible():
    # ponto explicito do design: vazio nao e' INFEASIBLE.
    order = OrderInput(id="A", weight_kg=99999.0, volume_m3=0.001, value=10.0)
    result = solve_axis_vehicle([order], capacity_kg=1700.0, capacity_m3=2.18, policy_name="valor_total")
    assert result.status == "optimal"
    assert result.selected_ids == []
    assert result.validated


def test_no_candidate_orders_at_all_is_validated_not_flagged_as_inconsistent():
    # bug real: lote/eixo sem nenhum pedido candidato retornava validated=False
    # (nunca chegava a rodar o validador), fazendo a tela mostrar um aviso de
    # "inconsistencia" que nao existia — zero pedidos e' trivialmente valido.
    result = solve_axis_vehicle([], capacity_kg=1700.0, capacity_m3=2.18, policy_name="valor_total")
    assert result.status == "empty_no_orders"
    assert result.validated
    assert result.validation_errors == []


def test_whole_order_preserved_never_partial():
    # pedido grande demais pra caber junto com outro deve ficar de fora
    # inteiro, nunca "parcialmente" — o modelo so tem variavel por pedido.
    big = OrderInput(id="big", weight_kg=1600.0, volume_m3=0.5, value=5000.0)
    small = OrderInput(id="small", weight_kg=200.0, volume_m3=0.1, value=100.0)
    result = solve_axis_vehicle([big, small], capacity_kg=1700.0, capacity_m3=2.18, policy_name="valor_total")
    # 1600+200=1800 > 1700kg: nao cabem os dois. Objetivo valor_total escolhe o "big".
    assert result.selected_ids == ["big"]
    assert result.total_weight_kg == 1600
    for order_result in result.order_results:
        if order_result.id == "small":
            assert order_result.selected is False


def _brute_force_best_value(orders: list[OrderInput], capacity_kg: float, capacity_m3: float):
    best = (0.0, ())
    for r in range(len(orders) + 1):
        for combo in itertools.combinations(orders, r):
            w = sum(o.weight_kg for o in combo)
            v = sum(o.volume_m3 for o in combo)
            if w <= capacity_kg and v <= capacity_m3:
                value = sum(o.value for o in combo)
                if value > best[0]:
                    best = (value, tuple(o.id for o in combo))
    return best


def test_small_case_matches_exhaustive_enumeration():
    orders = [
        OrderInput(id="o1", weight_kg=700, volume_m3=0.40, value=2100),
        OrderInput(id="o2", weight_kg=450, volume_m3=1.00, value=1800),
        OrderInput(id="o3", weight_kg=550, volume_m3=0.50, value=2600),
        OrderInput(id="o4", weight_kg=300, volume_m3=0.80, value=1200),
        OrderInput(id="o5", weight_kg=950, volume_m3=0.60, value=3400),
        OrderInput(id="o6", weight_kg=180, volume_m3=0.70, value=900),
    ]
    capacity_kg, capacity_m3 = 1700.0, 2.2

    result = solve_axis_vehicle(orders, capacity_kg=capacity_kg, capacity_m3=capacity_m3, policy_name="valor_total")
    best_value, _ = _brute_force_best_value(orders, capacity_kg, capacity_m3)

    assert result.status == "optimal"
    assert float(result.total_value) == best_value
    assert float(result.total_weight_kg) <= capacity_kg
    assert float(result.total_volume_m3) <= capacity_m3


def test_occupancy_policy_maximizes_combined_use_not_just_value():
    # A+B juntos cabem (1690kg/2,15m3) e ocupam bem as duas dimensoes.
    # C sozinho tem valor comercial maior mas usa muito menos a capacidade,
    # e nenhuma combinacao com C cabe junto de A ou B (estoura o peso).
    order_a = OrderInput(id="A", weight_kg=1600, volume_m3=0.15, value=100)
    order_b = OrderInput(id="B", weight_kg=90, volume_m3=2.00, value=100)
    order_c = OrderInput(id="C", weight_kg=1650, volume_m3=0.30, value=1500)

    result = solve_axis_vehicle(
        [order_a, order_b, order_c], capacity_kg=1700.0, capacity_m3=2.18, policy_name="ocupacao_media_kg_m3"
    )
    assert set(result.selected_ids) == {"A", "B"}


def test_tie_break_prefers_more_orders_then_more_value():
    # capacidade de kg deliberadamente apertada: {big} e {s1,s2} sao as
    # duas unicas combinacoes que cabem no limite e valem o mesmo total
    # (1000) — nao cabem juntas. Desempate deve preferir mais pedidos.
    one_big = OrderInput(id="big", weight_kg=200, volume_m3=0.1, value=1000)
    two_small_a = OrderInput(id="s1", weight_kg=100, volume_m3=0.05, value=500)
    two_small_b = OrderInput(id="s2", weight_kg=100, volume_m3=0.05, value=500)

    result = solve_axis_vehicle(
        [one_big, two_small_a, two_small_b], capacity_kg=200.0, capacity_m3=2.18, policy_name="valor_total"
    )
    assert set(result.selected_ids) == {"s1", "s2"}
