from sqlmodel import SQLModel, create_engine
from sqlalchemy import inspect, text
import os

# Diretório raiz do projeto (um nível acima de /backend), usado para resolver
# o caminho do arquivo SQLite independentemente de onde o processo é iniciado.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "database", "observatorio.db").replace("\\", "/")

# Banco padrão da Fase 0: SQLite (arquivo local, sem necessidade de Docker).
# Para usar PostgreSQL, basta definir a variável de ambiente DATABASE_URL, ex.:
#   postgresql://observatorio:observatorio_password@localhost:5432/observatorio_db
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

# O SQLite exige check_same_thread=False para funcionar com o pool de threads do FastAPI.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

def _ensure_columns():
    """"Migração" mínima: adiciona colunas novas anuláveis a tabelas já criadas.

    O projeto não usa migrations (`create_all` cria tabelas faltantes mas não as
    altera). Para o caso comum de coluna NOVA e ANULÁVEL (ex.: campos de curadoria),
    um `ALTER TABLE ... ADD COLUMN` resolve sem recriar o banco. Qualquer mudança
    além disso (renomear/tipar/NOT NULL) continua exigindo recriar o `.db`.
    """
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            existentes = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in existentes or not col.nullable:
                    continue
                tipo = col.type.compile(engine.dialect)
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {tipo}"))


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _ensure_columns()
