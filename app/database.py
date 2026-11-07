"""PostgreSQL engine and request-scoped SQLAlchemy sessions."""
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def normalize_database_url(value):
    if not value:
        raise RuntimeError("Set DATABASE_URL in .env or Render Environment")
    if value.startswith("postgres://"):
        value = "postgresql+psycopg://" + value[len("postgres://"):]
    elif value.startswith("postgresql://"):
        value = "postgresql+psycopg://" + value[len("postgresql://"):]
    try:
        url = make_url(value)
    except Exception:
        raise RuntimeError("DATABASE_URL is not a valid database connection URL") from None
    if url.drivername not in {"postgresql+psycopg", "sqlite", "sqlite+pysqlite"}:
        raise RuntimeError("Use a PostgreSQL DATABASE_URL; SQLite URLs are supported for isolated tests only")
    return url


def create_db_engine(value):
    url = normalize_database_url(value)
    options = {"pool_pre_ping": True, "hide_parameters": True}
    if url.get_backend_name() == "sqlite":
        options["connect_args"] = {"check_same_thread": False}
    else:
        options["connect_args"] = {"connect_timeout": 10}
        options.update(pool_size=5, max_overflow=5)
    return create_engine(url, **options)


engine = create_db_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    with SessionLocal() as db:
        try:
            yield db
        except Exception:
            db.rollback()
            raise


def init_db():
    from app import models  # noqa: F401
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError:
        raise RuntimeError("PostgreSQL initialization failed. Check DATABASE_URL, credentials, network and schema permissions. Use Render's External Database URL for local connections.") from None
