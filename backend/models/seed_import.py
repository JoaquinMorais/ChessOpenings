from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class SeedImport(SQLModel, table=True):
    __tablename__ = "seed_import"

    id: Optional[int] = Field(default=None, primary_key=True)
    file_key: str = Field(unique=True)
    name: str
    content_hash: str
    imported_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
