"""Probe de saúde das fontes — Etapa A (issues #3/#4).

Testa AO VIVO cada fonte de `collectors/sources.py` e reporta, sem persistir nada:
  - acessível? (status HTTP, com fallback para SSL inseguro quando aplicável);
  - sinal útil por tipo: nº de itens de RSS, nº de <url> em sitemap, forma do JSON,
    ou tamanho/indício de SPA para HTML;
  - veredito: OK · VAZIO · BLOQUEADO · ERRO.

Uso (a partir da raiz, com o venv ativo):
    python collectors/validate_sources.py                 # probe de todas as fontes
    python collectors/validate_sources.py --only=A,B      # só os níveis A e B
    python collectors/validate_sources.py --json=out.json # salva relatório estruturado
"""

import os
import sys
import json
import warnings
from concurrent.futures import ThreadPoolExecutor

import requests
import feedparser
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collectors.sources import SOURCES

warnings.simplefilter("ignore", InsecureRequestWarning)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ObservatorioBot/1.0"}
TIMEOUT = 12


def _signal(src, resp):
    """Extrai o sinal relevante de acordo com o tipo da fonte."""
    ctype = resp.headers.get("Content-Type", "").split(";")[0]
    body = resp.content or b""
    t = src["type"]

    if t == "rss":
        feed = feedparser.parse(body)
        n = len(feed.entries)
        return ("OK" if n else "VAZIO"), f"{n} itens RSS", n
    if t == "sitemap":
        soup = BeautifulSoup(body, "xml")
        urls = soup.find_all("url")
        sitemaps = soup.find_all("sitemap")
        n = len(urls) or len(sitemaps)
        rotulo = f"{len(urls)} <url>" + (f" / {len(sitemaps)} <sitemap>" if sitemaps else "")
        return ("OK" if n else "VAZIO"), rotulo, n
    if t == "json":
        try:
            data = resp.json()
        except ValueError:
            return "VAZIO", f"não-JSON ({ctype or '?'}, {len(body)}B)", 0
        if isinstance(data, list):
            return ("OK" if data else "VAZIO"), f"JSON lista[{len(data)}]", len(data)
        if isinstance(data, dict):
            chaves = ",".join(list(data.keys())[:4])
            return "OK", f"JSON obj{{{chaves}}}", 1
        return "OK", f"JSON {type(data).__name__}", 1
    # html / dynamic
    texto = body.decode(resp.encoding or "utf-8", "ignore")
    spa = "__NEXT_DATA__" in texto or 'id="root"' in texto or "__NUXT__" in texto
    return ("OK" if not spa else "SPA"), (f"SPA/JS ({len(body)}B)" if spa else f"HTML {len(body)}B"), len(body)


def probe(src):
    res = {"name": src["name"], "tier": src["tier"], "type": src["type"],
           "url": src["url"], "enabled": src["enabled"]}
    verify = src.get("verify_ssl", True)
    try:
        resp = requests.get(src["url"], headers=HEADERS, timeout=TIMEOUT,
                            verify=verify, allow_redirects=True)
        ssl_flag = ""
    except requests.exceptions.SSLError:
        # Segunda tentativa sem verificação (host com cadeia quebrada).
        try:
            resp = requests.get(src["url"], headers=HEADERS, timeout=TIMEOUT,
                                verify=False, allow_redirects=True)
            ssl_flag = " (ssl-inseguro)"
        except Exception as e:
            res.update(status="ERRO", http=None, signal=f"SSL+{type(e).__name__}", n=0)
            return res
    except requests.exceptions.RequestException as e:
        res.update(status="ERRO", http=None, signal=type(e).__name__, n=0)
        return res

    if resp.status_code in (401, 403, 406, 429):
        res.update(status="BLOQUEADO", http=resp.status_code, signal=f"HTTP {resp.status_code}", n=0)
        return res
    if resp.status_code >= 400:
        res.update(status="ERRO", http=resp.status_code, signal=f"HTTP {resp.status_code}", n=0)
        return res

    try:
        status, sinal, n = _signal(src, resp)
    except Exception as e:
        status, sinal, n = "ERRO", f"parse:{type(e).__name__}", 0
    res.update(status=status, http=resp.status_code, signal=sinal + ssl_flag, n=n)
    return res


def main(only=None, json_path=None):
    fontes = [s for s in SOURCES if not only or s["tier"] in only]
    print(f"Probe de {len(fontes)} fonte(s)...\n")

    with ThreadPoolExecutor(max_workers=8) as ex:
        resultados = list(ex.map(probe, fontes))

    # Mantém a ordem do registro, agrupando por tier.
    ordem = {r["name"]: i for i, r in enumerate(resultados)}
    resultados.sort(key=lambda r: (r["tier"], -r["n"], ordem[r["name"]]))

    icone = {"OK": "✓", "VAZIO": "·", "SPA": "~", "BLOQUEADO": "⨯", "ERRO": "✗"}
    larg = max(len(r["name"]) for r in resultados)
    tier_atual = None
    for r in resultados:
        if r["tier"] != tier_atual:
            tier_atual = r["tier"]
            print(f"\n── Nível {tier_atual} " + "─" * 40)
        flag = "" if r["enabled"] else "  [off]"
        print(f"  {icone.get(r['status'],'?')} {r['status']:9} {r['name']:{larg}}  "
              f"{str(r['http'] or '-'):4}  {r['type']:7}  {r['signal']}{flag}")

    total = len(resultados)
    ok = sum(1 for r in resultados if r["status"] == "OK")
    print(f"\nResumo: {ok}/{total} OK · "
          + " · ".join(f"{k}={sum(1 for r in resultados if r['status']==k)}"
                       for k in ["VAZIO", "SPA", "BLOQUEADO", "ERRO"]))

    if json_path:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)
        print(f"Relatório salvo em {json_path}")
    return resultados


if __name__ == "__main__":
    only = None
    json_path = None
    for arg in sys.argv[1:]:
        if arg.startswith("--only="):
            only = set(arg.split("=", 1)[1].upper().split(","))
        elif arg.startswith("--json="):
            json_path = arg.split("=", 1)[1]
    main(only=only, json_path=json_path)
