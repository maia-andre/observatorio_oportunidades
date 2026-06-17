import math
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from sqlalchemy import func, or_

from backend.database import create_db_and_tables, engine
from backend.models import Opportunity

# Quantidade de oportunidades exibidas por página no painel.
PAGE_SIZE = 20


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="backend/templates")


@app.get("/")
def read_root(
    request: Request,
    q: str = "",
    source: str = "",
    category: str = "",
    order: str = "desc",
    page: int = 1,
):
    """Painel com busca, filtro por fonte/categoria, ordenação por data e paginação."""
    if page < 1:
        page = 1

    with Session(engine) as session:
        # Fontes e categorias distintas para alimentar os seletores de filtro.
        sources = session.exec(
            select(Opportunity.source).distinct().order_by(Opportunity.source)
        ).all()
        categories = session.exec(
            select(Opportunity.category)
            .where(Opportunity.category.is_not(None))
            .distinct()
            .order_by(Opportunity.category)
        ).all()

        # Query base + query de contagem (compartilham os mesmos filtros).
        statement = select(Opportunity)
        count_statement = select(func.count()).select_from(Opportunity)

        if q:
            termo = f"%{q}%"
            filtro_texto = or_(
                Opportunity.title.ilike(termo),
                Opportunity.description.ilike(termo),
            )
            statement = statement.where(filtro_texto)
            count_statement = count_statement.where(filtro_texto)

        if source:
            statement = statement.where(Opportunity.source == source)
            count_statement = count_statement.where(Opportunity.source == source)

        if category:
            statement = statement.where(Opportunity.category == category)
            count_statement = count_statement.where(Opportunity.category == category)

        # Ordenação por data de publicação (padrão: mais recentes primeiro).
        if order == "asc":
            statement = statement.order_by(Opportunity.published_date.asc())
        else:
            statement = statement.order_by(Opportunity.published_date.desc())

        total = session.exec(count_statement).one()
        total_pages = max(1, math.ceil(total / PAGE_SIZE))
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * PAGE_SIZE
        opportunities = session.exec(
            statement.offset(offset).limit(PAGE_SIZE)
        ).all()

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "opportunities": opportunities,
                "sources": sources,
                "categories": categories,
                "total": total,
                "page": page,
                "total_pages": total_pages,
                "q": q,
                "source": source,
                "category": category,
                "order": order,
            },
        )
