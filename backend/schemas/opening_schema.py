from typing import Literal, Optional

from pydantic import BaseModel


class OpeningCreate(BaseModel):
    name: str
    color: Literal["white", "black"]


class OpeningUpdate(BaseModel):
    name: str


class OpeningRead(BaseModel):
    id: int
    name: str
    color: str
    node_count: int
    accuracy: Optional[float] = None
    in_seed: bool = False
    seed_visibility: Optional[Literal["public", "private"]] = None
    is_favorite: bool = False


class FavoriteUpdate(BaseModel):
    value: bool


class SeedSaveRequest(BaseModel):
    visibility: Literal["public", "private"]
    evaluate: bool = False
    allow_external: bool = False


class SeedRestoreRequest(BaseModel):
    file_key: str


class SeedFileInfo(BaseModel):
    file_key: str
    name: str
    visibility: Literal["public", "private"]
    state: Literal["in_db", "deleted_locally", "new"]


class SeedFileRead(BaseModel):
    path: str
    job_id: Optional[str] = None
    message: Optional[str] = None
