from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Opportunity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    url: str = Field(unique=True, index=True)
    published_date: Optional[datetime] = None
    source: str
    collected_at: datetime = Field(default_factory=datetime.utcnow)
