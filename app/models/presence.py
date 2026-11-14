from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserPresence(Base):
    __tablename__ = "user_presence"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_seen: Mapped[int] = mapped_column(BigInteger)
