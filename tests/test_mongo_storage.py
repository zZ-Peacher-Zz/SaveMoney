import sqlite3
import tempfile
import unittest
from pathlib import Path

from pymongo.errors import DuplicateKeyError

from app.models.user import User
from app.models.finance import Expense
from mongo_support import MemorySession, memory_database
from scripts.migrate_sqlite_to_mongo import read_sqlite, copy_records


class MongoStorageTests(unittest.TestCase):
    def test_rollback_and_unique_keys(self):
        database = memory_database()
        with MemorySession(database) as db:
            db.add(User(username="alice", password_hash="hash"))
            db.commit()
        with self.assertRaises(DuplicateKeyError):
            with MemorySession(database) as db:
                db.delete_many(User, {"username": "alice"})
                db.add(User(username="bob", password_hash="hash"))
                db.add(User(username="bob", password_hash="hash"))
                db.commit()
        self.assertEqual(database.users.count_documents({"username": "alice"}), 1)
        self.assertEqual(database.users.count_documents({"username": "bob"}), 0)

    def test_migration_preserves_source_and_ids(self):
        database = memory_database()
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "old.db"
            with sqlite3.connect(source) as connection:
                connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password_hash TEXT)")
                connection.execute("INSERT INTO users VALUES (42, 'alice', 'existing-hash')")
                connection.execute("CREATE TABLE user_expenses (id INTEGER PRIMARY KEY, user_id INTEGER, expense_date TEXT, category TEXT, amount REAL, note TEXT)")
                connection.execute("INSERT INTO user_expenses VALUES (19, 42, '2026-11-07', 'Food', 100, 'Lunch')")
            connection.close()
            before = source.read_bytes()
            records = read_sqlite(source)
            self.assertEqual(source.read_bytes(), before)
            copy_records(database, records, MemorySession)
            with MemorySession(database) as db:
                self.assertEqual(db.get(User, 42).username, "alice")
                self.assertEqual(db.get(Expense, 19).expense_date.isoformat(), "2026-11-07")
                user = User(username="bob", password_hash="hash")
                db.add(user)
                db.commit()
                self.assertEqual(user.id, 43)
            self.assertEqual(source.read_bytes(), before)
            with self.assertRaises(ValueError):
                copy_records(database, records, MemorySession)
