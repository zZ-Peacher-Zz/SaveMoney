"""Copy persistent SQLite records into an EMPTY MongoDB database.

Default is a read-only preview. --apply commits all records in one transaction.
Run with the app stopped. Existing sessions and recovery tokens are not copied.
"""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3
import sys

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))
from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / ".env")

from app.database import MongoSession, get_database, init_db, model_types

TEMPORARY = {"login_sessions", "recovery_tokens", "recovery_limits"}


def read_sqlite(source):
    source = Path(source).resolve()
    records = []
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for model in model_types():
            if model.collection in TEMPORARY or model.collection not in tables:
                continue
            # Names are fixed model collection identifiers, never CLI/user input.
            for row in connection.execute(f'SELECT * FROM "{model.collection}"'):
                records.append(model.from_document(dict(row)))
    return records


def copy_records(database, records, session_factory=MongoSession):
    for model in model_types():
        if database[model.collection].count_documents({}):
            raise ValueError("Destination must be empty; choose a new MONGODB_DB. No records copied.")
    with session_factory(database) as db:
        # Guard a second migration racing this one. An app must not be running yet.
        db.database.counters.insert_one({"_id": "migration_guard"}, **db._options())
        maxima = {}
        for item in records:
            db.add(item)
            if item.key_fields == ("id",):
                maxima[item.collection] = max(maxima.get(item.collection, 0), item.id)
        for collection, value in maxima.items():
            database.counters.update_one({"_id": collection}, {"$max": {"value": value}},
                                         upsert=True, **db._options())
        db.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(PROJECT_DIR / "expense_tracker.db"))
    parser.add_argument("--apply", action="store_true", help="Write to the configured EMPTY MongoDB database")
    args = parser.parse_args()
    records = read_sqlite(args.source)
    counts = {}
    for item in records:
        counts[item.collection] = counts.get(item.collection, 0) + 1
    for collection, count in sorted(counts.items()):
        print(f"{collection}: {count}")
    if not args.apply:
        print("Preview only. SQLite is unchanged. Use --apply after reviewing the destination settings.")
        return
    init_db()
    copy_records(get_database(), records)
    print("Migration committed. SQLite is unchanged. Log in again on the MongoDB app.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Avoid accidentally printing a URI or credentials from a driver exception.
        sys.exit("Migration failed. Check the source, Atlas settings, and that the destination is empty. SQLite is unchanged.")
