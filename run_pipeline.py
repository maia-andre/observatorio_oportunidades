"""Orquestrador da pipeline do Observatório: coleta → relevância → classificação.

Roda, em sequência e num único comando: coleta RSS (fontes do registro central) →
porta de relevância (descarta o que não é oportunidade) → classificação por regras.
Útil para agendamento (cron/CI). Cada etapa garante o schema, então funciona sem o
servidor no ar.

Uso (a partir da raiz do projeto):
    python run_pipeline.py            # coleta + avalia relevância + classifica os pendentes
    python run_pipeline.py --reset    # zera classificação e relevância antes (reprocessa tudo)

Obs.: a extração de prazo/valor (incl. PDF) roda à parte em `processing/enrich.py`;
as fontes estruturadas (PNCP/Querido Diário/Transparência) entram em incremento futuro.
"""

import sys

from collectors.rss.rss_collector import collect_rss
from processing.relevance import apply_relevance
from processing.classifier import classify_pending, reset_classification


def run(reset: bool = False):
    print("=" * 60)
    print("PIPELINE - Observatório de Oportunidades Institucionais")
    print("=" * 60)

    print("\n[1/3] Coleta RSS")
    collect_rss()

    # No reset, zera a classificação ANTES de re-pontuar a relevância — senão o
    # reset (status->"novo") apagaria a marcação de irrelevante recém-feita.
    if reset:
        n = reset_classification()
        print(f"\n  (classificação zerada em {n} registro(s))")

    print("\n[2/3] Porta de relevância")
    rel = apply_relevance(rescore=reset)
    print(f"  Relevantes: {rel['relevante']} | Irrelevantes: {rel['irrelevante']} "
          f"(avaliados: {rel['avaliados']})")

    print("\n[3/3] Classificação por regras")
    resumo = classify_pending()

    print(f"\n> Classificadas: {resumo['classificado']} | Não classificadas: {resumo['nao_classificado']}")
    for cat, n in sorted(resumo["por_categoria"].items(), key=lambda x: -x[1]):
        print(f"   - {cat}: {n}")


if __name__ == "__main__":
    run(reset="--reset" in sys.argv)
