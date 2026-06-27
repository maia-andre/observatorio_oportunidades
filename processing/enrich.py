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
from collections import Counter, defaultdict

import requests
from bs4 import BeautifulSoup

try:
    import fitz  # PyMuPDF — extração de texto de PDFs
except ImportError:
    fitz = None

# Adiciona a raiz do projeto ao sys.path para importar o backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from backend.database import engine, create_db_and_tables
from backend.models import Opportunity
from processing.extractor import extract_deadline, extract_max_value

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ObservatorioBot/1.0"}

# Fontes estruturadas: valor/prazo vêm de API autoritativa, então ficam FORA da
# limpeza de contaminação (que só faz sentido para o que foi extraído de páginas).
FONTES_ESTRUTURADAS = {"PNCP", "Portal da Transparência"}


def _extract_pdf_text(content: bytes, max_paginas: int = 20) -> str:
    """Texto das primeiras páginas de um PDF via PyMuPDF (vazio se indisponível)."""
    if fitz is None:
        return ""
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception:
        return ""
    partes = []
    for i, page in enumerate(doc):
        if i >= max_paginas:
            break
        partes.append(page.get_text())
    doc.close()
    return " ".join(partes)


def _fetch_text(url: str, timeout: int = 15):
    """Baixa o link e devolve o texto do **conteúdo principal** (HTML ou PDF).

    Editais costumam ser PDF: quando o conteúdo é PDF (Content-Type ou extensão),
    extrai o texto com PyMuPDF. Para HTML, remove script/style e blocos estruturais
    (nav/header/footer/aside) e prefere `<main>`/`<article>` ao `<body>` inteiro —
    reduz a contaminação por boilerplate (menus, rodapés, "editais relacionados").
    """
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    if resp.status_code != 200:
        return None

    ctype = resp.headers.get("Content-Type", "").lower()
    if "application/pdf" in ctype or url.lower().split("?")[0].endswith(".pdf"):
        return _extract_pdf_text(resp.content)

    soup = BeautifulSoup(resp.content, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside"]):
        tag.decompose()
    principal = soup.find("main") or soup.find("article") or soup.body or soup
    return principal.get_text(separator=" ")


def drop_contaminated_enrichment(min_repeticoes: int = 3):
    """Anula prazo/valor que se repetem em >= min_repeticoes itens da MESMA fonte.

    Páginas de listagem (ex.: Capta) repetem o prazo/valor de um item em destaque,
    contaminando vários editais distintos com o mesmo dado. Um valor/prazo idêntico
    em muitos itens da mesma fonte é quase certamente boilerplate — melhor não ter o
    dado do que tê-lo errado. Não toca em FONTES_ESTRUTURADAS (valor/prazo de API).
    Retorna (qtd_valores_anulados, qtd_prazos_anulados).
    """
    create_db_and_tables()
    nulos_v = nulos_d = 0
    with Session(engine) as session:
        por_fonte = defaultdict(list)
        for o in session.exec(select(Opportunity)).all():
            if o.source not in FONTES_ESTRUTURADAS:
                por_fonte[o.source].append(o)
        for items in por_fonte.values():
            cont_v = {v for v, c in Counter(o.value for o in items if o.value is not None).items()
                      if c >= min_repeticoes}
            cont_d = {d for d, c in Counter(o.deadline for o in items if o.deadline is not None).items()
                      if c >= min_repeticoes}
            for o in items:
                if o.value in cont_v:
                    o.value = None
                    nulos_v += 1
                    session.add(o)
                if o.deadline in cont_d:
                    o.deadline = None
                    nulos_d += 1
                    session.add(o)
        session.commit()
    return nulos_v, nulos_d


def enrich(limit: int = 20, source: str = None, only_missing: bool = True) -> int:
    create_db_and_tables()
    atualizados = 0

    with Session(engine) as session:
        # Só enriquece itens relevantes (não desperdiça fetch com o que foi filtrado).
        stmt = select(Opportunity).where(Opportunity.status != "irrelevante")
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

    nv, nd = drop_contaminated_enrichment()
    if nv or nd:
        print(f"> Contaminação removida: {nv} valor(es) e {nd} prazo(s) anulados (boilerplate de listagem).")
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
