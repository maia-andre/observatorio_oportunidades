---
name: verify
description: Como verificar mudanças do Observatório de ponta a ponta (painel FastAPI + pipeline)
---

# Verificação do Observatório

Superfície principal: painel HTTP (Jinja2 renderizado no servidor) — verificar com `curl` + `grep` no HTML.

## Subir o painel (porta isolada, não usar a 8000 do dev)

```bash
set -a; source .env; set +a   # FOCO_MUNICIPIO/FOCO_UF mudam o comportamento default do painel!
./venv/bin/uvicorn backend.main:app --port 8010
```

## Gotchas

- **`FOCO_MUNICIPIO` ativa o modo aderência por padrão** — para exercitar o caminho SQL puro, use `?municipio=0`; para o caminho FTS, adicione `?q=...`. São 3 caminhos de query distintos em `backend/main.py` (SQL, FTS, matching) — filtros novos precisam ser testados nos três.
- **CSS inline na `base.html`**: `grep -c 'alguma-classe'` no HTML conta também a regra CSS do `<style>` — grep pelo uso (`class="..."`) e não pelo nome solto.
- Estado do banco: `database/observatorio.db` (SQLite). Consultas rápidas via `./venv/bin/python -c "import sqlite3; ..."`. Para dados frescos: `python run_pipeline.py`.
- Coletores/pipeline: superfície é o stdout do script (`run_pipeline.py`, `collectors/*.py`). O Portal da Transparência precisa de chave no ambiente; sem ela o coletor pula sem erro (é o comportamento esperado, não falha).

## Fluxos que valem a pena dirigir

- Painel default (aderência SJC) · `?municipio=0` (SQL) · `?q=termo` (FTS) · combinações de filtros.
- Página de detalhe `/opportunity/{id}` (pegar id via sqlite).
- Paginação: conferir que params novos entram no `qs` de `index.html` (fácil de esquecer).
