from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.users import User
class Document(Base):
    
    __tablename__ = "documents"

    id : Mapped[int] = mapped_column(primary_key= True, index= True)
    title : Mapped[str] = mapped_column(String(250), default= "Untitled")
    content : Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=0)
    owner_id : Mapped[int] = mapped_column(ForeignKey("users.id"), nullable= False, index=True)
    created_at : Mapped[datetime] = mapped_column(DateTime, server_default= func.now())
    updated_at : Mapped[datetime] = mapped_column(DateTime , onupdate=func.now())

    owner : Mapped["User"] = relationship(back_populates="documents")
    permissions: Mapped[list["DocumentPermission"]] = relationship(back_populates="document")
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title={self.title!r})>"

class DocumentPermission(Base):
    __tablename__ = "document_permissions"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    permission: Mapped[str] = mapped_column(String(10), default="read")  # "read" | "write" | "admin"
    __table_args__ = (UniqueConstraint("user_id", "document_id"),)
    user: Mapped["User"] = relationship(back_populates="permissions")
    document: Mapped["Document"] = relationship(back_populates="permissions")
    def __repr__(self) -> str:
        return f"<DocumentPermission(user={self.user_id}, doc={self.document_id}, perm={self.permission!r})>"
