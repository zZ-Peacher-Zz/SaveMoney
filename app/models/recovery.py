from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecoveryEmail(Base):
    __tablename__ = "recovery_emails"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)


class RecoveryToken(Base):
    __tablename__ = "recovery_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    email: Mapped[str] = mapped_column(String(254))
    purpose: Mapped[str] = mapped_column(String(20))
    expires_at: Mapped[int] = mapped_column(Integer)


class RecoveryLimit(Base):
    __tablename__ = "recovery_limits"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    started_at: Mapped[int] = mapped_column(Integer)
    count: Mapped[int] = mapped_column(Integer)
