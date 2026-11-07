"""Opt-in PostgreSQL tests in a temporary schema, never production tables."""
import os
import unittest
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, create_db_engine
from app.models.user import User, LoginSession
from app.models.recovery import RecoveryToken
from app.recovery import consume_token
import hashlib
import time


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

    def test_recovery_consumption_and_revocation_commit_together(self):
        token = "postgres-integration-token"
        with Session(self.bind) as db:
            user = User(username="alice", password_hash="old-hash")
            db.add(user)
            db.flush()
            db.add(LoginSession(token_hash="session-hash", user_id=user.id, expires_at=int(time.time()) + 60))
            db.add(RecoveryToken(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id,
                                 email="alice@example.com", purpose="reset", expires_at=int(time.time()) + 60))
            db.commit()
            used = consume_token(db, token, "reset")
            db.get(User, used.user_id).password_hash = "new-hash"
            from sqlalchemy import delete
            db.execute(delete(LoginSession).where(LoginSession.user_id == used.user_id))
            db.commit()
            with self.assertRaises(HTTPException):
                consume_token(db, token, "reset")
            self.assertIsNone(db.scalar(select(LoginSession)))
            self.assertEqual(db.scalar(select(User)).password_hash, "new-hash")
