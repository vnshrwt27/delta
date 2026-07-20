from datetime import datetime
from typing import List

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.document import Document, DocumentPermission
class User(Base):
    __tablename__ = "users"

    id : Mapped[int] = mapped_column(primary_key= True, index= True)
    username : Mapped[str] = mapped_column(String(50), unique= True, nullable= True, index= True)
    email : Mapped[str] = mapped_column(String(120), unique= True, nullable= False , index=True)
    password_hash : Mapped[str] = mapped_column(String(128), nullable= False)

    created_at : Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Documents are mapped to their owners
    documents : Mapped[List["Document"]] = relationship(back_populates="owner")
    # DocumentPermissions are mapped to each user
    permissions : Mapped[List["DocumentPermission"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username!r})>"
