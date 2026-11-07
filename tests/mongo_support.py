"""In-memory Mongo tests. Snapshot sessions simulate rollback, not server isolation.

Run replica-set integration tests separately to validate real MongoDB transactions.
"""
from copy import deepcopy
import mongomock

from app.database import MongoSession, create_indexes


class SnapshotSession:
    def __init__(self, database):
        self.database = database
        self.in_transaction = False
        self.snapshot = None

    def start_transaction(self, **kwargs):
        self.snapshot = {name: list(self.database[name].find())
                         for name in self.database.list_collection_names() if name != "counters"}
        self.in_transaction = True

    def commit_transaction(self):
        self.in_transaction = False
        self.snapshot = None

    def abort_transaction(self):
        for name in self.database.list_collection_names():
            if name != "counters":
                self.database[name].delete_many({})
        for name, documents in self.snapshot.items():
            if documents:
                self.database[name].insert_many(deepcopy(documents))
        self.in_transaction = False
        self.snapshot = None

    def end_session(self):
        pass


class MemorySession(MongoSession):
    def __init__(self, database):
        super().__init__(database, SnapshotSession(database))

    def _options(self):
        super()._options()
        return {}


def memory_database():
    database = mongomock.MongoClient().savemoney_test
    create_indexes(database)
    return database
