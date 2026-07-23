from pydantic import BaseModel
from typing import Optional

class PutRequest(BaseModel):
    value: str
    version: Optional[int] = None

class DeleteRequest(BaseModel):
    version: Optional[int] = None

#below is the Record model that represents a stored record in the key-value store.
#It includes the key, value, version, deleted status, and updated_at timestamp.
class Record(BaseModel):
    key: str
    value: Optional[str]
    version: int
    deleted: bool
    updated_at: str