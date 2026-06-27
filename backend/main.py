import math
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from sqlalchemy import func, or_

from backend.database import create_db_and_tables, engine
from backend.models import Opportunity, MunicipalProfile
from backend.search import setup_fts, search_ranked_ids
from processing.matching import rank_opportunities

# Quantidade de oportunidades exibidas por página no painel.
PAGE_SIZE = 20


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    setup_fts(engine)  # índice FTS5 para a busca (no-op fora do SQLite)
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
    relevancia: str = "relevantes",
    prazo: str = "",
    valor: str = "",
    municipio: int = -1,
    page: int = 1,
):
    """Painel com busca full-text (FTS5/BM25), filtros, ordenação e paginação."""
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
        profiles = session.exec(
            select(MunicipalProfile).order_by(MunicipalProfile.name)
        ).all()
        # Município-foco padrão (env FOCO_MUNICIPIO) quando nenhum é informado (-1).
        # municipio == 0 = "Sem município" escolhido explicitamente (não re-aplica o foco).
        if municipio < 0:
            foco = os.getenv("FOCO_MUNICIPIO")
            alvo = next((p for p in profiles if p.name == foco), None) if foco else None
            municipio = alvo.id if alvo else 0

        # Filtros comuns (fonte/categoria/relevância), aplicáveis a qualquer query.
        def aplica_filtros(stmt):
            if source:
                stmt = stmt.where(Opportunity.source == source)
            if category:
                stmt = stmt.where(Opportunity.category == category)
            if relevancia != "todas":
                stmt = stmt.where(Opportunity.status != "irrelevante")
            # Filtro por prazo (deadline)
            if prazo == "com":
                stmt = stmt.where(Opportunity.deadline.is_not(None))
            elif prazo in ("30", "90"):
                agora = datetime.now()
                stmt = stmt.where(
                    Opportunity.deadline.is_not(None),
                    Opportunity.deadline >= agora,
                    Opportunity.deadline <= agora + timedelta(days=int(prazo)),
                )
            # Filtro por valor
            if valor == "com":
                stmt = stmt.where(Opportunity.value.is_not(None))
            elif valor == "100mil":
                stmt = stmt.where(Opportunity.value >= 100_000)
            elif valor == "1mi":
                stmt = stmt.where(Opportunity.value >= 1_000_000)
            return stmt

        # Com texto de busca, tenta o FTS5 (ranking por relevância). search_ranked_ids
        # devolve None se não der para usar FTS (não-SQLite/índice ausente) → cai no LIKE.
        ranked_ids = search_ranked_ids(engine, q) if q else None
        usando_fts = ranked_ids is not None
        profile = session.get(MunicipalProfile, municipio) if municipio else None

        matches = {}  # op.id -> (score, justificativa), preenchido no modo aderência
        if profile:
            # Modo aderência: ranqueia por score de matching ao município (paginação em Python).
            base = aplica_filtros(select(Opportunity))
            if ranked_ids is not None:        # busca textual ativa: restringe aos hits do FTS
                base = base.where(Opportunity.id.in_(ranked_ids))
            elif q:                            # FTS indisponível: fallback LIKE
                termo = f"%{q}%"
                base = base.where(or_(
                    Opportunity.title.ilike(termo),
                    Opportunity.description.ilike(termo),
                ))
            ranqueadas = rank_opportunities(profile, session.exec(base).all())
            total = len(ranqueadas)
            total_pages = max(1, math.ceil(total / PAGE_SIZE))
            page = min(page, total_pages)
            offset = (page - 1) * PAGE_SIZE
            pagina = ranqueadas[offset:offset + PAGE_SIZE]
            opportunities = [op for op, _, _ in pagina]
            matches = {op.id: (s, j) for op, s, j in pagina}
        elif usando_fts:
            # Caminho FTS: ordena por relevância (BM25). Como o conjunto é pequeno,
            # aplica os demais filtros e pagina em Python, preservando a ordem do rank.
            if ranked_ids:
                objs = session.exec(
                    aplica_filtros(select(Opportunity).where(Opportunity.id.in_(ranked_ids)))
                ).all()
                posicao = {oid: i for i, oid in enumerate(ranked_ids)}
                objs.sort(key=lambda o: posicao.get(o.id, len(ranked_ids)))
            else:
                objs = []
            total = len(objs)
            total_pages = max(1, math.ceil(total / PAGE_SIZE))
            page = min(page, total_pages)
            offset = (page - 1) * PAGE_SIZE
            opportunities = objs[offset:offset + PAGE_SIZE]
        else:
            # Caminho SQL: filtros + LIKE (fallback) + ordenação por data + paginação no banco.
            statement = aplica_filtros(select(Opportunity))
            count_statement = aplica_filtros(select(func.count()).select_from(Opportunity))
            if q:  # FTS indisponível (ex.: PostgreSQL): fallback textual por LIKE
                termo = f"%{q}%"
                filtro_texto = or_(
                    Opportunity.title.ilike(termo),
                    Opportunity.description.ilike(termo),
                )
                statement = statement.where(filtro_texto)
                count_statement = count_statement.where(filtro_texto)

            if order == "asc":
                statement = statement.order_by(Opportunity.published_date.asc())
            else:
                statement = statement.order_by(Opportunity.published_date.desc())

            total = session.exec(count_statement).one()
            total_pages = max(1, math.ceil(total / PAGE_SIZE))
            page = min(page, total_pages)
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
                "relevancia": relevancia,
                "prazo": prazo,
                "valor": valor,
                "municipio": municipio,
                "profiles": profiles,
                "matches": matches,
                "usando_fts": usando_fts,
            },
        )


@app.get("/opportunity/{op_id}")
def opportunity_detail(request: Request, op_id: int):
    """Página de detalhe de uma oportunidade."""
    with Session(engine) as session:
        op = session.get(Opportunity, op_id)
        if op is None:
            raise HTTPException(status_code=404, detail="Oportunidade não encontrada")
        return templates.TemplateResponse(
            request=request, name="detail.html", context={"op": op}
        )
