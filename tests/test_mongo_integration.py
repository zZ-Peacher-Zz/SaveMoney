"""Opt-in real replica-set checks. Never uses the app's production database."""
import os
import unittest
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from app.database import MongoSession, create_indexes
from app.models.user import User
from app.models.recovery import RecoveryToken
from app.recovery import consume_token
import hashlib
import time


@unittest.skipUnless(os.getenv("MONGODB_TEST_URI"), "MONGODB_TEST_URI not configured")
class MongoIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client = MongoClient(os.environ["MONGODB_TEST_URI"], serverSelectionTimeoutMS=10000)
        self.database = self.client["savemoney_test_" + uuid4().hex]
        create_indexes(self.database)

    def tearDown(self):
        self.client.drop_database(self.database.name)
        self.client.close()

    def test_transaction_rolls_back_all_changes(self):
        with MongoSession(self.database) as db:
            db.add(User(username="alice", password_hash="hash"))
            db.commit()
        with self.assertRaises(DuplicateKeyError):
            with MongoSession(self.database) as db:
                db.delete_many(User, {"username": "alice"})
                db.add(User(username="bob", password_hash="hash"))
                db.add(User(username="bob", password_hash="hash"))
                db.commit()
        self.assertEqual(self.database.users.count_documents({"username": "alice"}), 1)
        self.assertEqual(self.database.users.count_documents({"username": "bob"}), 0)

    def test_token_consumption_is_atomic(self):
        token = "integration-test-token"
        with MongoSession(self.database) as db:
            user = User(username="alice", password_hash="old-hash")
            db.add(user)
            db.add(RecoveryToken(token_hash=hashlib.sha256(token.encode()).hexdigest(),
                                 user_id=user.id, email="alice@example.com", purpose="reset",
                                 expires_at=int(time.time()) + 60))
            db.commit()
        with MongoSession(self.database) as db:
            used = consume_token(db, token, "reset")
            db.get(User, used.user_id).password_hash = "new-hash"
            db.commit()
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            with MongoSession(self.database) as db:
                consume_token(db, token, "reset")
        self.assertEqual(self.database.users.find_one({"username": "alice"})["password_hash"], "new-hash")
