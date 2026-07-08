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
    {"name": "Agência FAPESP",         "tier": "A", "type": "rss", "url": "https://agencia.fapesp.br/rss/", "enabled": True, "verify_ssl": True, "notes": "Notícias de fomento/pesquisa SP — chamadas e programas passam pela porta de relevância"},

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
    {"name": "PNCP-API",               "tier": "B", "type": "json", "url": "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta", "enabled": False, "verify_ssl": True, "notes": "Coletor dedicado: collectors/api/pncp_collector.py (exige dataFinal + modalidade; tamanhoPagina>=10)"},
    {"name": "Querido Diário",         "tier": "B", "type": "json", "url": "https://queridodiario.ok.org.br/api/gazettes", "enabled": False, "verify_ssl": True, "notes": "API retorna 403 (bloqueio tipo Cloudflare) deste ambiente — reavaliar acesso/headers"},
    {"name": "FINEP-API",              "tier": "B", "type": "json", "url": "https://www.finep.gov.br/o/c/chamadapublicas/?pageSize=1", "enabled": False, "verify_ssl": True, "notes": "Coletor dedicado: collectors/api/finep_collector.py (API Liferay anônima; filtra situacao='aberta'; prazoProposto=deadline)"},

    # ──────────── Candidatas SP/SJC investigadas em 07/2026 (sem endpoint utilizável) ────────────
    {"name": "Desenvolve SP",          "tier": "D", "type": "html", "url": "https://www.desenvolvesp.com.br/", "enabled": False, "verify_ssl": True, "notes": "Sem RSS; sitemap.xml retorna 403 (anti-bot) — linhas de crédito municipais exigiriam scraping dedicado"},
    {"name": "Prefeitura SJC",         "tier": "D", "type": "html", "url": "https://www.sjc.sp.gov.br/", "enabled": False, "verify_ssl": True, "notes": "Sem /feed nem sitemap.xml (404) — portal próprio; reavaliar página de editais/licitações"},
    {"name": "FAPESP (chamadas)",      "tier": "D", "type": "html", "url": "https://fapesp.br/chamadas", "enabled": False, "verify_ssl": True, "notes": "Sem RSS de chamadas (Agência FAPESP cobre por notícia) — página de chamadas vigentes exigiria scraping dedicado"},

    # ──────── Prêmios/selos — investigação 07/2026 (docs/pesquisa_emendas_premios_selos.md) ────────
    {"name": "Atricon",                "tier": "A", "type": "rss", "url": "https://atricon.org.br/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress — promotora do Selo PNTP (transparência); notícias gerais dos TCEs passam pela porta de relevância"},
    {"name": "APM",                    "tier": "A", "type": "rss", "url": "https://www.apaulista.org.br/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress — Associação Paulista de Municípios (eventos/editais/prêmios p/ municípios SP; exige www)"},
    {"name": "Sindinfor",              "tier": "A", "type": "rss", "url": "https://sindinfor.org.br/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress — promove o Prêmio Nacional Cidades Tecnológicas"},
    {"name": "Smart City Business",    "tier": "A", "type": "rss", "url": "https://www.smartcitybusiness.com.br/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress — congresso/premiação InovaCidade"},
    {"name": "República.org",          "tier": "A", "type": "rss", "url": "https://republica.org/feed", "enabled": True, "verify_ssl": True, "notes": "WordPress — mantenedora do Prêmio Espírito Público (gestão de pessoas no setor público)"},
    {"name": "CNM",                    "tier": "D", "type": "html", "url": "https://www.cnm.org.br/", "enabled": False, "verify_ssl": True, "notes": "Sem RSS (/feed 404 com e sem www) — divulga prêmios p/ municípios; monitorar exigiria scraping dedicado"},
    {"name": "Band Cidades Excelentes","tier": "D", "type": "html", "url": "https://www.bandcidadesexcelentes.com.br/", "enabled": False, "verify_ssl": True, "notes": "Conexão falha deste ambiente e sem feed conhecido — ranking IGMA avalia todos os municípios automaticamente (inscrição não é gargalo)"},
    {"name": "Selo UNICEF",            "tier": "D", "type": "html", "url": "https://selounicef.org.br/", "enabled": False, "verify_ssl": True, "notes": "Sem RSS (/feed 404) — ciclo bianual com edital próprio; acompanhar manualmente na janela de adesão"},
    {"name": "Prêmio Innovare",        "tier": "D", "type": "html", "url": "https://www.premioinnovare.com.br/", "enabled": False, "verify_ssl": True, "notes": "Sem RSS (/feed devolve HTML) — foco em sistema de Justiça, relevância municipal baixa"},
    {"name": "TCU (PNPC)",             "tier": "D", "type": "html", "url": "https://portal.tcu.gov.br/", "enabled": False, "verify_ssl": True, "notes": "Sem RSS utilizável encontrado (/rss falha) — PNPC tem adesão contínua, sem edital periódico"},
]


def enabled_sources(*types):
    """Fontes habilitadas, opcionalmente filtradas por um ou mais `type`."""
    out = [s for s in SOURCES if s.get("enabled")]
    if types:
        out = [s for s in out if s["type"] in types]
    return out
