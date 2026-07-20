from typing import Literal

from pydantic import BaseModel, ConfigDict


class OperationCreate(BaseModel):
    type: Literal["insert", "delete", "update"]
    pos: int
    text: str = ""
    length: int = 0
    client_version: int


class OperationRead(BaseModel):
    id: int
    document_id: int
    user_id: int
    op_type: str
    pos: int
    text: str
    length: int
    version: int
    model_config = ConfigDict(from_attributes=True)


class DocumentContent(BaseModel):
    content: str
    version: int
