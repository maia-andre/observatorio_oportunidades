"""Orquestrador da pipeline do Observatório: coleta seguida de classificação.

Roda, em sequência e num único comando: coleta RSS → coleta API/Sitemap →
classificação por regras. Útil para agendamento (cron/CI). Cada etapa já
garante o schema (`create_db_and_tables`), então funciona sem o servidor no ar.

Uso (a partir da raiz do projeto):
    python run_pipeline.py            # coleta + classifica os pendentes
    python run_pipeline.py --reset    # zera a classificação antes (reclassifica tudo)
"""

import sys

from collectors.rss.rss_collector import collect_rss
from collectors.api.api_collector import collect_api
from processing.classifier import classify_pending, reset_classification


def run(reset: bool = False):
    print("=" * 60)
    print("PIPELINE - Observatório de Oportunidades Institucionais")
    print("=" * 60)

    print("\n[1/3] Coleta RSS")
    collect_rss()

    print("\n[2/3] Coleta API/Sitemap")
    collect_api()

    print("\n[3/3] Classificação por regras")
    if reset:
        n = reset_classification()
        print(f"  (classificação zerada em {n} registro(s))")
    resumo = classify_pending()

    print(f"\n> Classificadas: {resumo['classificado']} | Não classificadas: {resumo['nao_classificado']}")
    for cat, n in sorted(resumo["por_categoria"].items(), key=lambda x: -x[1]):
        print(f"   - {cat}: {n}")


if __name__ == "__main__":
    run(reset="--reset" in sys.argv)
