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

RSS_SOURCES = [
    {"name": "Transferegov", "url": "https://www.gov.br/rss.xml"},
    {"name": "Prêmio Espírito Público", "url": "https://premioespiritopublico.org.br/feed"},
    {"name": "ABIPEM", "url": "https://www.abipem.org.br/feed"},
    {"name": "Capta", "url": "https://capta.org.br/feed"}
]

def collect_rss():
    print("Iniciando coleta RSS...")
    create_db_and_tables()  # garante o schema mesmo sem o servidor ter rodado antes
    with Session(engine) as session:
        for source in RSS_SOURCES:
            print(f"\n[Coletando] {source['name']} ({source['url']})")
            try:
                feed = feedparser.parse(source['url'])
                
                # feedparser.parse não lança erro facilmente, então verificamos o bozo
                if feed.bozo and getattr(feed.bozo_exception, "getMessage", lambda: "")() != "":
                    print(f"  Aviso ao ler feed: {feed.bozo_exception}")
                
                novos_itens = 0
                for entry in feed.entries:
                    # Tratar data de publicação (RFC 822 -> datetime)
                    pub_date = None
                    if hasattr(entry, 'published'):
                        try:
                            pub_date = parsedate_to_datetime(entry.published)
                        except Exception:
                            pass

                    # A normalização cuida de limpar HTML, aparar texto e canonicalizar a URL.
                    op = normalize_opportunity(
                        title=getattr(entry, 'title', None),
                        description=getattr(entry, 'description', ""),
                        url=getattr(entry, 'link', None),
                        published_date=pub_date,
                        source=source['name'],
                    )
                    if op is None:
                        continue

                    # Verifica se a URL canônica já existe no banco (deduplicação)
                    existing = session.exec(select(Opportunity).where(Opportunity.url == op.url)).first()
                    if not existing:
                        session.add(op)
                        novos_itens += 1
                        print(f"  + Adicionado: {op.title}")
                
                session.commit()
                print(f"  > Finalizado {source['name']} - {novos_itens} novos itens salvos.")
                
            except Exception as e:
                print(f"  ! Erro crítico ao processar {source['name']}: {e}")

if __name__ == "__main__":
    collect_rss()
