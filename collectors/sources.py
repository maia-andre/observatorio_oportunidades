"""Registro central de fontes — Etapa A (issues #3/#4).

Catálogo único de TODAS as fontes mapeadas na Fase 0 (níveis A–D), incluindo as
que não chegaram a ser validadas, mais candidatas estruturadas adicionais
(PNCP-API, Querido Diário). Os coletores leem deste registro em vez de manterem
listas próprias, e `collectors/validate_sources.py` usa-o para o probe de saúde.

Campos:
  - name     : rótulo da fonte (vira `Opportunity.source`).
  - tier     : "A" (RSS) · "B" (API/JSON/Sitemap) · "C" (HTML estático) · "D" (dinâmico/erros).
  - type     : "rss" | "sitemap" | "json" | "html" | "dynamic" (estratégia de coleta).
  - url      : URL a ser consultada/probed (feed, sitemap.xml, endpoint JSON ou página).
  - enabled  : se entra na coleta automática. O probe roda em TODAS, mas só as
               `enabled` (e vivas) são coletadas — atualizado conforme a validação.
  - verify_ssl: False para hosts com cadeia de certificado quebrada (probe/coleta
               caem para conexão insegura e marcam isso).
  - notes    : observação técnica (da Fase 0 ou desta etapa).
"""

# Cada entrada é um dict simples (sem dependências externas) para facilitar
# edição manual e serialização no relatório do probe.
SOURCES = [
    # ───────────────────────── Nível A — RSS ─────────────────────────
    {"name": "ABIPEM",                 "tier": "A", "type": "rss", "url": "https://www.abipem.org.br/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress"},
    {"name": "BFUCA UNESCO",           "tier": "A", "type": "rss", "url": "https://bfucaunesco.org.br/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress"},
    {"name": "ICISMEP",                "tier": "A", "type": "rss", "url": "https://icismep.mg.gov.br/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress"},
    {"name": "Estônia Hub",            "tier": "A", "type": "rss", "url": "https://estoniahub.com.br/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress"},
    {"name": "Transferegov",           "tier": "A", "type": "rss", "url": "https://www.gov.br/rss.xml", "enabled": False, "verify_ssl": True, "notes": "Feed gov.br GENÉRICO (notícia, baixa relevância) — depende da porta de relevância"},
    {"name": "Santa Isabel",           "tier": "A", "type": "rss", "url": "https://site.santaisabel.sp.gov.br/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress (prefeitura)"},
    {"name": "ABNT",                   "tier": "A", "type": "rss", "url": "https://abnt.org.br/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress"},
    {"name": "Capta",                  "tier": "A", "type": "rss", "url": "https://capta.org.br/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress — fonte de editais/financiamento (alta relevância na Fase 0)"},
    {"name": "CENPEC",                 "tier": "A", "type": "rss", "url": "https://www.cenpec.org.br/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress"},
    {"name": "Prêmio Espírito Público","tier": "A", "type": "rss", "url": "https://premioespiritopublico.org.br/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress"},

    # ──────────────────── Nível B — API / JSON / Sitemap ────────────────────
    {"name": "Portal da Transparência","tier": "B", "type": "json",    "url": "https://api.portaldatransparencia.gov.br/api-de-dados/emendas", "enabled": False, "verify_ssl": True, "notes": "Exige header 'chave-api-dados' (cadastro gratuito) — sem chave retorna 401"},
    {"name": "ONA",                    "tier": "B", "type": "sitemap", "url": "https://www.ona.org.br/sitemap.xml", "enabled": True, "verify_ssl": True, "notes": "Next.js"},
    {"name": "Agência SP",             "tier": "B", "type": "sitemap", "url": "https://www.agenciasp.sp.gov.br/sitemap.xml", "enabled": True, "verify_ssl": True, "notes": "WordPress"},
    {"name": "ENAP",                   "tier": "B", "type": "sitemap", "url": "https://enap.gov.br/sitemap.xml", "enabled": True, "verify_ssl": True, "notes": "Gov.br"},
    {"name": "IQG",                    "tier": "B", "type": "sitemap", "url": "https://www.iqg.com.br/sitemap.xml", "enabled": True, "verify_ssl": True, "notes": "Next.js"},
    {"name": "Ranking Municípios",     "tier": "B", "type": "json",    "url": "https://ranking-municipios.tesouro.gov.br/", "enabled": True, "verify_ssl": True, "notes": "Tesouro — SPA, endpoint JSON a confirmar"},
    {"name": "Caixa Sustentabilidade", "tier": "B", "type": "sitemap", "url": "http://www.caixa.gov.br/sitemap.xml", "enabled": True, "verify_ssl": True, "notes": "Gov.br (.aspx)"},
    {"name": "Conexão Inovação",       "tier": "B", "type": "sitemap", "url": "https://www.conexaoinovacaopublica.org/sitemap.xml", "enabled": True, "verify_ssl": True, "notes": "Next.js"},
    {"name": "Google Education",       "tier": "B", "type": "sitemap", "url": "https://edu.google.com/sitemap.xml", "enabled": True, "verify_ssl": True, "notes": "Portal próprio"},
    {"name": "Comunicação SP",         "tier": "B", "type": "sitemap", "url": "https://www.comunicacao.sp.gov.br/sitemap.xml", "enabled": True, "verify_ssl": True, "notes": "Gov.br"},
    {"name": "Conasems",               "tier": "B", "type": "sitemap", "url": "https://portal.conasems.org.br/sitemap.xml", "enabled": True, "verify_ssl": True, "notes": "WordPress"},

    # ──────────────────── Nível C — HTML estático ────────────────────
    {"name": "Radar Transparência",    "tier": "C", "type": "html", "url": "https://radardatransparencia.atricon.org.br/", "enabled": True, "verify_ssl": True, "notes": "Next.js"},
    {"name": "Tree Cities",            "tier": "C", "type": "html", "url": "https://www.treecitiesoftheworld.org/", "enabled": True, "verify_ssl": True, "notes": "Next.js"},
    {"name": "Certificadora Social",   "tier": "C", "type": "html", "url": "https://www.certificadora.social/selo-transparencia", "enabled": True, "verify_ssl": True, "notes": "Next.js"},
    {"name": "Congresso Nacional",     "tier": "C", "type": "html", "url": "https://www.congressonacional.leg.br/apoioemendas", "enabled": True, "verify_ssl": True, "notes": "Portal próprio — apoio a emendas"},
    {"name": "Prosas",                 "tier": "C", "type": "html", "url": "https://prosas.com.br/editais", "enabled": True, "verify_ssl": True, "notes": "Agregador de EDITAIS (alta relevância)"},
    {"name": "Prêmio Quality",         "tier": "C", "type": "html", "url": "https://www.premioquality.com/", "enabled": True, "verify_ssl": True, "notes": "Next.js"},
    {"name": "OBMEP",                  "tier": "C", "type": "html", "url": "https://www.obmep.org.br/", "enabled": True, "verify_ssl": True, "notes": "Next.js"},

    # ──────────────── Nível D — dinâmico / erros na Fase 0 ────────────────
    {"name": "PNCP (site)",            "tier": "D", "type": "dynamic", "url": "https://pncp.gov.br/app/editais", "enabled": False, "verify_ssl": True, "notes": "UI dinâmica (timeout/Playwright) — preferir PNCP-API abaixo"},
    {"name": "CPB",                    "tier": "D", "type": "html",    "url": "https://cpb.org.br/competicoes/premio-paralimpicos/", "enabled": False, "verify_ssl": False, "notes": "Erro de certificado SSL na Fase 0"},
    {"name": "Diário Oficial (DOU)",   "tier": "D", "type": "dynamic", "url": "https://www.in.gov.br/leiturajornal", "enabled": False, "verify_ssl": True, "notes": "Timeout/dinâmico — preferir Querido Diário abaixo"},
    {"name": "MAPA (Agricultura)",     "tier": "D", "type": "html",    "url": "https://www.gov.br/agricultura/pt-br/assuntos/inspecao", "enabled": False, "verify_ssl": True, "notes": "Timeout na Fase 0"},
    {"name": "PNCQ",                   "tier": "D", "type": "html",    "url": "https://pncq.org.br/certificacoes/", "enabled": False, "verify_ssl": False, "notes": "Erro de certificado SSL na Fase 0"},
    {"name": "CIEE",                   "tier": "D", "type": "html",    "url": "https://portal.ciee.org.br/", "enabled": False, "verify_ssl": True, "notes": "Erro 403 (anti-bot) na Fase 0"},
    {"name": "WABA",                   "tier": "D", "type": "html",    "url": "https://www.waba.org.my/resources/otherlanguages/portugese/leis1.htm", "enabled": False, "verify_ssl": True, "notes": "Erro 406 na Fase 0"},
    {"name": "Ciudades Educadoras",    "tier": "D", "type": "html",    "url": "http://www.ciudadeseducadorasla.org/", "enabled": False, "verify_ssl": False, "notes": "Erro de certificado SSL na Fase 0"},

    # ──────────── Candidatas estruturadas (recomendadas nesta etapa) ────────────
    {"name": "PNCP-API",               "tier": "B", "type": "json", "url": "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao", "enabled": True, "verify_ssl": True, "notes": "API REST pública do PNCP (editais/contratações) — endpoint/params a confirmar no probe"},
    {"name": "Querido Diário",         "tier": "B", "type": "json", "url": "https://queridodiario.ok.org.br/api/gazettes", "enabled": True, "verify_ssl": True, "notes": "API pública de diários oficiais municipais (Open Knowledge Brasil)"},
]


def enabled_sources(*types):
    """Fontes habilitadas, opcionalmente filtradas por um ou mais `type`."""
    out = [s for s in SOURCES if s.get("enabled")]
    if types:
        out = [s for s in out if s["type"] in types]
    return out
