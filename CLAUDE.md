# CLAUDE.md

Orientações para o Claude Code (e para os desenvolvedores) trabalharem neste repositório. Documentação canônica complementar em `README.md` e `docs/`.

## Visão geral

**Observatório de Oportunidades Institucionais** — plataforma para monitorar automaticamente fontes públicas (RSS, APIs, sitemaps, HTML) e consolidar "oportunidades" institucionais (editais, premiações, emendas parlamentares, convênios, programas federais/estaduais, chamamentos públicos etc.) em uma base única. É uma PoC evolutiva, organizada em fases (0 a 5).

## Estado atual — Fase 0 (MVP de Descoberta)

- Fluxo validado de ponta a ponta: **coleta autônoma → persistência → painel HTML**. A "Validação 1" coletou ~140 oportunidades de 8 fontes iniciais.
- Backend FastAPI + SQLModel; painel server-side com Jinja2 + PicoCSS (via CDN).
- **Banco padrão: SQLite** (`database/observatorio.db`, sem Docker). PostgreSQL continua suportado via `DATABASE_URL` e é o alvo para fases futuras.
- Em aberto: validar fontes remanescentes — issues **#3** (RSS) e **#4** (API).
- Fora do escopo da Fase 0: IA, classificação, alertas, OCR.

## Stack

- **Linguagem:** Python 3.10+
- **Web/API:** FastAPI + Uvicorn
- **ORM/validação:** SQLModel (envelopa SQLAlchemy + Pydantic)
- **Banco:** SQLite (padrão Fase 0) · PostgreSQL (opcional/alvo futuro)
- **Coleta:** requests, feedparser (RSS), BeautifulSoup + lxml (XML/sitemap)
- **Painel:** Jinja2 + PicoCSS
- **Futuro:** frontend React/Next.js; infra Docker/Nginx

## Estrutura de diretórios

- `backend/` — app FastAPI
  - `main.py` — rotas e painel (rota `/` renderiza `index.html`)
  - `database.py` — criação do engine e das tabelas
  - `models.py` — modelo `Opportunity`
  - `templates/index.html` — painel (Jinja2 + PicoCSS)
- `collectors/` — scripts autônomos de coleta, um subdiretório por tipo: `rss/`, `api/`, `html/`, `sitemap/`
- `database/` — arquivo SQLite local (ignorado pelo git)
- `docs/` — documentação por fase (`arquitetura/`, `fase 0/`, `fase 1/`)
- `docker-compose.yml` — **opcional**, apenas para quem quiser rodar com PostgreSQL
- `frontend/` — reservado para fases futuras

## Modelo de dados (`Opportunity`)

`id` (PK) · `title` · `description?` · `url` (**único e indexado — chave de deduplicação**) · `published_date?` · `source` · `collected_at`. Definido em `backend/models.py`.

## Como rodar (local, sem Docker)

Use o `venv` já existente na raiz. Execute sempre **a partir da raiz do projeto** (os caminhos relativos dependem disso).

```powershell
# 1) ativar venv e instalar dependências
venv\Scripts\activate
pip install -r requirements.txt

# 2) subir o painel (cria o banco e as tabelas no 1º boot)
uvicorn backend.main:app --reload
# painel em http://localhost:8000

# 3) em outro terminal (venv ativo), popular o banco
python collectors/rss/rss_collector.py
python collectors/api/api_collector.py
```

> **Opcional — PostgreSQL:** `docker-compose up -d` e, antes de iniciar o servidor/coletores, defina a variável de ambiente:
> `$env:DATABASE_URL = "postgresql://observatorio:observatorio_password@localhost:5432/observatorio_db"`

## Banco de dados

- O default SQLite é resolvido em `backend/database.py` (caminho absoluto para `database/observatorio.db`, com `check_same_thread=False` para o pool de threads do FastAPI).
- Para trocar de banco, defina `DATABASE_URL` (ex.: PostgreSQL). As tabelas são criadas por `create_db_and_tables()` no `lifespan` do FastAPI.
- O arquivo `.db` é ignorado pelo git. Para "resetar" o banco: apague o arquivo e reinicie o servidor.

## Coletores — convenções

- Cada coletor é um **script Python autônomo** (executável por cron/CI), desacoplado do processo da API.
- Importam engine/modelos do backend ajustando `sys.path` para a raiz do projeto.
- **Deduplicam por `url`** (consultam a existência antes de inserir) e dão `commit` ao final.
- Para adicionar uma fonte: edite a lista `*_SOURCES` no coletor do tipo correspondente, ou crie um novo script no subdiretório adequado seguindo o mesmo padrão (Session do SQLModel → checagem por `url` → `commit`).
- O coletor de API/sitemap limita a 5 itens por fonte (proposital, para o MVP).

## Convenções gerais

- Código e comentários em **português**.
- **Sem migrations** na Fase 0: o schema vem de `SQLModel.metadata.create_all`. Mudanças no modelo exigem recriar o banco (ou migration manual).
- Manter a Fase 0 enxuta — não antecipar funcionalidades de fases posteriores.

## Workflow Git

- **Branch por dev/issue:** `dev/issues-x-y` (ex.: `andre/issues-1-2`, `diego/issues-3-4`).
- Merge via **Pull Request** para `main`, referenciando issues no PR (`resolves #n`).
- Desenvolvedores: **André** (`maia-andre`) e **Diego**.

## Roadmap (resumo)

0. **MVP de Descoberta** (atual) — coleta + persistência + painel
1. **Radar Institucional** — inbox única, histórico, deduplicação, filtros, pesquisa
2. **Curadoria Automatizada** — classificação por regras
3. **Assistente de IA** — LLM/OCR (resumo, classificação semântica, extração de prazos)
4. **Matching Institucional** — score de aderência oportunidade × município
5. **Centro de Inteligência** — monitoramento legislativo/orçamentário e apoio à decisão

Detalhamento de cada fase em `README.md` e `docs/`.
