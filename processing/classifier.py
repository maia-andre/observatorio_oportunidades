"""Motor de Classificação por regras — Fase 2 + Etapa B/B1b (ponderado, multi-rótulo).

Script autônomo (mesmo padrão dos coletores). Varre as oportunidades relevantes
ainda sem categoria, pontua cada categoria pelas palavras-chave de
`processing/rules.py` (com vetos de `NEGATIVES`) e atribui:
  - `category`   = categoria de maior score (desempate pela prioridade/ordem do RULES);
  - `categories` = todas as categorias com score, ordenadas por score (multi-rótulo);
  - `status`     = "classificado" | "nao_classificado".

Termos compostos (com espaço) pesam mais (2) por serem mais específicos que os
simples (1). É um passo separado da coleta, idempotente e re-executável.
"""

import os
import sys
import unicodedata
from typing import Optional

# Adiciona a raiz do projeto ao sys.path para importar o backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from backend.database import engine, create_db_and_tables
from backend.models import Opportunity
from processing.rules import RULES, NEGATIVES

_ORDEM = {c: i for i, c in enumerate(RULES)}  # prioridade = ordem de inserção no RULES


def _normalize(texto: str) -> str:
    """Texto em minúsculas e sem acento, para casar com as palavras-chave."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def classify_scored(title: str, description: Optional[str] = None):
    """Retorna (categoria_principal, [categorias por score desc]).

    Pontua cada categoria pelo nº de palavras-chave presentes (termo composto = 2,
    simples = 1). `NEGATIVES` veta a categoria inteira. Sem match → (None, []).
    """
    texto = _normalize(f"{title or ''} {description or ''}")
    if not texto.strip():
        return None, []

    scores = {}
    for categoria, palavras in RULES.items():
        if any(neg in texto for neg in NEGATIVES.get(categoria, ())):
            continue
        s = sum(2 if " " in p else 1 for p in palavras if p in texto)
        if s:
            scores[categoria] = s
    if not scores:
        return None, []

    ranked = sorted(scores, key=lambda c: (-scores[c], _ORDEM[c]))
    return ranked[0], ranked


def classify_text(title: str, description: Optional[str] = None) -> Optional[str]:
    """Apenas a categoria principal (mantido por compatibilidade)."""
    return classify_scored(title, description)[0]


def reset_classification() -> int:
    """Zera category/categories (=None) e status (="novo") de todos os registros.

    Útil para reclassificar do zero após alterar regras. Retorna a quantidade.
    """
    create_db_and_tables()
    with Session(engine) as session:
        ops = session.exec(select(Opportunity)).all()
        for op in ops:
            op.category = None
            op.categories = None
            op.status = "novo"
            session.add(op)
        session.commit()
    return len(ops)


def classify_pending() -> dict:
    """Classifica as oportunidades relevantes sem categoria e atualiza o status.

    - com match  → category/categories preenchidos, status = "classificado"
    - sem match  → status = "nao_classificado" (visível no painel p/ curadoria)
    Só processa relevantes (status != "irrelevante"). Idempotente.
    """
    create_db_and_tables()
    resumo = {"classificado": 0, "nao_classificado": 0, "por_categoria": {}}

    with Session(engine) as session:
        # Só classifica o que passou pela porta de relevância (status != "irrelevante").
        pendentes = session.exec(
            select(Opportunity).where(
                Opportunity.category.is_(None),
                Opportunity.status != "irrelevante",
            )
        ).all()
        print(f"Classificando {len(pendentes)} oportunidade(s) pendente(s)...")

        for op in pendentes:
            principal, ranked = classify_scored(op.title, op.description)
            if principal:
                op.category = principal
                op.categories = ",".join(ranked)
                op.status = "classificado"
                resumo["classificado"] += 1
                resumo["por_categoria"][principal] = resumo["por_categoria"].get(principal, 0) + 1
            else:
                op.status = "nao_classificado"
                resumo["nao_classificado"] += 1
            session.add(op)

        session.commit()

    return resumo


if __name__ == "__main__":
    # `--reset` reclassifica tudo do zero (após mudar as regras).
    if "--reset" in sys.argv:
        n = reset_classification()
        print(f"Classificação zerada em {n} registro(s).")

    r = classify_pending()
    print(f"\n> Classificadas: {r['classificado']} | Não classificadas: {r['nao_classificado']}")
    for cat, n in sorted(r["por_categoria"].items(), key=lambda x: -x[1]):
        print(f"   - {cat}: {n}")
