import os
import sys
import feedparser
from datetime import datetime
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

# Adiciona a raiz do projeto ao sys.path para importar o backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlmodel import Session, select
from backend.database import engine
from backend.models import Opportunity

RSS_SOURCES = [
    {"name": "Transferegov", "url": "https://www.gov.br/rss.xml"},
    {"name": "Prêmio Espírito Público", "url": "https://premioespiritopublico.org.br/feed"},
    {"name": "ABIPEM", "url": "https://www.abipem.org.br/feed"},
    {"name": "Capta", "url": "https://capta.org.br/feed"}
]

def clean_html(raw_html):
    """Remove as tags HTML do conteúdo para ficar limpo no banco."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ").strip()

def collect_rss():
    print("Iniciando coleta RSS...")
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
                    # Tratar data de publicação
                    pub_date = None
                    if hasattr(entry, 'published'):
                        try:
                            # Tenta converter a data de RFC 822 para datetime
                            pub_date = parsedate_to_datetime(entry.published)
                            pub_date = pub_date.replace(tzinfo=None) # remove tzinfo para manter simples no banco
                        except Exception:
                            pass
                    
                    title = getattr(entry, 'title', "Sem Título")
                    link = getattr(entry, 'link', None)
                    description = clean_html(getattr(entry, 'description', ""))
                    
                    if not link:
                        continue
                        
                    # Verifica se a URL já existe no banco (deduplicação)
                    existing = session.exec(select(Opportunity).where(Opportunity.url == link)).first()
                    if not existing:
                        op = Opportunity(
                            title=title,
                            description=description,
                            url=link,
                            published_date=pub_date,
                            source=source['name']
                        )
                        session.add(op)
                        novos_itens += 1
                        print(f"  + Adicionado: {title}")
                
                session.commit()
                print(f"  > Finalizado {source['name']} - {novos_itens} novos itens salvos.")
                
            except Exception as e:
                print(f"  ! Erro crítico ao processar {source['name']}: {e}")

if __name__ == "__main__":
    collect_rss()
