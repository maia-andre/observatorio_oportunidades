"""Busca full-text com SQLite FTS5 (ranking BM25) — Etapa B (B2).

Cria uma tabela virtual FTS5 de **conteúdo externo**, espelhando `opportunity`
(título, descrição e **resumo da curadoria LLM**) e mantida em sincronia por
triggers, e oferece busca ranqueada por relevância (BM25 com pesos por coluna:
título > resumo > descrição). O resumo entra no índice pelo trigger de UPDATE,
já que a curadoria roda depois da inserção.

É específico do SQLite; com PostgreSQL (alvo futuro) tudo aqui vira no-op e o
`main.py` cai para a busca por LIKE. O tokenizer usa `remove_diacritics 2`, então
a busca é **acento-insensível** nos dois lados: "saude" casa "saúde" e vice-versa.
"""

import re

from sqlalchemy import text


def is_sqlite(engine) -> bool:
    return engine.dialect.name == "sqlite"


def setup_fts(engine) -> bool:
    """Cria a tabela FTS5 + triggers (idempotente) e reindexa. No-op fora do SQLite.

    Os triggers ficam no schema do banco, então qualquer processo que insira em
    `opportunity` (os coletores, inclusive) mantém o índice em dia; o 'rebuild'
    cobre as linhas inseridas antes de o índice existir. Retorna True se o FTS
    está pronto para uso.
    """
    if not is_sqlite(engine):
        return False
    try:
        with engine.begin() as conn:
            # Migração de schema do índice: CREATE ... IF NOT EXISTS não atualiza
            # definições antigas, então se o índice existe sem a coluna `summary`
            # (versão anterior), derruba tabela + triggers e recria — o rebuild
            # abaixo repopula tudo a partir de `opportunity`.
            existe = conn.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE name='opportunity_fts'"
            )).scalar()
            tem_summary = conn.execute(text(
                "SELECT count(*) FROM pragma_table_info('opportunity_fts') WHERE name='summary'"
            )).scalar()
            if existe and not tem_summary:
                for trigger in ("opportunity_ai", "opportunity_ad", "opportunity_au"):
                    conn.execute(text(f"DROP TRIGGER IF EXISTS {trigger}"))
                conn.execute(text("DROP TABLE opportunity_fts"))
            conn.execute(text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS opportunity_fts USING fts5("
                "title, description, summary, content='opportunity', content_rowid='id', "
                "tokenize=\"unicode61 remove_diacritics 2\")"
            ))
            conn.execute(text(
                "CREATE TRIGGER IF NOT EXISTS opportunity_ai AFTER INSERT ON opportunity BEGIN "
                "INSERT INTO opportunity_fts(rowid, title, description, summary) "
                "VALUES (new.id, new.title, new.description, new.summary); END"
            ))
            conn.execute(text(
                "CREATE TRIGGER IF NOT EXISTS opportunity_ad AFTER DELETE ON opportunity BEGIN "
                "INSERT INTO opportunity_fts(opportunity_fts, rowid, title, description, summary) "
                "VALUES('delete', old.id, old.title, old.description, old.summary); END"
            ))
            conn.execute(text(
                "CREATE TRIGGER IF NOT EXISTS opportunity_au AFTER UPDATE ON opportunity BEGIN "
                "INSERT INTO opportunity_fts(opportunity_fts, rowid, title, description, summary) "
                "VALUES('delete', old.id, old.title, old.description, old.summary); "
                "INSERT INTO opportunity_fts(rowid, title, description, summary) "
                "VALUES (new.id, new.title, new.description, new.summary); END"
            ))
            conn.execute(text("INSERT INTO opportunity_fts(opportunity_fts) VALUES('rebuild')"))
        return True
    except Exception:
        # Build do SQLite sem FTS5: a busca cai para LIKE no main.py.
        return False


def _build_match(q: str):
    """Converte a busca livre em expressão FTS5 segura: prefixo (`termo*`) por token.

    Tokeniza por ``\\w+`` (descarta aspas/operadores que quebrariam o MATCH) e monta
    ``"termo"* "outro"*`` — casamento por prefixo e em conjunção (AND) dos termos.
    Retorna None se não sobrar nenhum token.
    """
    tokens = re.findall(r"\w+", q, flags=re.UNICODE)
    if not tokens:
        return None
    return " ".join(f'"{t}"*' for t in tokens)


def search_ranked_ids(engine, q: str, limit: int = 1000):
    """ids de `opportunity` que casam com `q`, ordenados por BM25 (melhor primeiro).

    Retorna None quando não dá para usar FTS (não-SQLite, índice ausente ou consulta
    sem tokens) — sinal para o chamador usar o caminho LIKE. Lista vazia significa
    "FTS funcionou, zero resultados".
    """
    if not is_sqlite(engine):
        return None
    match = _build_match(q)
    if match is None:
        return None
    try:
        with engine.connect() as conn:
            # Pesos por coluna (ordem do CREATE): título 3×, descrição 1×, resumo 2× —
            # bater no título vale mais; o resumo curado é limpo e fica entre os dois.
            rows = conn.execute(
                text("SELECT rowid FROM opportunity_fts WHERE opportunity_fts MATCH :m "
                     "ORDER BY bm25(opportunity_fts, 3.0, 1.0, 2.0) LIMIT :lim"),
                {"m": match, "lim": limit},
            ).all()
        return [r[0] for r in rows]
    except Exception:
        return None
