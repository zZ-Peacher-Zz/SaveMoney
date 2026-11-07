"""MongoDB connection and request-scoped document unit of work.

Production requests use Atlas transactions. Integer counters preserve existing API
IDs; aborted writes can leave harmless gaps in those counters.
"""
import os
from functools import lru_cache

from fastapi import HTTPException
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern


@lru_cache(maxsize=1)
def get_client():
    uri = os.getenv("MONGODB_URI", "")
    if not uri or "<db_password>" in uri or not uri.startswith(("mongodb://", "mongodb+srv://")):
        raise RuntimeError("Set MONGODB_URI with the real Atlas password in .env or Render Environment")
    return MongoClient(uri, serverSelectionTimeoutMS=10000, connectTimeoutMS=10000, appname="SaveMoney")


def get_database():
    return get_client()[os.getenv("MONGODB_DB", "savemoney")]


def model_types():
    from app import models
    return [getattr(models, name) for name in models.__all__]


def create_indexes(database):
    database.counters.create_index("value")
    for model in model_types():
        collection = database[model.collection]
        collection.create_index([(key, 1) for key in model.key_fields], unique=True)
        for keys in model.unique_fields:
            collection.create_index([(key, 1) for key in keys], unique=True)
    for collection, owner in (("user_expenses", "user_id"), ("group_expenses", "group_id")):
        database[collection].create_index([(owner, 1), ("expense_date", -1), ("id", -1)])
    database.group_members.create_index("user_id")
    database.group_invitations.create_index("user_id")
    database.group_incomes.create_index([("group_id", 1), ("month", 1)])
    database.login_sessions.create_index("user_id")
    database.recovery_tokens.create_index("user_id")


def init_db():
    try:
        database = get_database()
        database.client.admin.command("ping")
        topology = database.client.admin.command("hello")
        if not topology.get("setName") and topology.get("msg") != "isdbgrid":
            raise RuntimeError("MongoDB must be a replica set or Atlas cluster to support transactions")
        create_indexes(database)
    except PyMongoError:
        raise RuntimeError("MongoDB connection failed. Check Atlas credentials, Network Access and cluster status.") from None


class MongoSession:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session if session is not None else database.client.start_session()
        self.tracked = {}
        self.original = {}
        self.pending = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _options(self):
        if not self.session.in_transaction:
            self.session.start_transaction(read_concern=ReadConcern("snapshot"), write_concern=WriteConcern("majority"))
        return {"session": self.session}

    def _track(self, model, value):
        if value is None:
            return None
        item = model.from_document(value)
        key = (model, tuple(item.identity_filter().values()))
        if key not in self.tracked:
            self.tracked[key] = item
            self.original[key] = item.to_document()
        return self.tracked[key]

    def get(self, model, key):
        values = key if isinstance(key, tuple) else (key,)
        return self.one(model, dict(zip(model.key_fields, values)))

    def one(self, model, filters=None):
        value = self.database[model.collection].find_one(filters or {}, **self._options())
        return self._track(model, value)

    def find(self, model, filters=None, sort=None):
        cursor = self.database[model.collection].find(filters or {}, **self._options())
        if sort:
            cursor = cursor.sort(sort)
        return [self._track(model, value) for value in cursor]

    def values(self, model, field, filters=None):
        cursor = self.database[model.collection].find(filters or {}, {field: 1}, **self._options())
        return [value[field] for value in cursor]

    def add(self, item):
        if item.key_fields == ("id",) and item.id is None:
            counter = self.database.counters.find_one_and_update(
                {"_id": item.collection}, {"$inc": {"value": 1}}, upsert=True, return_document=ReturnDocument.AFTER)
            item.id = counter["value"]
        self.pending.append(item)

    def flush(self):
        # IDs are assigned in add(); writes remain buffered until commit().
        pass

    def delete_many(self, model, filters):
        self.flush_changes()
        result = self.database[model.collection].delete_many(filters, **self._options())
        # Discard matching loaded records so later commits never resurrect them.
        for key in list(self.tracked):
            if key[0] is model:
                del self.tracked[key]
                del self.original[key]
        return result.deleted_count

    def delete(self, item):
        return self.delete_many(type(item), item.identity_filter())

    def flush_changes(self):
        for item in self.pending:
            self.database[item.collection].insert_one(item.to_document(), **self._options())
            key = (type(item), tuple(item.identity_filter().values()))
            self.tracked[key] = item
            self.original[key] = item.to_document()
        self.pending.clear()
        for key, item in self.tracked.items():
            value = item.to_document()
            if value != self.original[key]:
                changes = {field: content for field, content in value.items() if content != self.original[key].get(field)}
                self.database[item.collection].update_one(item.identity_filter(), {"$set": changes}, **self._options())
                self.original[key] = value

    def commit(self):
        try:
            self.flush_changes()
            if self.session.in_transaction:
                for attempt in range(3):
                    try:
                        self.session.commit_transaction()
                        break
                    except PyMongoError as error:
                        if not error.has_error_label("UnknownTransactionCommitResult") or attempt == 2:
                            raise
        except Exception:
            self.rollback()
            raise
        self.tracked.clear()
        self.original.clear()

    def refresh(self, item):
        # The model already contains the committed values and assigned ID.
        pass

    def rollback(self):
        if self.session.in_transaction:
            self.session.abort_transaction()
        self.pending.clear()
        self.tracked.clear()
        self.original.clear()

    def close(self):
        self.rollback()
        self.session.end_session()


def get_db():
    with MongoSession(get_database()) as db:
        try:
            yield db
        except DuplicateKeyError:
            raise HTTPException(409, "This record already exists. Please refresh and try again.")
        except PyMongoError:
            raise HTTPException(503, "Database temporarily unavailable. Please try again.")
