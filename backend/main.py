from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from contextlib import asynccontextmanager

from backend.database import create_db_and_tables, engine
from backend.models import Opportunity

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="backend/templates")

@app.get("/")
def read_root(request: Request):
    with Session(engine) as session:
        # Pega as últimas oportunidades ordenadas por data
        opportunities = session.exec(select(Opportunity).order_by(Opportunity.published_date.desc())).all()
        return templates.TemplateResponse(
            request=request, name="index.html", context={"opportunities": opportunities}
        )
