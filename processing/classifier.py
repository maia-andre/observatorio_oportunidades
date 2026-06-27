"""Motor de Classificação por regras — Fase 2 (issues #6 e #8).

Script autônomo (mesmo padrão dos coletores: executável por cron/CI, desacoplado
da API). Varre as oportunidades pendentes (`category IS NULL`), atribui uma
categoria com base nas palavras-chave de `processing/rules.py` e atualiza o
`status`. É um passo separado da coleta e re-executável.
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
from processing.rules import RULES


def _normalize(texto: str) -> str:
    """Texto em minúsculas e sem acento, para casar com as palavras-chave."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def classify_text(title: str, description: Optional[str] = None) -> Optional[str]:
    """Retorna a primeira categoria cuja palavra-chave aparece no texto, ou None."""
    texto = _normalize(f"{title or ''} {description or ''}")
    for categoria, palavras in RULES.items():
        if any(palavra in texto for palavra in palavras):
            return categoria
    return None


def reset_classification() -> int:
    """Zera a classificação (category=None, status="novo") de todos os registros.

    Útil para **reclassificar do zero** após alterar as regras (`rules.py`),
    já que `classify_pending` só processa itens com `category IS NULL`.
    Retorna a quantidade de registros resetados.
    """
    create_db_and_tables()
    with Session(engine) as session:
        ops = session.exec(select(Opportunity)).all()
        for op in ops:
            op.category = None
            op.status = "novo"
            session.add(op)
        session.commit()
    return len(ops)


def classify_pending() -> dict:
    """Classifica as oportunidades com `category IS NULL` e atualiza o status.

    - com match  → category = X, status = "classificado"
    - sem match  → status = "nao_classificado" (visível no painel p/ curadoria)

    Idempotente: itens já classificados (category preenchida) são ignorados.
    Retorna um resumo com as contagens.
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
            categoria = classify_text(op.title, op.description)
            if categoria:
                op.category = categoria
                op.status = "classificado"
                resumo["classificado"] += 1
                resumo["por_categoria"][categoria] = resumo["por_categoria"].get(categoria, 0) + 1
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
