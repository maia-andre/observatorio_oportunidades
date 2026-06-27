"""Coletor RSS — lê as fontes do registro central `collectors/sources.py`.

Mesmo padrão autônomo de antes (executável por cron/CI, garante o schema), mas as
fontes não são mais uma lista fixa aqui: vêm de `enabled_sources("rss")`, então
adicionar/remover feed é só editar o registro. Constrói as oportunidades via
`normalize_opportunity` e deduplica pela URL canônica.
"""

import os
import sys
import feedparser
from email.utils import parsedate_to_datetime

# Adiciona a raiz do projeto ao sys.path para importar o backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlmodel import Session, select
from backend.database import engine, create_db_and_tables
from backend.models import Opportunity
from processing.normalizer import normalize_opportunity
from collectors.sources import enabled_sources


def collect_rss():
    fontes = enabled_sources("rss")
    print(f"Iniciando coleta RSS ({len(fontes)} feed(s) habilitado(s))...")
    create_db_and_tables()  # garante o schema mesmo sem o servidor ter rodado antes
    total_novos = 0
    with Session(engine) as session:
        for source in fontes:
            print(f"\n[Coletando] {source['name']} ({source['url']})")
            try:
                feed = feedparser.parse(source["url"])

                # feedparser.parse não lança erro facilmente, então verificamos o bozo
                if feed.bozo and getattr(feed.bozo_exception, "getMessage", lambda: "")() != "":
                    print(f"  Aviso ao ler feed: {feed.bozo_exception}")

                if not feed.entries:
                    print("  - Feed sem itens (pulando).")
                    continue

                novos_itens = 0
                for entry in feed.entries:
                    # Tratar data de publicação (RFC 822 -> datetime)
                    pub_date = None
                    if hasattr(entry, "published"):
                        try:
                            pub_date = parsedate_to_datetime(entry.published)
                        except Exception:
                            pass

                    # A normalização cuida de limpar HTML, aparar texto e canonicalizar a URL.
                    op = normalize_opportunity(
                        title=getattr(entry, "title", None),
                        description=getattr(entry, "description", ""),
                        url=getattr(entry, "link", None),
                        published_date=pub_date,
                        source=source["name"],
                    )
                    if op is None:
                        continue

                    # Verifica se a URL canônica já existe no banco (deduplicação)
                    existing = session.exec(select(Opportunity).where(Opportunity.url == op.url)).first()
                    if not existing:
                        session.add(op)
                        novos_itens += 1

                session.commit()
                total_novos += novos_itens
                print(f"  > Finalizado {source['name']} - {novos_itens} novos itens salvos.")

            except Exception as e:
                print(f"  ! Erro crítico ao processar {source['name']}: {e}")

    print(f"\n> RSS: {total_novos} novo(s) item(ns) no total.")
    return total_novos


if __name__ == "__main__":
    collect_rss()
