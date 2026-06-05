import os
import sys
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# Adiciona a raiz do projeto ao sys.path para importar o backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlmodel import Session, select
from backend.database import engine
from backend.models import Opportunity

API_SOURCES = [
    {"name": "Portal da Transparência", "url": "https://api.portaldatransparencia.gov.br/api-de-dados/emendas", "type": "json"},
    {"name": "Conexão Inovação", "url": "https://www.conexaoinovacaopublica.org/sitemap.xml", "type": "sitemap"},
    {"name": "Google Education", "url": "https://edu.google.com/sitemap.xml", "type": "sitemap"},
    {"name": "ENAP", "url": "https://enap.gov.br/sitemap.xml", "type": "sitemap"}
]

def collect_api():
    print("Iniciando coleta API/Sitemap...")
    with Session(engine) as session:
        for source in API_SOURCES:
            print(f"\n[Coletando] {source['name']} ({source['url']})")
            # Headers amigáveis para evitar bloqueios 403
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ObservatorioBot/1.0"}
            try:
                response = requests.get(source['url'], headers=headers, timeout=15)
                
                if response.status_code != 200:
                    print(f"  - Falha na requisição. HTTP Status: {response.status_code}")
                    continue
                
                novos_itens = 0
                
                if source['type'] == "sitemap":
                    soup = BeautifulSoup(response.content, "xml")
                    urls = soup.find_all("url")
                    
                    # Limitamos a 5 URLs apenas para validar o MVP e não inundar o banco
                    for url_node in urls[:5]:
                        loc = url_node.find("loc")
                        if not loc: continue
                        link = loc.text
                        
                        existing = session.exec(select(Opportunity).where(Opportunity.url == link)).first()
                        if not existing:
                            title_guess = link.rstrip('/').split('/')[-1].replace('-', ' ').title() or 'Página Inicial'
                            op = Opportunity(
                                title=f"[Sitemap] {title_guess}",
                                description=f"Conteúdo indexado automaticamente a partir do sitemap de {source['name']}.",
                                url=link,
                                published_date=datetime.utcnow(), # Usamos agora como fallback
                                source=source['name']
                            )
                            session.add(op)
                            novos_itens += 1
                            print(f"  + Adicionado (Sitemap): {title_guess}")
                
                elif source['type'] == "json":
                    try:
                        data = response.json()
                        # Simula um parsing se a API retornar lista (como a do Portal da Transparência costuma fazer)
                        if isinstance(data, list):
                            for item in data[:5]:
                                codigo = item.get('codigoEmenda', item.get('id', 'N/A'))
                                link = f"https://portaldatransparencia.gov.br/emendas/{codigo}"
                                title = f"Emenda {codigo} - {item.get('nomeAutor', 'Desconhecido')}"
                                
                                existing = session.exec(select(Opportunity).where(Opportunity.url == link)).first()
                                if not existing:
                                    op = Opportunity(
                                        title=title,
                                        description=f"Emenda parlamentar extraída via API. Autor: {item.get('nomeAutor', 'N/A')}",
                                        url=link,
                                        published_date=datetime.utcnow(),
                                        source=source['name']
                                    )
                                    session.add(op)
                                    novos_itens += 1
                                    print(f"  + Adicionado (API): {title}")
                        else:
                            print("  - O formato do JSON não é uma lista. Requer parser customizado.")
                    except ValueError:
                        print("  - A resposta não é um JSON válido.")

                session.commit()
                print(f"  > Finalizado {source['name']} - {novos_itens} novos itens salvos.")
            except requests.exceptions.RequestException as e:
                print(f"  ! Erro de rede ao processar {source['name']}: {e}")
            except Exception as e:
                print(f"  ! Erro inesperado ao processar {source['name']}: {e}")

if __name__ == "__main__":
    collect_api()
