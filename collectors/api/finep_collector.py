"""Coletor FINEP — chamadas públicas abertas, SEM chave de API.

Consulta a API Liferay do portal da FINEP (objeto `chamadapublicas`), que aceita
leitura anônima e devolve as chamadas com campos estruturados: título, descrição,
situação (aberta/encerrada), PRAZO de submissão (`prazoProposto`), vigência,
público-alvo, região e tema — os campos que o painel precisa, sem scraping.

Só coleta chamadas com `situacao = 'aberta'`. Como o site novo da FINEP é um SPA
sem rota pública de detalhe por chamada, a URL canônica aponta para o painel de
busca já filtrado pelo título (`?search=`), que é também a chave de deduplicação.

Uso (a partir da raiz, venv ativo):
    python collectors/api/finep_collector.py
    python collectors/api/finep_collector.py --limite=10
"""

import os
import sys
import time
from datetime import datetime
from urllib.parse import quote

import requests

# Adiciona a raiz do projeto ao sys.path para importar o backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlmodel import Session, select
from backend.database import engine, create_db_and_tables
from backend.models import Opportunity
from processing.normalizer import normalize_opportunity

BASE = "https://www.finep.gov.br/o/c/chamadapublicas/"
PAINEL_BUSCA = "https://www.finep.gov.br/chamadas-publicas"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}
LIMITE = 40  # teto de chamadas por execução (hoje ~36 abertas)


def _parse_dt(valor):
    """ISO 8601 com sufixo Z ('2026-08-14T18:00:00.000Z') -> datetime; None se inválido."""
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _nomes(campo):
    """Extrai os rótulos de campos de lista/dict da API ({'name': ...})."""
    if isinstance(campo, dict):
        return [campo.get("name")] if campo.get("name") else []
    if isinstance(campo, list):
        return [x.get("name") for x in campo if isinstance(x, dict) and x.get("name")]
    return []


def _get(params, tentativas=3):
    """GET com pequenas re-tentativas."""
    for _ in range(tentativas):
        try:
            r = requests.get(BASE, headers=HEADERS, params=params, timeout=25)
            if r.status_code == 200 and r.content:
                return r.json()
        except requests.exceptions.RequestException:
            pass
        time.sleep(1.5)
    return None


def collect_finep(limite: int = LIMITE) -> int:
    print(f"Iniciando coleta FINEP (chamadas públicas abertas, teto {limite})...")
    create_db_and_tables()

    payload = _get({
        "filter": "situacao eq 'aberta'",
        "sort": "dataDePublicacao:desc",
        "pageSize": max(1, limite),
    })
    if not payload or not payload.get("items"):
        print("  Sem chamadas abertas (ou API indisponível).")
        return 0

    novos = 0
    with Session(engine) as session:
        for item in payload["items"][:limite]:
            titulo = item.get("titulo") or "Chamada pública FINEP"
            # Painel de busca da FINEP filtrado pelo título (SPA sem rota de detalhe).
            url = f"{PAINEL_BUSCA}?search={quote(titulo)}"

            partes = []
            partes += _nomes(item.get("tipoDeOportunidade"))
            partes += _nomes(item.get("temaPrincipal"))
            regiao = _nomes(item.get("regiao"))
            if regiao:
                partes.append(f"Região: {', '.join(regiao)}")
            publico = _nomes(item.get("publicoAlvo"))
            if publico:
                partes.append(f"Público-alvo: {', '.join(publico)}")
            descricao = ". ".join(partes)
            if item.get("descricaoRawText"):
                descricao = f"{descricao}. {item['descricaoRawText']}" if descricao else item["descricaoRawText"]

            op = normalize_opportunity(
                title=titulo,
                description=descricao,
                url=url,
                source="FINEP",
                published_date=_parse_dt(item.get("dataDePublicacao")),
                # Prazo de submissão quando existe; senão o fim da vigência da chamada.
                deadline=_parse_dt(item.get("prazoProposto")) or _parse_dt(item.get("vigenciaFim")),
            )
            if op is None:
                continue

            existing = session.exec(select(Opportunity).where(Opportunity.url == op.url)).first()
            if not existing:
                session.add(op)
                novos += 1

        session.commit()

    total = payload.get("totalCount", "?")
    print(f"  {novos} novo(s) de {total} chamada(s) aberta(s).")
    print(f"\n> FINEP: {novos} novo(s) item(ns) no total.")
    return novos


if __name__ == "__main__":
    limite = LIMITE
    for arg in sys.argv[1:]:
        if arg.startswith("--limite="):
            limite = int(arg.split("=", 1)[1])
    collect_finep(limite=limite)
