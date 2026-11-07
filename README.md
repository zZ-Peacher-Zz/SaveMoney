# SaveMoney - FastAPI + PostgreSQL

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

## Configure PostgreSQL

Copy [.env.example](.env.example) to `.env`. The app loads it automatically;
process/Render environment variables take precedence. Never commit credentials.

```env
DATABASE_URL=postgresql://database_user:YOUR_PASSWORD@YOUR_POSTGRES_HOST/savemoneydatabase
APP_BASE_URL=http://127.0.0.1:8000
COOKIE_SECURE=0
```

Use Render's **External Database URL** when running locally. Its internal hostname
is accessible only from Render services in the same region. Use the **Internal
Database URL** for the deployed Render service. Preserve connection options from
the provider, including SSL settings; external connections can use `sslmode=require`.
Percent-encode special characters in the username/password.

SQLAlchemy uses the psycopg driver. Tables are created at startup; the database
must already exist and the database user must have schema creation permissions.
Missing or unreachable configuration fails startup without a fallback database.

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

Set `DATABASE_URL`, `APP_BASE_URL=https://your-app.onrender.com`, and
`COOKIE_SECURE=1` in Environment. Remove an old `PYTHON_VERSION=3.14...` override;
the repository selects Python 3.12. Set the email configuration below as well.

Accounts, income, expenses, avatars, memberships, and recovery data are stored in
PostgreSQL, so these records do not require a Render persistent disk.

## Existing data

Changing the database connection does not migrate existing records. The previous
Atlas database and local SQLite files are left untouched. A new PostgreSQL database
starts empty; arrange a separate data migration if old records must be retained.

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
- [app/database.py](app/database.py): PostgreSQL engine and request-scoped SQLAlchemy sessions.
- [app/models/](app/models/): SQLAlchemy tables, relationships, and unique constraints.
- [app/routers/](app/routers/): account, recovery, family, finance, and page endpoints.
- [app/schemas/](app/schemas/): request validation with Pydantic.
- [app/security.py](app/security.py): scrypt password hashes and HttpOnly session cookies.
- [app/dependencies.py](app/dependencies.py): group permissions and ledger selection.
- [templates/](templates/), [static/](static/): frontend.

The public API preserves its existing integer IDs and JSON fields. PostgreSQL stores
expense dates as DATE values and avatars as binary data.

## Tests

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Functional tests use isolated SQLite databases. PostgreSQL configuration and DDL
compilation are also checked. For real PostgreSQL transaction tests, set
`POSTGRES_TEST_URL` to a test database URL. These opt-in tests create and remove a
random temporary schema and require schema creation permissions. They do not
modify application tables. Without that variable, the two integration tests skip.
