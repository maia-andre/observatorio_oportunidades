"""Seed de perfis municipais de exemplo — Etapa C (matching).

Como ainda não há integração com dados reais de municípios, este script popula
alguns perfis de exemplo para demonstrar o matching de aderência. Idempotente:
não duplica perfis já existentes (checa nome + UF).

Uso (a partir da raiz do projeto):
    python processing/seed_profiles.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from backend.database import engine, create_db_and_tables
from backend.models import MunicipalProfile

# Interesses usam os nomes das categorias da taxonomia (ver processing/rules.py),
# o que faz a sobreposição de categorias do matching funcionar diretamente.
PERFIS = [
    # Município-foco real: São José dos Campos/SP (polo aeroespacial, tecnologia,
    # educação — ITA/INPE/Embraer/Univap). Perfil de interesses amplo e realista.
    {"name": "São José dos Campos", "uf": "SP",
     "interests": ("Inovação, Educação, Saúde, Sustentabilidade, Mobilidade, "
                   "Premiações, Convênios, Licitações, Tecnologia, Aeroespacial"),
     "population": 730_000},
    {"name": "Atibaia", "uf": "SP",
     "interests": "Educação, Inovação, Sustentabilidade, Premiações, Cultura",
     "population": 150_000},
    {"name": "Porto Velho", "uf": "RO",
     "interests": "Saúde, Mobilidade, Licitações, Convênios, Infraestrutura",
     "population": 540_000},
    {"name": "Município Modelo", "uf": "MG",
     "interests": "Educação, Saúde, Sustentabilidade, Inovação, Convênios",
     "population": 50_000},
]


def seed() -> int:
    create_db_and_tables()
    criados = 0
    with Session(engine) as session:
        for p in PERFIS:
            existe = session.exec(
                select(MunicipalProfile).where(
                    MunicipalProfile.name == p["name"],
                    MunicipalProfile.uf == p["uf"],
                )
            ).first()
            if not existe:
                session.add(MunicipalProfile(**p))
                criados += 1
        session.commit()
    print(f"> {criados} perfil(is) criado(s) ({len(PERFIS) - criados} já existia(m)).")
    return criados


if __name__ == "__main__":
    seed()
