import os
import unittest
os.environ.setdefault("DATABASE_URL", "sqlite://")

from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from app.database import Base, create_db_engine, normalize_database_url
from app import models


class PostgresConfigTests(unittest.TestCase):
    def test_render_urls_use_psycopg(self):
        for scheme in ("postgres://", "postgresql://", "postgresql+psycopg://"):
            url = normalize_database_url(scheme + "user:pass@localhost/money")
            self.assertEqual(url.drivername, "postgresql+psycopg")
            self.assertEqual(url.database, "money")

    def test_encoded_password_and_ssl_query_are_preserved(self):
        url = normalize_database_url("postgresql://user:p%40ss%2Fword@localhost/money?sslmode=require")
        self.assertEqual(url.password, "p@ss/word")
        self.assertEqual(url.query["sslmode"], "require")
        engine = create_db_engine(url.render_as_string(hide_password=False))
        self.assertEqual(engine.dialect.driver, "psycopg")
        engine.dispose()

    def test_all_models_compile_for_postgresql(self):
        statements = {table.name: str(CreateTable(table).compile(dialect=postgresql.dialect()))
                      for table in Base.metadata.sorted_tables}
        self.assertIn("BYTEA", statements["user_avatars"])
        self.assertIn("DATE", statements["user_expenses"])
        self.assertIn("SERIAL", statements["users"])
        self.assertIn("UNIQUE (group_id, user_id, month)", statements["group_incomes"])

    def test_invalid_configuration_never_exposes_secret(self):
        for value in (None, "mongodb://user:secret@example.com/db", "unknown://user:secret@example.com/db"):
            with self.assertRaises(RuntimeError) as error:
                normalize_database_url(value)
            self.assertNotIn("secret", str(error.exception))
