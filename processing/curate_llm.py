"""Curadoria LLM opcional — Gemini (free tier), resumo + secretaria sugerida.

Camada OPCIONAL sobre a pipeline determinística: para cada oportunidade já
classificada, gera (1) um resumo executivo de 1–2 frases e (2) a secretaria
municipal mais indicada para tocá-la — os dois campos que regra/regex não
conseguem produzir com qualidade.

Princípios (ver CLAUDE.md):
  - O núcleo da pipeline continua funcionando SEM esta etapa: sem
    `GEMINI_API_KEY` no ambiente, o curador pula sem erro (mesmo padrão do
    coletor do Portal da Transparência).
  - Custo zero: free tier do Gemini. Para respeitar os limites (~10 req/min),
    as oportunidades vão em LOTES numa única requisição, com pausa entre lotes
    e backoff em HTTP 429.
  - Nada de dependência nova: chamada REST direta via `requests`.

Uso (a partir da raiz, venv ativo, .env carregado):
    python processing/curate_llm.py                 # cura pendentes (teto padrão)
    python processing/curate_llm.py --limit=20
    python processing/curate_llm.py --model=gemini-flash-lite-latest
"""

import json
import os
import sys
import time

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from backend.database import engine, create_db_and_tables
from backend.models import Opportunity, utcnow

API_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Alias estável do Google para o Flash atual do free tier (10 req/min, 1500 req/dia).
MODELO_PADRAO = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

LOTE = 10        # oportunidades por requisição (economiza a quota diária)
PAUSA_S = 7      # pausa entre lotes ≈ 8-9 req/min, abaixo do teto do free tier
LIMITE = 50      # teto de oportunidades curadas por execução
MAX_TEXTO = 700  # corte da descrição enviada (tokens custam quota por minuto)

# Secretarias típicas de uma prefeitura — o modelo escolhe DESTA lista (saída
# controlada; qualquer coisa fora dela é descartada na validação).
SECRETARIAS = [
    "Educação", "Saúde", "Meio Ambiente", "Mobilidade Urbana", "Urbanismo",
    "Inovação e Tecnologia", "Cultura", "Esporte", "Assistência Social",
    "Fazenda", "Administração", "Obras", "Turismo",
    "Desenvolvimento Econômico", "Gabinete do Prefeito",
]

PROMPT = """Você é curador de oportunidades institucionais para prefeituras brasileiras.
Para CADA oportunidade do array JSON abaixo, produza:
- "resumo": 1 a 2 frases objetivas em português dizendo o que é a oportunidade e para quem, sem repetir o título literalmente.
- "secretaria": a secretaria municipal mais indicada para tocar a oportunidade, escolhida EXATAMENTE desta lista: {secretarias}.

Responda APENAS com um array JSON válido, um objeto por oportunidade:
[{{"id": <id>, "resumo": "...", "secretaria": "..."}}]

Oportunidades:
{itens}"""


def _payload_lote(ops):
    itens = [{
        "id": op.id,
        "titulo": op.title,
        "fonte": op.source,
        "categoria": op.category,
        "descricao": (op.description or "")[:MAX_TEXTO],
    } for op in ops]
    texto = PROMPT.format(
        secretarias=", ".join(SECRETARIAS),
        itens=json.dumps(itens, ensure_ascii=False),
    )
    return {
        "contents": [{"parts": [{"text": texto}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }


def _chamar_gemini(api_key, model, body, tentativas=3):
    """POST no generateContent com backoff simples em 429/erros transitórios."""
    url = API_TEMPLATE.format(model=model)
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    for tentativa in range(1, tentativas + 1):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=60)
        except requests.exceptions.RequestException as e:
            print(f"  ! erro de rede ({e.__class__.__name__}), tentativa {tentativa}/{tentativas}")
            time.sleep(5 * tentativa)
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:  # estourou o rate limit do free tier
            espera = 20 * tentativa
            print(f"  ! rate limit (429) — aguardando {espera}s...")
            time.sleep(espera)
            continue
        print(f"  ! HTTP {r.status_code}: {r.text[:200]}")
        return None
    return None


def _extrair_itens(resposta):
    """Extrai e valida o array JSON devolvido pelo modelo. Tolerante a lixo."""
    try:
        texto = resposta["candidates"][0]["content"]["parts"][0]["text"]
        dados = json.loads(texto)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return {}
    validos = {}
    if not isinstance(dados, list):
        return validos
    for d in dados:
        if not isinstance(d, dict) or not d.get("id"):
            continue
        resumo = str(d.get("resumo") or "").strip()[:600] or None
        secretaria = str(d.get("secretaria") or "").strip()
        if secretaria not in SECRETARIAS:  # saída fora da lista é descartada
            secretaria = None
        if resumo or secretaria:
            validos[int(d["id"])] = (resumo, secretaria)
    return validos


def curate_llm(limit: int = LIMITE, model: str = None) -> int:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("> Curadoria LLM pulada (defina GEMINI_API_KEY no .env para ativar).")
        return 0
    model = model or MODELO_PADRAO
    create_db_and_tables()

    curadas = 0
    with Session(engine) as session:
        pendentes = session.exec(
            select(Opportunity)
            .where(Opportunity.status == "classificado")
            .where(Opportunity.curated_at.is_(None))
            .order_by(Opportunity.collected_at.desc())
            .limit(limit)
        ).all()
        if not pendentes:
            print("> Curadoria LLM: nada pendente.")
            return 0

        print(f"Curando {len(pendentes)} oportunidade(s) com {model} "
              f"(lotes de {LOTE})...")
        for inicio in range(0, len(pendentes), LOTE):
            lote = pendentes[inicio:inicio + LOTE]
            if inicio:
                time.sleep(PAUSA_S)  # respeita o rate limit do free tier
            resposta = _chamar_gemini(api_key, model, _payload_lote(lote))
            if resposta is None:
                print("  ! lote sem resposta — interrompendo (tente novamente depois).")
                break
            itens = _extrair_itens(resposta)
            for op in lote:
                dados = itens.get(op.id)
                if not dados:
                    continue
                op.summary, op.department = dados
                op.curated_at = utcnow()
                session.add(op)
                curadas += 1
            session.commit()
            print(f"  lote {inicio // LOTE + 1}: {len([o for o in lote if itens.get(o.id)])}/{len(lote)} curada(s)")

    print(f"\n> Curadoria LLM: {curadas} oportunidade(s) curada(s).")
    return curadas


if __name__ == "__main__":
    limit = LIMITE
    model = None
    for arg in sys.argv[1:]:
        if arg.startswith("--limit="):
            limit = int(arg.split("=", 1)[1])
        elif arg.startswith("--model="):
            model = arg.split("=", 1)[1]
    curate_llm(limit=limit, model=model)
