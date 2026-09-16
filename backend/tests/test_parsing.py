from app.services import parsing


def test_parse_br_number_money():
    assert parsing.parse_br_number("R$ 3.758,40") == 3758.40


def test_parse_br_number_plain_decimal():
    assert parsing.parse_br_number("128,25") == 128.25


def test_parse_br_number_empty():
    assert parsing.parse_br_number("") is None
    assert parsing.parse_br_number(None) is None


def test_parse_br_number_extra_whitespace():
    # "espaco sobrando" citado na apresentacao: o numero tem resposta unica
    # independente de espaco extra em volta ou entre o R$ e o valor.
    assert parsing.parse_br_number("  R$   2.350,90  ") == 2350.90


def test_parse_br_date_valid():
    result = parsing.parse_br_date("01/08/2026")
    assert not result.flagged
    assert result.value.isoformat() == "2026-08-01"


def test_parse_br_date_suspicious_year_is_flagged_not_silently_fixed():
    # caso real do diagnostico: L12609909 tem 26/08/2014 num lote de 2026.
    # calendario valido (nao vira 'hoje'), mas sinalizado por estar muito
    # distante do periodo operacional — fica pendencia, nao correcao muda.
    result = parsing.parse_br_date("26/08/2014")
    assert result.flagged
    assert result.value.isoformat() == "2014-08-26"
    assert result.raw == "26/08/2014"


def test_parse_itens_resumo_single_item():
    items = parsing.parse_itens_resumo("12185 - CX. DAGUA BAKOF 1000L C/TMP (1,00 UN)")
    assert len(items) == 1
    assert items[0].code == "12185"
    assert items[0].quantity == 1.0
    assert items[0].unit == "UN"


def test_parse_itens_resumo_multiple_items_with_quoted_description():
    raw = '22931 - PISO KARINA REF. 75032 "A" 75 X 75 RET POLIDO BLACK GOLD (15,61 MT)'
    items = parsing.parse_itens_resumo(raw)
    assert len(items) == 1
    assert items[0].code == "22931"
    assert items[0].quantity == 15.61
    assert items[0].unit == "MT"


def test_parse_itens_resumo_pipe_separated():
    raw = (
        "15179 - ENGATE KRONA 50CM (1,00 UN) | "
        "8236 - ANEL JAPI DE VEDAÇAO COM GUIA P/ VASO SANIT (1,00 UN)"
    )
    items = parsing.parse_itens_resumo(raw)
    assert [i.code for i in items] == ["15179", "8236"]


def test_exclusion_crateus():
    assert parsing.exclusion_reason(city="CRATEUS", logistics_status="ENTREGUE", delivery_status="NORMAL") == (
        "entrega_urbana_crateus"
    )


def test_exclusion_crateus_with_accent():
    # bug real encontrado montando dados de demonstracao: cidade escrita com
    # acento ("Crateus" com til) nao batia contra o literal sem acento e o
    # pedido passava direto — comparacao precisa ser accent-insensitive.
    assert parsing.exclusion_reason(city="Crateús", logistics_status="Entregue", delivery_status="Entregue") == (
        "entrega_urbana_crateus"
    )


def test_exclusion_retirada_in_either_field():
    assert parsing.exclusion_reason(city="IPAPORANGA", logistics_status="ENTREGUE", delivery_status="RETIRADA") == (
        "retirada_balcao"
    )


def test_exclusion_cancelado_only_in_logistica_field():
    # o diagnostico aponta que cancelamento aparece em Logistica, nao so em Situacao —
    # filtrar so um campo perde caso.
    assert parsing.exclusion_reason(city="PORANGA", logistics_status="CANCELADO", delivery_status="NORMAL") == (
        "cancelado"
    )


def test_exclusion_cancelado_only_in_situacao_entrega_field():
    # simetrico ao teste acima: cancelamento que aparece so no campo de
    # situacao da entrega (nao em logistica) tambem precisa ser pego —
    # e' exatamente o caso que motivou ler os dois campos.
    assert parsing.exclusion_reason(city="PORANGA", logistics_status="Entregue", delivery_status="CANCELADO") == (
        "cancelado"
    )


def test_no_exclusion_for_normal_delivery():
    assert parsing.exclusion_reason(city="PORANGA", logistics_status="ENTREGUE", delivery_status="NORMAL") is None
