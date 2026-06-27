"""Camada de Normalização (Fase 1 - Radar Institucional).

Ponto único de padronização dos dados antes de persistir uma oportunidade.
Os coletores (RSS, API, Sitemap, HTML) constroem suas oportunidades através de
`normalize_opportunity`, garantindo títulos/descrições limpos, URLs canônicas
(usadas como chave de deduplicação) e datas naive consistentes no banco.
"""

import re
import warnings
from datetime import datetime
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

from backend.models import Opportunity

# Campos curtos que parecem URL/arquivo (ex.: alguns títulos do PNCP) fazem o
# BeautifulSoup emitir MarkupResemblesLocatorWarning. É inofensivo aqui (queremos
# só extrair texto), então silenciamos para não poluir a saída dos coletores.
try:
    from bs4 import MarkupResemblesLocatorWarning
    warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)
except ImportError:  # versões antigas do bs4
    warnings.filterwarnings("ignore", message=".*looks like a (URL|filename).*")

# Limites para evitar campos absurdamente longos vindos das fontes.
MAX_TITLE = 300
MAX_DESCRIPTION = 2000
MAX_SOURCE = 100

TITULO_PADRAO = "Sem Título"


def clean_text(value, max_length: Optional[int] = None) -> str:
    """Remove HTML, colapsa espaços/quebras e apara o texto (com corte opcional)."""
    if not value:
        return ""
    texto = BeautifulSoup(str(value), "html.parser").get_text(separator=" ")
    texto = re.sub(r"\s+", " ", texto).strip()
    if max_length and len(texto) > max_length:
        texto = texto[:max_length].rstrip() + "…"
    return texto


def normalize_url(url) -> str:
    """Canonicaliza a URL: apara espaços, remove fragmento (#...), normaliza
    esquema/host para minúsculas e remove a barra final do caminho.

    A URL canônica é a chave de deduplicação, então a normalização reduz
    duplicatas que diferem apenas por maiúsculas/host ou barra final.
    """
    if not url:
        return ""
    url = str(url).strip().split("#")[0]
    if not url:
        return ""
    parts = urlsplit(url)
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), netloc, path, parts.query, ""))


def normalize_date(value) -> Optional[datetime]:
    """Garante datetime naive (sem tzinfo) para consistência no banco."""
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=None) if value.tzinfo else value


def normalize_opportunity(
    *,
    title,
    url,
    source,
    description=None,
    published_date=None,
    category=None,
    deadline=None,
    value=None,
) -> Optional[Opportunity]:
    """Aplica a normalização e devolve um `Opportunity` pronto para persistir.

    Retorna ``None`` quando falta o campo essencial (URL válida) — nesse caso o
    item deve ser descartado pelo coletor.
    """
    url_n = normalize_url(url)
    if not url_n:
        return None

    return Opportunity(
        title=clean_text(title, MAX_TITLE) or TITULO_PADRAO,
        description=clean_text(description, MAX_DESCRIPTION) or None,
        url=url_n,
        source=clean_text(source, MAX_SOURCE),
        published_date=normalize_date(published_date),
        category=category,
        deadline=normalize_date(deadline),
        value=value,
    )
