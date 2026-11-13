"""Opt-in PostgreSQL tests in a temporary schema, never production tables."""
import os
import unittest
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, create_db_engine
from app.models.user import User


@unittest.skipUnless(os.getenv("POSTGRES_TEST_URL"), "POSTGRES_TEST_URL not configured")
class PostgresIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_db_engine(os.environ["POSTGRES_TEST_URL"])
        self.schema = "savemoney_test_" + uuid4().hex
        with self.engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.bind = self.engine.execution_options(schema_translate_map={None: self.schema})
        Base.metadata.create_all(self.bind)

    def tearDown(self):
        with self.engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        self.engine.dispose()

    def test_serial_ids_and_transaction_rollback(self):
        with Session(self.bind) as db:
            alice = User(username="alice", password_hash="hash")
            db.add(alice)
            db.commit()
            self.assertGreater(alice.id, 0)
            alice.password_hash = "changed"
            db.add(User(username="alice", password_hash="duplicate"))
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()
            self.assertEqual(db.scalar(select(User)).password_hash, "hash")
