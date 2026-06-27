"""Coletor Portal da Transparência — Etapa A/C (fonte estruturada com credencial).

Consome a API de Dados Abertos do Portal da Transparência (emendas parlamentares e
convênios). Requer uma chave gratuita, lida **exclusivamente** da variável de
ambiente ``PORTAL_TRANSPARENCIA_API_KEY`` e enviada no header ``chave-api-dados``.

Segurança (importante):
  - a chave NUNCA é hardcoded, logada ou impressa; só vem do ambiente;
  - sem a variável definida, o coletor apenas avisa e sai (não quebra a pipeline);
  - guarde a chave em `.env` (ignorado pelo git) e carregue com:
        set -a; source .env; set +a

Uso (a partir da raiz, venv ativo, com a variável já no ambiente):
    python collectors/api/transparencia_collector.py --probe     # só inspeciona o schema
    python collectors/api/transparencia_collector.py             # coleta emendas + convênios
    python collectors/api/transparencia_collector.py --limite=10 --ano=2026
"""

import os
import sys
import json
import time
from datetime import datetime

import requests

# Adiciona a raiz do projeto ao sys.path para importar o backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlmodel import Session, select
from backend.database import engine, create_db_and_tables
from backend.models import Opportunity
from processing.normalizer import normalize_opportunity

BASE = "https://api.portaldatransparencia.gov.br/api-de-dados"
SOURCE = "Portal da Transparência"


def _api_key():
    """Chave da API a partir do ambiente (ou None). Nunca a registra/loga."""
    return os.getenv("PORTAL_TRANSPARENCIA_API_KEY") or None


def _headers(key):
    return {
        "chave-api-dados": key,
        "Accept": "application/json",
        "User-Agent": "ObservatorioBot/1.0",
    }


def _get(endpoint, key, params, tentativas=3):
    """GET autenticado com re-tentativas. Devolve (status_code, payload|None)."""
    url = f"{BASE}/{endpoint}"
    for _ in range(tentativas):
        try:
            r = requests.get(url, headers=_headers(key), params=params, timeout=25)
            if r.status_code == 200:
                try:
                    return 200, r.json()
                except ValueError:
                    return 200, None
            if r.status_code in (401, 403):
                return r.status_code, None  # chave inválida/sem permissão: não insiste
        except requests.exceptions.RequestException:
            pass
        time.sleep(1.5)  # respeita o rate limit (~90 req/min)
    return None, None


def _to_float(valor):
    """Converte valores pt-BR ('1.234.567,89') ou numéricos em float; None se vazio."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def probe():
    """Inspeciona o schema (1 página de cada endpoint). Imprime campos, nunca a chave."""
    key = _api_key()
    if not key:
        print("Defina PORTAL_TRANSPARENCIA_API_KEY no ambiente antes de rodar o probe.")
        return
    ano = datetime.now().year
    for endpoint, params in [("emendas", {"ano": ano, "pagina": 1}),
                             ("convenios", {"pagina": 1})]:
        status, payload = _get(endpoint, key, params)
        print(f"\n== /{endpoint}  (params={params}) -> HTTP {status} ==")
        if status == 200 and isinstance(payload, list) and payload:
            item = payload[0]
            print("  campos:", ", ".join(sorted(item.keys())))
            print("  amostra:", json.dumps(item, ensure_ascii=False)[:400])
        elif status in (401, 403):
            print("  chave rejeitada (401/403) — verifique se a chave está correta/ativa.")
        else:
            print(f"  sem lista de itens (payload: {type(payload).__name__}).")


def collect_transparencia(limite: int = 10, ano: int = None) -> int:
    """Coleta emendas (do ano) e convênios, mapeando para Opportunity. Skip se sem chave."""
    key = _api_key()
    if not key:
        print(f"[{SOURCE}] PORTAL_TRANSPARENCIA_API_KEY ausente — pulando (sem erro).")
        return 0

    ano = ano or datetime.now().year
    create_db_and_tables()
    total = 0

    with Session(engine) as session:
        # --- Emendas parlamentares (têm valor; sem prazo) ---
        status, emendas = _get("emendas", key, {"ano": ano, "pagina": 1})
        for item in (emendas or [])[:limite]:
            codigo = item.get("codigoEmenda") or item.get("numeroEmenda") or item.get("id")
            if not codigo:
                continue
            autor = item.get("nomeAutor", "Desconhecido")
            op = normalize_opportunity(
                title=f"Emenda {codigo} — {autor}",
                description=(f"Emenda parlamentar {ano}. Autor: {autor}. "
                             f"Função: {item.get('funcao', 'N/A')}. "
                             f"Localidade: {item.get('localidadeDoGasto', 'N/A')}."),
                url=f"https://portaldatransparencia.gov.br/emendas/{codigo}",
                source=SOURCE,
                value=_to_float(item.get("valorEmpenhado") or item.get("valorPago")),
            )
            if op and not session.exec(select(Opportunity).where(Opportunity.url == op.url)).first():
                session.add(op)
                total += 1

        # --- Convênios: DEFERIDO ---
        # A API de /convenios exige um filtro obrigatório (período <= 1 mês, ou
        # convenente/órgão/localidade/número) e, nos testes, devolve convênios
        # HISTÓRICOS (vigência já encerrada, ex.: 2002/2003) — pouco úteis como
        # "oportunidade aberta". Campos reais p/ implementar no futuro:
        # dataFinalVigencia, valor, situacao, orgao, municipioConvenente — filtrando
        # por UF do município-alvo e vigência futura.

        session.commit()

    print(f"> {SOURCE}: {total} novo(s) item(ns).")
    return total


if __name__ == "__main__":
    if "--probe" in sys.argv:
        probe()
        sys.exit(0)
    limite, ano = 10, None
    for arg in sys.argv[1:]:
        if arg.startswith("--limite="):
            limite = int(arg.split("=", 1)[1])
        elif arg.startswith("--ano="):
            ano = int(arg.split("=", 1)[1])
    collect_transparencia(limite=limite, ano=ano)
