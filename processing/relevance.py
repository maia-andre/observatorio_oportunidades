"""Porta de relevância por regras — Etapa A (issues #3/#4), SEM LLM.

Nem tudo que os coletores trazem é uma "oportunidade": feeds genéricos (ex.: o RSS
do gov.br) e blogs institucionais publicam muita notícia comum. Esta camada pontua
cada item por SINAIS de oportunidade (termos como "edital/inscrições/chamada",
presença de valor em R$, presença de prazo, e a confiança da fonte) e marca como
`irrelevante` o que fica abaixo do limiar — assim o painel mostra sinal, não ruído.

Determinística e barata: reutiliza o `processing/extractor` para detectar valor/prazo.
Script autônomo (mesmo padrão dos coletores), re-executável e idempotente.
"""

import os
import sys
import unicodedata
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from backend.database import engine, create_db_and_tables
from backend.models import Opportunity
from processing.extractor import extract_deadline, extract_max_value

# Limiar padrão: itens com score < LIMIAR viram "irrelevante".
LIMIAR = 0.5

# Sinais textuais ponderados (sem acento, minúsculas — casados por substring).
TERMOS_FORTES = {  # cara de oportunidade aberta / processo seletivo
    "edital", "chamada publica", "chamada aberta", "chamamento", "termo de fomento",
    "inscricoes abertas", "submissao de propostas", "selecao de projetos", "selecao publica",
    "credenciamento", "concurso de projetos", "fomento a", "carta convite",
}
TERMOS_MEDIOS = {  # vocabulário recorrente de oportunidades
    "inscricoes", "inscricao", "premio", "premiacao", "convenio", "bolsa", "bolsas",
    "financiamento", "fomento", "concurso", "selo", "certificacao", "acreditacao",
    "chamada", "patrocinio", "subvencao", "captacao de recursos", "prestacao de contas",
}
TERMOS_FRACOS = {  # sugerem, mas não bastam sozinhos
    "programa", "oportunidade", "projeto", "recursos", "apoio", "iniciativa", "parceria",
}

# Fontes estruturadas/curadas que são quase 100% oportunidade: ganham base de confiança.
FONTES_CONFIAVEIS = {
    "PNCP", "PNCP-API", "Querido Diário", "Portal da Transparência", "Capta", "Prosas",
    "Prêmio Espírito Público", "Congresso Nacional",
}

PESOS = {
    "forte": 1.0, "medio": 0.6, "fraco": 0.3,
    "valor": 0.5, "prazo": 0.4, "fonte": 0.3,
}


def _normalize(texto: str) -> str:
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def score_relevance(title: str, description: Optional[str] = None,
                    source: Optional[str] = None) -> float:
    """Pontua o item em 0..1 somando sinais de oportunidade (saturado em 1.0)."""
    texto = _normalize(f"{title or ''} {description or ''}")
    if not texto.strip():
        return 0.0

    score = 0.0
    if any(t in texto for t in TERMOS_FORTES):
        score += PESOS["forte"]
    if any(t in texto for t in TERMOS_MEDIOS):
        score += PESOS["medio"]
    if any(t in texto for t in TERMOS_FRACOS):
        score += PESOS["fraco"]

    # Sinais estruturais reaproveitando o extrator (valor em R$ / prazo).
    if extract_max_value(texto) is not None:
        score += PESOS["valor"]
    if extract_deadline(texto) is not None:
        score += PESOS["prazo"]

    if source in FONTES_CONFIAVEIS:
        score += PESOS["fonte"]

    return min(1.0, round(score, 3))


def apply_relevance(limiar: float = LIMIAR, rescore: bool = False) -> dict:
    """Avalia os itens ainda não pontuados (ou todos, se `rescore`) e marca irrelevantes.

    - score >= limiar → mantém status atual (segue para a classificação);
    - score <  limiar → status = "irrelevante" (oculto no painel por padrão).
    Itens já classificados não são rebaixados a menos que `rescore=True`.
    """
    create_db_and_tables()
    resumo = {"relevante": 0, "irrelevante": 0, "avaliados": 0}

    with Session(engine) as session:
        stmt = select(Opportunity)
        if not rescore:
            stmt = stmt.where(Opportunity.relevance_score.is_(None))
        itens = session.exec(stmt).all()

        for op in itens:
            s = score_relevance(op.title, op.description, op.source)
            op.relevance_score = s
            resumo["avaliados"] += 1
            if s < limiar:
                op.status = "irrelevante"
                resumo["irrelevante"] += 1
            else:
                # Se estava marcado irrelevante num passe anterior, reabilita.
                if op.status == "irrelevante":
                    op.status = "novo"
                resumo["relevante"] += 1
            session.add(op)

        session.commit()

    return resumo


if __name__ == "__main__":
    rescore = "--rescore" in sys.argv
    limiar = LIMIAR
    for arg in sys.argv[1:]:
        if arg.startswith("--limiar="):
            limiar = float(arg.split("=", 1)[1])
    r = apply_relevance(limiar=limiar, rescore=rescore)
    print(f"> Avaliados: {r['avaliados']} | Relevantes: {r['relevante']} | Irrelevantes: {r['irrelevante']}")
