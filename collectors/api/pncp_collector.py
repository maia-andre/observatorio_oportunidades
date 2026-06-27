"""Coletor PNCP — Etapa A (fontes estruturadas), SEM LLM e SEM chave de API.

Consulta a API pública de Consulta do PNCP (Portal Nacional de Contratações
Públicas), endpoint de "contratações com proposta em aberto" — editais cujo prazo
de envio de propostas ainda está vigente. Diferente do RSS, cada item já vem com
PRAZO (`dataEncerramentoProposta`) e VALOR (`valorTotalEstimado`), além de órgão e
município — justamente os campos que o painel precisa e que o RSS não entrega.

Re-executável; deduplica pela URL canônica do edital no app do PNCP.

Uso (a partir da raiz, venv ativo):
    python collectors/api/pncp_collector.py
    python collectors/api/pncp_collector.py --limite=5 --dias=120
"""

import os
import sys
import time
from datetime import datetime, timedelta

import requests

# Adiciona a raiz do projeto ao sys.path para importar o backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlmodel import Session, select
from backend.database import engine, create_db_and_tables
from backend.models import Opportunity
from processing.normalizer import normalize_opportunity

BASE = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}

# Modalidades mais "oportunidade" para um radar municipal (código PNCP -> rótulo).
MODALIDADES = {
    3: "Concurso",
    4: "Concorrência Eletrônica",
    6: "Pregão Eletrônico",
    12: "Credenciamento",
}
TAMANHO_PAGINA = 10        # mínimo aceito pela API (valores < 10 retornam HTTP 400)
DIAS_JANELA = 90           # editais com encerramento de proposta até hoje + N dias
LIMITE_POR_MODALIDADE = 8  # teto por modalidade para não afogar o painel


def _parse_dt(valor):
    """ISO 8601 ('2026-07-07T10:00:00') -> datetime; None se ausente/inválido."""
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor)
    except (ValueError, TypeError):
        return None


def _pncp_url(numero_controle):
    """URL canônica do edital no app do PNCP a partir do numeroControlePNCP.

    Formato: '<cnpj>-<seqOrgao>-<sequencial>/<ano>'.
    Ex.: '04696490000163-1-000065/2024' -> .../app/editais/04696490000163/2024/65
    """
    try:
        ident, ano = numero_controle.split("/")
        partes = ident.split("-")
        cnpj, seq = partes[0], partes[-1]
        return f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{int(seq)}"
    except (ValueError, AttributeError, IndexError):
        return None


def _get(params, tentativas=3):
    """GET com pequenas re-tentativas (a API ocasionalmente oscila)."""
    for _ in range(tentativas):
        try:
            r = requests.get(BASE, headers=HEADERS, params=params, timeout=25)
            if r.status_code == 200 and r.content:
                return r.json()
            if r.status_code == 204:      # sem registros para o filtro
                return {"data": []}
        except requests.exceptions.RequestException:
            pass
        time.sleep(1.5)
    return None


def collect_pncp(limite_por_modalidade: int = LIMITE_POR_MODALIDADE,
                 dias_janela: int = DIAS_JANELA) -> int:
    data_final = (datetime.now() + timedelta(days=dias_janela)).strftime("%Y%m%d")
    print(f"Iniciando coleta PNCP (encerramento até {data_final}, "
          f"{len(MODALIDADES)} modalidade(s))...")
    create_db_and_tables()
    total_novos = 0

    with Session(engine) as session:
        for codigo, rotulo in MODALIDADES.items():
            params = {
                "dataFinal": data_final,
                "codigoModalidadeContratacao": codigo,
                "pagina": 1,
                "tamanhoPagina": max(TAMANHO_PAGINA, limite_por_modalidade),
            }
            payload = _get(params)
            if not payload or not payload.get("data"):
                print(f"  [{rotulo}] sem registros.")
                continue

            novos = 0
            for item in payload["data"][:limite_por_modalidade]:
                url = _pncp_url(item.get("numeroControlePNCP")) or item.get("linkSistemaOrigem")
                unidade = item.get("unidadeOrgao") or {}
                local = f"{unidade.get('municipioNome', '?')}/{unidade.get('ufSigla', '?')}"
                descricao = (f"{item.get('modalidadeNome', rotulo)}. "
                             f"Órgão: {unidade.get('nomeUnidade', '')} – {local}. "
                             f"Situação: {item.get('situacaoCompraNome', '')}. "
                             f"{item.get('objetoCompra', '')}")

                op = normalize_opportunity(
                    title=item.get("objetoCompra") or f"Edital PNCP ({rotulo})",
                    description=descricao,
                    url=url,
                    source="PNCP",
                    published_date=_parse_dt(item.get("dataPublicacaoPncp")),
                    deadline=_parse_dt(item.get("dataEncerramentoProposta")),
                    value=item.get("valorTotalEstimado"),
                )
                if op is None:
                    continue

                existing = session.exec(select(Opportunity).where(Opportunity.url == op.url)).first()
                if not existing:
                    session.add(op)
                    novos += 1

            session.commit()
            total_novos += novos
            print(f"  [{rotulo}] {novos} novo(s) de {payload.get('totalRegistros', '?')} disponíveis.")

    print(f"\n> PNCP: {total_novos} novo(s) item(ns) no total.")
    return total_novos


if __name__ == "__main__":
    limite = LIMITE_POR_MODALIDADE
    dias = DIAS_JANELA
    for arg in sys.argv[1:]:
        if arg.startswith("--limite="):
            limite = int(arg.split("=", 1)[1])
        elif arg.startswith("--dias="):
            dias = int(arg.split("=", 1)[1])
    collect_pncp(limite_por_modalidade=limite, dias_janela=dias)
