from sqlalchemy import BigInteger, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GroupMessage(Base):
    __tablename__ = "group_messages"
    __table_args__ = (Index("ix_group_messages_group_id_id", "group_id", "id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[int] = mapped_column(BigInteger)
