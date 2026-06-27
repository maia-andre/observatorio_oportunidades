from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Retorna o UTC atual sem tzinfo (datetimes naive, padrão do projeto).

    Substitui datetime.utcnow() (depreciado) preservando o comportamento naive
    usado no restante do código (ex.: coletores que removem o tzinfo das datas).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Opportunity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    url: str = Field(unique=True, index=True)
    published_date: Optional[datetime] = None
    source: str
    # Campos da Fase 1 (estrutura mínima de dados do Radar Institucional).
    # Permanecem nulos/"novo" até serem preenchidos pela curadoria/classificação (Fase 2).
    category: Optional[str] = Field(default=None, index=True)
    # Multi-rótulo (Etapa B/B1b): categorias secundárias separadas por vírgula,
    # ordenadas por score; `category` acima é o rótulo principal.
    categories: Optional[str] = Field(default=None)
    deadline: Optional[datetime] = None  # prazo da oportunidade (extraível na Fase 3-lite)
    value: Optional[float] = Field(default=None)  # valor/teto em R$, quando extraível
    # Score 0..1 da porta de relevância (Etapa A): quão "oportunidade" o item parece.
    # None = ainda não avaliado; itens abaixo do limiar recebem status "irrelevante".
    relevance_score: Optional[float] = Field(default=None, index=True)
    status: str = Field(default="novo", index=True)
    collected_at: datetime = Field(default_factory=utcnow)


class MunicipalProfile(SQLModel, table=True):
    """Perfil de um município para o matching de oportunidades (Etapa C).

    `interests` lista as áreas de interesse (nomes de categorias e/ou palavras-chave)
    separadas por vírgula — usadas pelo motor de matching para medir a aderência.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    uf: str = Field(index=True)
    interests: str
    population: Optional[int] = Field(default=None)
