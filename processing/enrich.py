"""Enriquecimento por "fetch profundo" — Fase 3-lite (issue #12).

Para oportunidades ainda não enriquecidas, baixa o conteúdo do link, extrai
**prazo** (`deadline`) e **valor** (`value`) via `processing/extractor` e atualiza
o banco. **Sem LLM.** Re-executável; processa em lotes para ser educado com as fontes.

Uso (a partir da raiz do projeto):
    python processing/enrich.py                      # ate 20 itens ainda sem prazo/valor
    python processing/enrich.py --limit=10
    python processing/enrich.py --source=Capta       # foca numa fonte (ex.: editais)
"""

import os
import sys

import requests
from bs4 import BeautifulSoup

# Adiciona a raiz do projeto ao sys.path para importar o backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from backend.database import engine, create_db_and_tables
from backend.models import Opportunity
from processing.extractor import extract_deadline, extract_max_value

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ObservatorioBot/1.0"}


def _fetch_text(url: str, timeout: int = 15):
    """Baixa a página e devolve o texto do **conteúdo principal**.

    Remove script/style e blocos estruturais (nav/header/footer/aside) e prefere
    `<main>`/`<article>` ao `<body>` inteiro — isso reduz a contaminação por
    boilerplate (menus, rodapés, "editais relacionados") que, na extração ingênua
    de página inteira, fazia páginas distintas devolverem o mesmo valor/prazo.
    """
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    if resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.content, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside"]):
        tag.decompose()
    principal = soup.find("main") or soup.find("article") or soup.body or soup
    return principal.get_text(separator=" ")


def enrich(limit: int = 20, source: str = None, only_missing: bool = True) -> int:
    create_db_and_tables()
    atualizados = 0

    with Session(engine) as session:
        stmt = select(Opportunity)
        if only_missing:
            stmt = stmt.where(Opportunity.deadline.is_(None), Opportunity.value.is_(None))
        if source:
            stmt = stmt.where(Opportunity.source == source)
        ops = session.exec(stmt.limit(limit)).all()

        print(f"Enriquecendo até {len(ops)} oportunidade(s)"
              + (f" da fonte '{source}'" if source else "") + "...")

        for op in ops:
            try:
                texto = _fetch_text(op.url)
            except Exception as e:
                print(f"  ! erro em {op.url[:60]}: {e}")
                continue
            if not texto:
                continue

            # Combina a descrição já existente com o conteúdo baixado.
            base = f"{op.description or ''} {texto}"
            prazo = extract_deadline(base)
            valor = extract_max_value(base)

            if prazo or valor:
                op.deadline = prazo or op.deadline
                op.value = valor or op.value
                session.add(op)
                atualizados += 1
                prazo_str = prazo.strftime("%d/%m/%Y") if prazo else "-"
                valor_str = f"R$ {valor:,.2f}" if valor else "-"
                print(f"  + {op.title[:45]:45} | prazo={prazo_str} | valor={valor_str}")

        session.commit()

    print(f"\n> {atualizados} oportunidade(s) enriquecida(s).")
    return atualizados


if __name__ == "__main__":
    limit = 20
    source = None
    for arg in sys.argv[1:]:
        if arg.startswith("--limit="):
            limit = int(arg.split("=", 1)[1])
        elif arg.startswith("--source="):
            source = arg.split("=", 1)[1]
    enrich(limit=limit, source=source)
