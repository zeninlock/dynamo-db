from pydantic import BaseModel
from typing import Optional


class PutRequest(BaseModel):
    value: str


class Record(BaseModel):
    key: str
    value: Optional[str]
    version: int
    deleted: bool
    updated_at: str