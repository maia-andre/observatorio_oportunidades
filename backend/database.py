from sqlmodel import SQLModel, create_engine
import os

# Usamos a string de conexão alinhada com o docker-compose
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observatorio:observatorio_password@localhost:5432/observatorio_db")

engine = create_engine(DATABASE_URL, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
