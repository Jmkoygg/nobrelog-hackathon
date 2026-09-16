from app.services.cubagem import compute_item_cubagem

PISO_21246 = {
    "id": "prod-21246",
    "code": "21246",
    "sale_unit": "MT",
    "load_unit": "caixa",
    "conversion_factor": 2.30,  # m2 por caixa
    "weight_kg": 28.28,
    "volume_m3": 0.019,
}


def test_piso_conversion_exact_box_count():
    # exemplo real do diagnostico: 23 m2 = exatamente 10 caixas = 282,8 kg
    result = compute_item_cubagem(quantity_sold=23.0, sale_unit="MT", product=PISO_21246)
    assert result.issue is None
    assert result.computed_weight_kg == 282.8
    assert round(result.computed_volume_m3, 3) == 0.19


def test_piso_conversion_rounds_up_never_down():
    # 11,50 m2 / 2,30 = exatamente 5 -> nao deve virar 4 por erro de ponto flutuante
    result = compute_item_cubagem(quantity_sold=11.50, sale_unit="MT", product=PISO_21246)
    assert result.computed_weight_kg == 5 * 28.28

    # fracao de caixa: 11,60 m2 exige 6 caixas, nunca 5 (nao se descarta a fracao)
    result_frac = compute_item_cubagem(quantity_sold=11.60, sale_unit="MT", product=PISO_21246)
    assert result_frac.computed_weight_kg == 6 * 28.28


def test_simple_bagged_product_no_conversion():
    argamassa = {
        "id": "prod-14900",
        "code": "14900",
        "sale_unit": "UN",
        "load_unit": "UN",
        "conversion_factor": 1.0,
        "weight_kg": 15.0,
        "volume_m3": 0.009,
    }
    result = compute_item_cubagem(quantity_sold=7.0, sale_unit="UN", product=argamassa)
    assert result.computed_weight_kg == 105.0
    assert result.issue is None


def test_missing_product_blocks_without_zero():
    result = compute_item_cubagem(quantity_sold=10.0, sale_unit="UN", product=None)
    assert result.issue == "produto_sem_ficha"
    assert result.computed_weight_kg is None
    assert result.computed_volume_m3 is None


def test_missing_sale_unit_blocks_without_zero():
    result = compute_item_cubagem(quantity_sold=10.0, sale_unit=None, product=PISO_21246)
    assert result.issue == "unidade_ausente"
    assert result.computed_weight_kg is None


def test_product_without_weight_in_catalog_blocks():
    incomplete = {"id": "prod-x", "code": "X", "sale_unit": "UN", "weight_kg": None, "volume_m3": None}
    result = compute_item_cubagem(quantity_sold=1.0, sale_unit="UN", product=incomplete)
    assert result.issue == "produto_sem_ficha"
