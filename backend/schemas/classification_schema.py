from pydantic import BaseModel


class ClassificationRead(BaseModel):
    key: str
    label: str
    symbol: str
    color: str