from sqlalchemy import Integer, String, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    expires_at: Mapped[int] = mapped_column(Integer)


class UserAvatar(Base):
    __tablename__ = "user_avatars"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    image: Mapped[bytes] = mapped_column(LargeBinary)
