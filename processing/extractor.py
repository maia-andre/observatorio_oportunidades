"""Extração de campos estruturados por regex/heurísticas — Fase 3-lite (issue #12).

**Sem LLM** (custo zero). Extrai, de texto livre de editais:
  - datas (`dd/mm/aaaa` e "DD de mês de AAAA");
  - **prazo** (data associada a termos como "inscrições até", "prazo", "encerramento");
  - **valores monetários** (`R$ ...`, com suporte a "mil"/"milhões"/"bilhões").

A heurística não é perfeita (formatos variam, PDFs ficam de fora), mas cobre uma
fatia relevante dos editais textuais a custo zero — ver `processing/enrich.py`.
"""

import re
import unicodedata
from datetime import datetime
from typing import List, Optional


def _strip_accents(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}

MULTIPLICADORES = {
    "mil": 1_000, "milhao": 1_000_000, "milhoes": 1_000_000,
    "bilhao": 1_000_000_000, "bilhoes": 1_000_000_000,
}

# Termos que sinalizam que a data próxima é um prazo (texto já sem acento).
PRAZO_KEYS = [
    "prazo", "inscrico", "inscricoes", "encerr", "submiss", "submet",
    "data limite", "data final", "vigencia", "ate o dia", "ate as", "ate ",
]

_RE_DATA_NUM = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b")
_RE_DATA_EXT = re.compile(r"\b(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})\b")
# R$ seguido de número pt-BR (1.234.567,89 / 50.000 / 500), com multiplicador opcional.
_RE_VALOR = re.compile(r"r\$\s*(\d[\d.]*(?:,\d+)?)\s*(milhoes|milhao|bilhoes|bilhao|mil)?")


def _to_date(d, m, y) -> Optional[datetime]:
    y = int(y)
    if y < 100:
        y += 2000
    try:
        return datetime(y, int(m), int(d))
    except (ValueError, TypeError):
        return None


def _parse_money_ptbr(num: str) -> Optional[float]:
    """Converte número no formato pt-BR ("1.234.567,89", "50.000", "500") em float."""
    s = num.strip().replace(" ", "")
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")  # ponto = milhar, vírgula = decimal
    else:
        s = s.replace(".", "")                     # sem vírgula: ponto é milhar
    try:
        return float(s)
    except ValueError:
        return None


def extract_dates(text: str) -> List[datetime]:
    """Todas as datas reconhecidas no texto (numéricas e por extenso)."""
    t = _strip_accents((text or "").lower())
    datas = []
    for d, m, y in _RE_DATA_NUM.findall(t):
        dt = _to_date(d, m, y)
        if dt:
            datas.append(dt)
    for d, mes_nome, y in _RE_DATA_EXT.findall(t):
        m = MESES.get(mes_nome)
        if m:
            dt = _to_date(d, m, y)
            if dt:
                datas.append(dt)
    return datas


def extract_values(text: str) -> List[float]:
    """Todos os valores monetários (R$) reconhecidos, já com multiplicadores aplicados."""
    t = _strip_accents((text or "").lower())
    valores = []
    for num, mult in _RE_VALOR.findall(t):
        v = _parse_money_ptbr(num)
        if v is None:
            continue
        if mult:
            v *= MULTIPLICADORES.get(mult, 1)
        valores.append(v)
    return valores


def extract_deadline(text: str) -> Optional[datetime]:
    """Heurística de prazo: data que aparece logo após um termo de prazo.

    Quando há várias candidatas, retorna a **mais distante** (data de encerramento
    costuma ser a última citada).
    """
    t = _strip_accents((text or "").lower())
    candidatas = []
    for key in PRAZO_KEYS:
        inicio = 0
        while True:
            idx = t.find(key, inicio)
            if idx == -1:
                break
            inicio = idx + len(key)
            janela = t[idx: idx + 80]  # olha logo após a palavra-chave
            m = _RE_DATA_NUM.search(janela)
            if m:
                dt = _to_date(*m.groups())
            else:
                m = _RE_DATA_EXT.search(janela)
                dt = _to_date(m.group(1), MESES.get(m.group(2)), m.group(3)) if m else None
            if dt:
                candidatas.append(dt)
    return max(candidatas) if candidatas else None


def extract_max_value(text: str) -> Optional[float]:
    """Maior valor monetário do texto (em geral o teto/total do edital)."""
    valores = extract_values(text)
    return max(valores) if valores else None
