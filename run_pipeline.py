"""Orquestrador da pipeline: coleta → relevância → classificação → enriquecimento.

Roda, em sequência e num único comando: coleta RSS + PNCP + FINEP + Portal da
Transparência (emendas) → porta de relevância → classificação por regras → enriquecimento
(prazo/valor via deep-fetch, incl. PDF). Útil para agendamento (cron/CI). Cada etapa
garante o schema, então funciona sem o servidor no ar.

Uso (a partir da raiz do projeto):
    python run_pipeline.py            # coleta + relevância + classifica + enriquece
    python run_pipeline.py --reset    # zera classificação/relevância antes (reprocessa tudo)

Obs.: o Portal da Transparência só coleta se PORTAL_TRANSPARENCIA_API_KEY estiver no
ambiente (carregue com `set -a; source .env; set +a`); sem a chave, pula sem erro.
O mesmo vale para a curadoria LLM (resumo + secretaria sugerida via Gemini): só
roda se GEMINI_API_KEY estiver no ambiente — o núcleo da pipeline segue 100%
determinístico sem ela.
"""

import os
import sys

from collectors.rss.rss_collector import collect_rss
from collectors.api.pncp_collector import collect_pncp
from collectors.api.finep_collector import collect_finep
from collectors.api.transparencia_collector import collect_transparencia
from processing.relevance import apply_relevance
from processing.classifier import classify_pending, reset_classification
from processing.enrich import enrich
from processing.curate_llm import curate_llm


def run(reset: bool = False):
    print("=" * 60)
    print("PIPELINE - Observatório de Oportunidades Institucionais")
    print("=" * 60)

    print("\n[1/8] Coleta RSS")
    collect_rss()

    print("\n[2/8] Coleta PNCP (editais com propostas abertas)")
    collect_pncp()
    foco_uf = os.getenv("FOCO_UF")
    if foco_uf:
        print(f"  + PNCP local (UF={foco_uf})")
        collect_pncp(uf=foco_uf)

    print("\n[3/8] Coleta FINEP (chamadas públicas abertas)")
    collect_finep()

    print("\n[4/8] Coleta Portal da Transparência (emendas — requer chave no ambiente)")
    collect_transparencia()

    # No reset, zera a classificação ANTES de re-pontuar a relevância — senão o
    # reset (status->"novo") apagaria a marcação de irrelevante recém-feita.
    if reset:
        n = reset_classification()
        print(f"\n  (classificação zerada em {n} registro(s))")

    print("\n[5/8] Porta de relevância")
    rel = apply_relevance(rescore=reset)
    print(f"  Relevantes: {rel['relevante']} | Irrelevantes: {rel['irrelevante']} "
          f"(avaliados: {rel['avaliados']})")

    print("\n[6/8] Classificação por regras")
    resumo = classify_pending()
    print(f"  Classificadas: {resumo['classificado']} | Não classificadas: {resumo['nao_classificado']}")
    for cat, n in sorted(resumo["por_categoria"].items(), key=lambda x: -x[1]):
        print(f"   - {cat}: {n}")

    print("\n[7/8] Enriquecimento (prazo/valor via deep-fetch + PDF)")
    enrich(limit=50)

    print("\n[8/8] Curadoria LLM (opcional — requer GEMINI_API_KEY no ambiente)")
    curate_llm()


if __name__ == "__main__":
    run(reset="--reset" in sys.argv)
