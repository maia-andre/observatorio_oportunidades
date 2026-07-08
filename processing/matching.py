"""Motor de matching municipal — Etapa C (C2), SEM LLM.

Pontua a aderência de uma oportunidade ao perfil de um município em 0–100, de forma
determinística e interpretável (overlap de categorias/keywords + localidade + prazo
em aberto). Devolve também a justificativa (quais sinais bateram), para o painel.

Sem dependência nova: usa só normalização de texto e comparação de conjuntos.
"""

import unicodedata
from datetime import datetime
from typing import List, Tuple

from backend.models import Opportunity, MunicipalProfile

# Pesos dos sinais (a soma satura em 100).
PESO_CATEGORIA = 30   # por categoria de interesse que casa (até 2 contam)
PESO_MUNICIPIO = 25   # oportunidade cita o nome do município
PESO_UF = 10          # mesma UF (quando não cita o município)
PESO_KEYWORD = 8      # por termo de interesse presente no texto (até 2 contam)
PESO_SECRETARIA = 15  # secretaria sugerida pela curadoria casa com interesse
PESO_ABERTURA = 10    # prazo em aberto (futuro)
PESO_VENCIDA = 25     # penalidade: prazo já vencido (não acionável)


def _norm(texto: str) -> str:
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _interesses(profile: MunicipalProfile) -> set:
    """Conjunto de interesses normalizados a partir do campo `interests`."""
    return {_norm(t).strip() for t in (profile.interests or "").split(",") if t.strip()}


def score_match(op: Opportunity, profile: MunicipalProfile) -> Tuple[int, List[str]]:
    """Aderência (0–100) da oportunidade `op` ao `profile`, com justificativa."""
    interesses = _interesses(profile)
    justificativa: List[str] = []
    score = 0

    # Categorias da oportunidade (principal + secundárias do multi-rótulo).
    op_cats = set()
    if op.category:
        op_cats.add(_norm(op.category))
    if op.categories:
        op_cats |= {_norm(c) for c in op.categories.split(",") if c.strip()}

    # 1) Sobreposição de categorias com os interesses (sinal mais forte).
    cats_match = op_cats & interesses
    if cats_match:
        score += min(2, len(cats_match)) * PESO_CATEGORIA
        justificativa.append("categoria de interesse: " + ", ".join(sorted(cats_match)))

    # 2) Localidade: cita o município, ou ao menos a mesma UF.
    texto = _norm(f"{op.title} {op.description or ''}")
    uf = _norm(profile.uf)
    if _norm(profile.name) and _norm(profile.name) in texto:
        score += PESO_MUNICIPIO
        justificativa.append(f"cita o município ({profile.name})")
    elif uf and (f"/{uf}" in texto or f" {uf} " in texto):
        score += PESO_UF
        justificativa.append(f"mesma UF ({profile.uf})")

    # 3) Termos de interesse presentes no texto (que não casaram como categoria).
    kw_match = {t for t in interesses
                if t and t not in cats_match and len(t) > 3 and t in texto}
    if kw_match:
        score += min(2, len(kw_match)) * PESO_KEYWORD
        justificativa.append("termos de interesse: " + ", ".join(sorted(kw_match)))

    # 3.5) Secretaria sugerida pela curadoria LLM casa com interesse do perfil.
    # Contenção nos dois sentidos para casar "inovacao" ⊆ "inovacao e tecnologia".
    # Sem curadoria (department nulo) o sinal simplesmente não existe — o núcleo
    # do matching segue determinístico. Pode reforçar o sinal de categoria (dois
    # sistemas independentes concordando é aderência maior mesmo).
    if op.department:
        dep = _norm(op.department)
        if any(t in dep or dep in t for t in interesses if len(t) > 3):
            score += PESO_SECRETARIA
            justificativa.append(f"secretaria sugerida ({op.department}) é de interesse")

    # 4) Prazo: em aberto soma (acionável agora); vencido penaliza (não acionável).
    if op.deadline and op.deadline >= datetime.now():
        score += PESO_ABERTURA
        justificativa.append("prazo em aberto")
    elif op.deadline:
        score -= PESO_VENCIDA
        justificativa.append("prazo vencido")

    return max(0, min(100, score)), justificativa


def rank_opportunities(profile: MunicipalProfile, ops: List[Opportunity]):
    """Anota cada oportunidade com (score, justificativa) e ordena por score desc."""
    anotadas = [(op, *score_match(op, profile)) for op in ops]
    anotadas.sort(key=lambda t: t[1], reverse=True)
    return anotadas  # lista de (op, score, justificativa)
