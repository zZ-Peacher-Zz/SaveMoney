# SaveMoney - FastAPI + MongoDB Atlas

A personal and family expense tracker with account login, avatars, monthly income,
shared ledgers, group invitations, CSV export, and verified email password recovery.

## Install

Python 3.12 is selected by `.python-version`.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Configure MongoDB Atlas

Copy [.env.example](.env.example) to `.env`. The app loads it automatically; existing
process/Render environment variables take precedence. Never commit passwords or keys.

```env
MONGODB_URI=mongodb+srv://moneyManage:<db_password>@cluster0.w96azfz.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=SaveMoney
APP_BASE_URL=http://127.0.0.1:8000
COOKIE_SECURE=0
```

Replace `<db_password>` with the Atlas database user's password, not the Atlas website
login password. Percent-encode special characters in the username/password. Keep
credentials in `.env` or Render Environment, never in source code or GitHub.

In Atlas:

1. In Database Access, give the database user read/write access to `SaveMoney`.
2. In Network Access, allow your local public IP and the Render service's outbound IP
   ranges. See Render Settings for its outbound addresses.
3. Ensure the cluster is active and the driver connection string is correct.

A MongoDB replica set is required because writes use transactions. Atlas supports
this topology; a standalone local mongod is not sufficient. Collections and unique
indexes are initialized during app startup. The app fails explicitly if the URI is
missing or still contains the password placeholder; it does not fall back to SQLite.

## Run

```bash
uvicorn main:app --reload
```

Open http://127.0.0.1:8000. Signed-out visitors are redirected to `/login`.
Separate account pages: `/register`, `/forgot-password`, `/reset-password`, `/verify-email`.
API documentation is at `/docs`.

## Render

Create a Python Web Service connected to this repository:

- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health check: `/api/health`

Set `MONGODB_URI`, `MONGODB_DB`, `APP_BASE_URL=https://your-app.onrender.com`, and
`COOKIE_SECURE=1` in Environment. Remove an old `PYTHON_VERSION=3.14...` override;
the repository selects Python 3.12. `DATABASE_URL` is no longer used.

Accounts, income, expenses, avatars, memberships, and recovery data live in Atlas,
so the app does not need a Render persistent disk for these records. MongoDB starts
empty unless you deliberately migrate existing data.

## Existing SQLite data

The original SQLite file is retained unchanged. A migration tool copies persistent
user/group records and keeps their integer IDs. It does not copy sessions, recovery
tokens, or rate counters; users log in again and request fresh recovery links.
Legacy shared tables from before user accounts are not assigned to an arbitrary user.

Stop the app and back up SQLite before migration. Use a new, empty destination database:

```bash
# Read-only preview: no connection to Atlas and no database writes
python scripts/migrate_sqlite_to_mongo.py
# After verifying the configured destination:
python scripts/migrate_sqlite_to_mongo.py --apply
```

The tool refuses a non-empty destination and commits the copy and ID counters in one
transaction. It never deletes or modifies the source SQLite file.

## Email recovery

Set `RESEND_API_KEY` and `EMAIL_FROM` for HTTPS mail delivery, and set `APP_BASE_URL`
to the exact public app address. Render Free blocks common SMTP ports; use Resend
there. On other hosts, SMTP is also supported with `SMTP_HOST`, `SMTP_PORT` (587
STARTTLS or 465 TLS), `SMTP_USER`, and `SMTP_PASSWORD`.

New UI accounts provide a recovery email. Existing users add one after login using
**Email khoi phuc tai khoan** and their current password. Recovery requires verifying
the address first. An email can belong to only one verified account.

Links expire after 30 minutes, are stored only as hashes, and can be consumed once.
Password reset revokes login sessions and outstanding recovery links atomically.
Old email links are redirected to the dedicated recovery page. No link is printed to
logs or returned as a fallback when mail delivery is not configured.

`onboarding@resend.dev` is for testing to the email on your Resend account. Verify a
domain and use its sender address before sending to other family members.

## Family ledgers

Create a group, invite an existing username, and have the recipient accept the
invitation. Invitations are checked automatically every three seconds while the tab
is visible. Select a group or the personal ledger before saving income/expenses.
Personal records remain private. Each member sets their own income contribution;
the summary adds all contributions and shared expenses for the chosen month.

Members edit their own expenses. The owner can manage all group expenses, invite
and remove members, and clear a group month. Historical shared records remain after
member removal, while that user's access is revoked. Avatars are visible only to
members sharing the selected group. Savings goals are not implemented yet.

## Code structure

- [main.py](main.py): app startup, static files, router registration.
- [app/database.py](app/database.py): shared PyMongo client, indexes, transactions,
  and request-scoped document tracking.
- [app/models/](app/models/): dataclass document definitions and unique keys.
- [app/routers/](app/routers/): account, recovery, family, finance, and page endpoints.
- [app/schemas/](app/schemas/): request validation with Pydantic.
- [app/security.py](app/security.py): scrypt password hashes and HttpOnly session cookies.
- [app/dependencies.py](app/dependencies.py): group permissions and ledger selection.
- [templates/](templates/), [static/](static/): frontend.

The public API preserves its existing integer IDs and JSON fields. MongoDB stores
expense dates as ISO `YYYY-MM-DD` strings, and avatars as PNG binary data.

## Tests

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Unit tests use an isolated in-memory Mongo implementation with simulated rollback.
They do not prove real server transaction isolation. To run the opt-in transaction
integration tests, set `MONGODB_TEST_URI` to a replica-set test cluster; the tests use
and clean up a randomly named database, never the configured production database.
