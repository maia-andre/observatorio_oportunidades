# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Orientações para o Claude Code (e para os desenvolvedores) trabalharem neste repositório. Documentação canônica complementar em `README.md` e `docs/`.

## Visão geral

**Observatório de Oportunidades Institucionais** — plataforma para monitorar automaticamente fontes públicas (RSS, APIs, sitemaps, HTML) e consolidar "oportunidades" institucionais (editais, premiações, emendas parlamentares, convênios, programas federais/estaduais, chamamentos públicos etc.) em uma base única. É uma PoC evolutiva, organizada em fases (0 a 5).

## Estado atual

- **Fases 0–1** (Descoberta, Radar) ✅, **Fase 2** (Curadoria por regras) ✅ e **Fase 4** (Matching municipal, PoC) ✅.
- **Pipeline (núcleo determinístico):** coleta (**RSS + PNCP + FINEP + Portal da Transparência/emendas**) → **porta de relevância** (`processing/relevance.py`) → **classificação ponderada** com multi-rótulo (`processing/classifier.py`) → **enriquecimento** de prazo/valor por regex + **PDF** (`processing/enrich.py`, PyMuPDF) com **anti-contaminação** de boilerplate → **curadoria LLM opcional** (`processing/curate_llm.py`, Gemini free tier: resumo + secretaria sugerida; pula sem erro se faltar `GEMINI_API_KEY`).
- **Painel:** busca full-text **SQLite FTS5/BM25** (acento-insensível, `backend/search.py`), filtros (fonte/categoria/prazo/valor), **ciclo de vida** (vencidas ocultas por padrão, ordenação por urgência, selos nova/vencida), página de detalhe `/opportunity/{id}`, e **matching municipal** (aderência 0–100, `processing/matching.py`, penaliza prazo vencido).
- **Restrição do projeto:** **custo zero**. O núcleo (coleta/relevância/classificação/busca/matching) é determinístico e funciona sem chave alguma; a única camada com LLM é a curadoria opcional via **free tier do Gemini** (decisão de 07/2026 — revisão da regra anterior "sem LLM").
- Backend FastAPI + SQLModel; painel Jinja2 + PicoCSS (CDN). **Banco padrão SQLite**; PostgreSQL via `DATABASE_URL`.
- Issues **#3/#4** (validação de fontes, Diego) seguem abertas; **#6–#12** fechadas.

## Stack

- **Linguagem:** Python 3.10+
- **Web/API:** FastAPI + Uvicorn
- **ORM/validação:** SQLModel (envelopa SQLAlchemy + Pydantic)
- **Banco:** SQLite (padrão Fase 0) · PostgreSQL (opcional/alvo futuro)
- **Coleta:** requests, feedparser (RSS), BeautifulSoup + lxml (XML); **PyMuPDF** (texto de PDF, no enrich)
- **Busca:** SQLite **FTS5** (ranking BM25, acento-insensível) — `backend/search.py`
- **Painel:** Jinja2 + PicoCSS
- **Futuro:** frontend React/Next.js; infra Docker/Nginx

## Estrutura de diretórios

- `backend/` — app FastAPI
  - `main.py` — painel (`/` lista/filtra/busca/ranqueia) e detalhe (`/opportunity/{id}`)
  - `database.py` — engine + criação das tabelas
  - `models.py` — modelos `Opportunity` e `MunicipalProfile`
  - `search.py` — busca FTS5 (índice + triggers + ranking BM25)
  - `templates/` — `index.html` (painel) e `detail.html` (detalhe)
- `collectors/` — coleta autônoma (cron/CI):
  - `sources.py` — **registro central** de todas as fontes (catálogo + `enabled`)
  - `validate_sources.py` — **probe** de saúde das fontes (ao vivo)
  - `rss/rss_collector.py` — RSS (lê do registro)
  - `api/pncp_collector.py` — **PNCP** (editais c/ proposta aberta; suporta `--uf`)
  - `api/finep_collector.py` — **FINEP** (chamadas públicas abertas; API Liferay anônima)
  - `api/transparencia_collector.py` — **Portal da Transparência** (emendas; chave via env)
  - `api/api_collector.py` — coletor de sitemap **legado** (não usado na pipeline)
- `processing/` — pós-coleta (tudo sem LLM):
  - `normalizer.py` (normalização) · `relevance.py` (porta de relevância)
  - `rules.py` + `classifier.py` (classificação ponderada, multi-rótulo)
  - `extractor.py` + `enrich.py` (prazo/valor por regex + PDF + anti-contaminação)
  - `curate_llm.py` (curadoria LLM **opcional**: resumo + secretaria via Gemini free tier)
  - `matching.py` (aderência municipal) · `seed_profiles.py` (perfis de exemplo)
- `run_pipeline.py` — orquestra coleta → relevância → classificação → enriquecimento (aceita `--reset`)
- `.env.example` — modelo de variáveis (chaves/foco); o `.env` é **gitignored**
- `database/` (SQLite, ignorado) · `docs/` · `docker-compose.yml` (opcional, PostgreSQL) · `frontend/` (futuro)

## Modelo de dados (`Opportunity`)

**`Opportunity`** (`backend/models.py`): `id` · `title` · `description?` · `url` (**único/indexado — chave de dedup**) · `published_date?` · `source` · `category?` · `categories?` (multi-rótulo, separado por vírgula) · `deadline?` · `value?` (R$) · `relevance_score?` (0–1) · `status` · `collected_at` · `summary?`/`department?`/`curated_at?` (curadoria LLM opcional). Ciclo do `status`: `novo` → (relevância) `irrelevante` ou segue → (classificação) `classificado`/`nao_classificado`.

**`MunicipalProfile`**: `id` · `name` · `uf` · `interests` (categorias/keywords por vírgula) · `population?` — usado pelo matching (`processing/matching.py`).

O helper `utcnow()` substitui o `datetime.utcnow()` depreciado. **Sem migrations**: `create_all` cria tabelas faltantes mas **não** altera colunas. Exceção mínima: `_ensure_columns()` (`backend/database.py`) adiciona via `ALTER TABLE` colunas **novas e anuláveis** que faltem (ex.: campos de curadoria) — qualquer mudança além disso (renomear/tipar/NOT NULL) ainda exige recriar o banco (apagar o `.db`).

## Como rodar (local, sem Docker)

Execute sempre **a partir da raiz do projeto** (os caminhos relativos dependem disso). Os comandos abaixo usam bash (Linux/macOS); no Windows/PowerShell, troque a ativação do venv por `venv\Scripts\activate` e `export VAR=...` por `$env:VAR = "..."`.

```bash
# 1) criar/ativar venv e instalar dependências
python3 -m venv venv        # só na primeira vez (o venv é ignorado pelo git)
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt   # psycopg2-binary é OPCIONAL (só p/ PostgreSQL)

# 2) (opcional) segredos e foco: copie .env.example -> .env (gitignored) e preencha
#    PORTAL_TRANSPARENCIA_API_KEY (emendas) · FOCO_UF (ex.: SP) · FOCO_MUNICIPIO
#    GEMINI_API_KEY (curadoria LLM opcional — chave grátis em aistudio.google.com/apikey)
set -a; source .env; set +a   # carrega as variáveis no shell atual

# 3) subir o painel (cria banco/tabelas no 1º boot)
uvicorn backend.main:app --reload   # http://localhost:8000

# 4) pipeline completa: coleta (RSS+PNCP+emendas) -> relevância -> classificação -> enriquecimento
python run_pipeline.py
python run_pipeline.py --reset      # reprocessa tudo (após mudar regras)

# etapas/ferramentas individuais:
python collectors/validate_sources.py            # probe de saúde de TODAS as fontes
python collectors/rss/rss_collector.py
python collectors/api/pncp_collector.py --uf=SP  # PNCP, opcionalmente por estado
python collectors/api/finep_collector.py         # FINEP (chamadas abertas, sem chave)
python collectors/api/transparencia_collector.py --probe   # requer chave no ambiente
python processing/curate_llm.py --limit=20       # curadoria LLM (requer GEMINI_API_KEY)
python processing/classifier.py --reset
python processing/enrich.py --limit=10           # prazo/valor (regex + PDF), também roda na pipeline
python processing/seed_profiles.py               # perfis municipais de exemplo
```

> **Opcional — PostgreSQL:** `docker-compose up -d` e, antes de iniciar o servidor/coletores, defina a variável de ambiente:
> `export DATABASE_URL="postgresql://observatorio:observatorio_password@localhost:5432/observatorio_db"`
> (Windows/PowerShell: `$env:DATABASE_URL = "postgresql://..."`)

## Banco de dados

- O default SQLite é resolvido em `backend/database.py` (caminho absoluto para `database/observatorio.db`, com `check_same_thread=False` para o pool de threads do FastAPI).
- Para trocar de banco, defina `DATABASE_URL` (ex.: PostgreSQL). As tabelas são criadas por `create_db_and_tables()` no `lifespan` do FastAPI.
- O arquivo `.db` é ignorado pelo git. Para "resetar" o banco: apague o arquivo e reinicie o servidor.

## Coletores — convenções

- Cada coletor é um **script Python autônomo** (executável por cron/CI), desacoplado do processo da API. Garantem o schema chamando `create_db_and_tables()` no início, então rodam mesmo sem o servidor ter subido antes.
- Importam engine/modelos do backend ajustando `sys.path` para a raiz do projeto.
- **Constroem as oportunidades via `processing.normalizer.normalize_opportunity`** (não instanciam `Opportunity` direto): isso limpa HTML, apara texto e canonicaliza a URL antes de persistir.
- **Deduplicam pela URL canônica** (`op.url`, consultando a existência antes de inserir) e dão `commit` ao final.
- Para adicionar/ajustar uma fonte: edite o **registro central** `collectors/sources.py` (o coletor RSS lê dele). Fontes com API própria têm coletor dedicado (`pncp_collector.py`, `transparencia_collector.py`). Rode `collectors/validate_sources.py` para checar a saúde de todas ao vivo.
- **Segredos nunca no código/git:** chaves (ex.: Portal da Transparência) vêm só de variáveis de ambiente (`.env`, gitignored); coletores que precisam de chave **pulam sem erro** se ela faltar.

## Convenções gerais

- Código e comentários em **português**.
- **Custo zero:** o núcleo (relevância/classificação/extração/busca/matching) é determinístico (regras, regex, PyMuPDF, FTS5, overlap) e roda sem chave alguma. LLM só na **curadoria opcional** (`processing/curate_llm.py`, Gemini free tier, gateada por `GEMINI_API_KEY` — pula sem erro). Antes de adicionar dependência, confirmar.
- **Sem migrations:** schema via `SQLModel.metadata.create_all` (cria tabelas faltantes, não altera colunas). Mudança de modelo → recriar o banco.
- **Commit por tarefa; PR por etapa** para a `main`.

## Workflow Git

- **Branch por dev/issue:** `dev/issues-x-y` (ex.: `andre/issues-1-2`, `diego/issues-3-4`).
- Merge via **Pull Request** para `main`, referenciando issues no PR (`resolves #n`).
- Desenvolvedores: **André** (`maia-andre`) e **Diego**.

## Roadmap (resumo)

0. **MVP de Descoberta** ✅
1. **Radar Institucional** ✅ — normalização, histórico, dedup, filtros, busca
2. **Curadoria Automatizada** ✅ — classificação ponderada por regras (multi-rótulo) + porta de relevância
3. **Assistente de IA** → substituída pela **Fase 3-lite** (determinística, sem LLM): extração de prazo/valor por regex + PDF
4. **Matching Institucional** ✅ (PoC) — `processing/matching.py` + perfis municipais
5. **Centro de Inteligência** — monitoramento legislativo/orçamentário (futuro)

Detalhamento de cada fase em `README.md` e `docs/`.
