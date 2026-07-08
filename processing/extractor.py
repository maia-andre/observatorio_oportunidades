"""Extração de campos estruturados por regex/heurísticas — Fase 3-lite (issue #12).

**Sem LLM** (custo zero). Extrai, de texto livre de editais:
  - datas (`dd/mm/aaaa` e "DD de mês de AAAA");
  - **prazo** (data associada a termos como "inscrições até", "prazo", "encerramento");
  - **valores monetários** (`R$ ...`, com "mil"/"milhões"/"bilhões" e as abreviações
    "Mi"/"MM"/"Bi"; ignora faixas de receita/faturamento do público-alvo, que são
    critério de elegibilidade e não valor da oportunidade).

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
    # Abreviações usuais em editais e listagens ("R$ 4,8 Mi", "R$ 2 MM", "R$ 1 Bi").
    "mi": 1_000_000, "mm": 1_000_000, "bi": 1_000_000_000,
}

# Um R$ precedido destes termos (janela curta) é faixa de receita/faturamento do
# público-alvo — elegibilidade, não o valor da oportunidade (ex.: chamadas FINEP:
# "Receita: até R$ 4,8 Mi, ... maior que R$ 300,0 Mi").
CONTEXTOS_NAO_VALOR = ("receita", "faturamento")
_JANELA_CONTEXTO = 40

# Termos que sinalizam que a data próxima é um prazo (texto já sem acento).
PRAZO_KEYS = [
    "prazo", "inscrico", "inscricoes", "encerr", "submiss", "submet",
    "data limite", "data final", "vigencia", "ate o dia", "ate as", "ate ",
]

_RE_DATA_NUM = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b")
_RE_DATA_EXT = re.compile(r"\b(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})\b")
# R$ seguido de número pt-BR (1.234.567,89 / 50.000 / 500), com multiplicador
# opcional — por extenso ou abreviado. "mil" antes de "mi" na alternância (senão
# "300 mil" casaria "mi"); o \b final impede falso multiplicador em palavra maior
# (ex.: "R$ 300 milhas" não vira 300 milhões... e "minutos" não vira "mi").
_RE_VALOR = re.compile(r"r\$\s*(\d[\d.]*(?:,\d+)?)\s*(milhoes|milhao|bilhoes|bilhao|mil|mi|mm|bi)?\b")


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
    """Todos os valores monetários (R$) reconhecidos, já com multiplicadores aplicados.

    Valores em contexto de receita/faturamento (janela curta antes do match) são
    descartados: são o porte das empresas elegíveis, não o valor da oportunidade.
    """
    t = _strip_accents((text or "").lower())
    valores = []
    for m in _RE_VALOR.finditer(t):
        contexto = t[max(0, m.start() - _JANELA_CONTEXTO):m.start()]
        if any(k in contexto for k in CONTEXTOS_NAO_VALOR):
            continue
        v = _parse_money_ptbr(m.group(1))
        if v is None:
            continue
        if m.group(2):
            v *= MULTIPLICADORES.get(m.group(2), 1)
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
