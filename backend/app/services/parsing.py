"""Parsing de numero brasileiro e do campo Itens_Resumo dos CSVs da Nobre Lar.

Nada aqui conhece nome de cidade, veiculo ou produto especifico — so regras
de formato (como o Brasil escreve numero, como aquele CSV concatena itens).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

_MONEY_RE = re.compile(r"[^\d,.\-]")
_ITEM_RE = re.compile(
    r"^\s*(?P<code>\d+)\s*-\s*(?P<description>.+?)\s*"
    r"\((?P<quantity>[\d.,]+)\s*(?P<unit>[A-Za-zÀ-ÿ0-9²³/]+)\)\s*$"
)


def parse_br_number(raw: str | float | int | None) -> float | None:
    """Converte '1.234,56' ou 'R$ 412,00' em 1234.56. None se vazio/invalido."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = _MONEY_RE.sub("", raw).strip()
    if not text:
        return None
    # formato BR: ponto separa milhar, virgula e decimal.
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


@dataclass
class ParsedDate:
    value: date | None
    raw: str
    flagged: bool
    note: str | None = None


def parse_br_date(raw: str | None, *, today: date | None = None) -> ParsedDate:
    """dd/mm/aaaa (ou dd/mm/aa). Nunca vira 'hoje' quando invalida — fica
    sinalizada, com o texto original preservado, para virar pendencia."""
    today = today or date.today()
    if not raw or not raw.strip():
        return ParsedDate(value=None, raw=raw or "", flagged=True, note="data ausente")

    text = raw.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            parsed = datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        if parsed.year < 2000 or parsed > date(today.year + 1, 12, 31):
            return ParsedDate(
                value=None, raw=text, flagged=True,
                note=f"ano fora da faixa esperada ({parsed.year})",
            )
        if parsed.year < today.year - 3:
            # calendario valido, mas muito distante do periodo operacional
            # atual (caso real: L12609909 com data de 2014 num lote de 2026).
            # Preserva o valor (nao e' impossivel), so sinaliza para revisao.
            return ParsedDate(
                value=parsed, raw=text, flagged=True,
                note=f"data muito anterior ao periodo atual ({parsed.year}), confirmar antes de usar",
            )
        return ParsedDate(value=parsed, raw=text, flagged=False)

    return ParsedDate(value=None, raw=text, flagged=True, note="formato de data nao reconhecido")


@dataclass
class ParsedItem:
    code: str
    description: str
    quantity: float
    unit: str | None


def parse_itens_resumo(raw: str | None) -> list[ParsedItem]:
    """'12185 - CX DAGUA (1,00 UN) | 21503 - CIMENTO (80,00 UN)' -> itens.

    Item que nao casa com o formato esperado ainda assim e' preservado
    (quantidade None, unidade None) em vez de descartado silenciosamente —
    quem chama decide virar pendencia, nunca perder o registro.
    """
    if not raw or not raw.strip():
        return []

    items: list[ParsedItem] = []
    for chunk in raw.split(" | "):
        chunk = chunk.strip()
        if not chunk:
            continue
        match = _ITEM_RE.match(chunk)
        if not match:
            items.append(ParsedItem(code="", description=chunk, quantity=0.0, unit=None))
            continue
        qty = parse_br_number(match.group("quantity")) or 0.0
        items.append(
            ParsedItem(
                code=match.group("code").strip(),
                description=match.group("description").strip(),
                quantity=qty,
                unit=match.group("unit").strip().upper(),
            )
        )
    return items


def normalize_city(raw: str | None) -> str:
    if not raw:
        return ""
    return " ".join(raw.strip().upper().split())


def normalize_city_key(raw: str | None) -> str:
    """Como normalize_city, mas tambem remove acento — usado so como CHAVE
    de correspondencia entre fontes com convencoes diferentes (CSV da
    operacao vem sem acento e tudo maiusculo; cadastro de cidades/geocoding
    vem com acento e nome proprio). O valor exibido ao usuario continua
    vindo de normalize_city ou do cadastro, nunca desta funcao."""
    import unicodedata

    text = normalize_city(raw)
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


_EXCLUDE_KEYWORDS = ("RETIRADA", "CANCELAD")


def exclusion_reason(*, city: str, logistics_status: str | None, delivery_status: str | None) -> str | None:
    """Cidade Crateus, retirada e cancelamento ficam fora do recorte do
    desafio. Cancelamento pode aparecer em qualquer um dos dois campos de
    status — filtrar so um deles perde caso, como o diagnostico apontou."""
    if normalize_city(city) == "CRATEUS":
        return "entrega_urbana_crateus"

    fields = [f for f in (logistics_status, delivery_status) if f]
    upper_fields = [f.strip().upper() for f in fields]

    for field in upper_fields:
        if "RETIRADA" in field:
            return "retirada_balcao"
    for field in upper_fields:
        if "CANCELAD" in field:
            return "cancelado"
    return None


def is_delivered(*, logistics_status: str | None, delivery_status: str | None) -> bool:
    fields = [f.strip().upper() for f in (logistics_status, delivery_status) if f]
    return any("ENTREGUE" in f for f in fields)
