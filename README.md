# Monthly Expense Tracker — FastAPI + SQLite

## Code structure

```text
main.py                 # Create the FastAPI app, mount static files, include routers
app/
  database.py           # Engine, ORM Base, table initialization, get_db dependency
  security.py           # Password hashes, sessions, current_user dependency
  dependencies.py       # Group authorization and personal/family ledger selection
  helpers.py            # Month validation and expense serialization
  models/
    user.py             # User and login session tables
    finance.py          # Personal income and expense tables
    group.py            # Family groups, membership, invitations, shared records
  schemas/
    auth.py             # Login and registration request validation
    finance.py          # Income and expense request validation
    groups.py           # Group and invitation request validation
  routers/
    auth.py             # Registration, login, logout, current account
    groups.py           # Groups, members, invitations
    months.py           # Monthly summary, income, clearing, CSV export
    expenses.py         # List, create, update, delete expenses
    pages.py            # Homepage and health check
templates/              # HTML templates
static/                 # CSS and JavaScript
tests/                  # Account and family authorization regression tests
```

Start the app with `uvicorn main:app --reload` as before. Routers use `get_db`
from `app.database`; tests override that dependency with an isolated database.
The refactor keeps existing API paths, request schemas, and database table names.

Ứng dụng quản lý chi tiêu hằng tháng gồm:

- Backend Python bằng FastAPI
- SQLite database
- SQLAlchemy ORM
- REST API
- Frontend HTML/CSS/JavaScript
- CRUD khoản chi
- Thu nhập theo từng tháng
- Tổng chi, còn lại, tỷ lệ tiết kiệm
- Tổng hợp chi tiêu theo danh mục
- Export CSV
- Responsive desktop/mobile

## 1. Yêu cầu

- Python 3.10+
- pip

## 2. Cài đặt

Mở terminal tại thư mục project:

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### macOS / Linux

```bash
source .venv/bin/activate
```

Cài thư viện:

```bash
pip install -r requirements.txt
```

## 3. Chạy app

```bash
uvicorn main:app --reload
```

Mở:

```text
http://127.0.0.1:8000
```

FastAPI docs:

```text
http://127.0.0.1:8000/docs
```

## 4. Database

App tự tạo file:

```text
expense_tracker.db
```

Database có 2 bảng:

### monthly_incomes

- id
- month
- amount

### expenses

- id
- expense_date
- category
- amount
- note

## 5. API chính

```text
GET    /api/months/{month}/summary
PUT    /api/months/{month}/income
GET    /api/months/{month}/expenses

POST   /api/expenses
PUT    /api/expenses/{expense_id}
DELETE /api/expenses/{expense_id}

DELETE /api/months/{month}
GET    /api/months/{month}/export.csv
```

`month` có format:

```text
YYYY-MM
```

Ví dụ:

```text
2026-11
```

## 6. Luồng dữ liệu

```text
Browser
  ↓ fetch()
FastAPI REST API
  ↓
SQLAlchemy
  ↓
SQLite
```

Frontend không lưu dữ liệu bằng localStorage nữa. Khi refresh trang, dữ liệu được đọc lại từ database.

## 7. Hướng phát triển tiếp

Có thể nâng cấp project thành app dùng nhiều người bằng cách thêm:

- User authentication
- PostgreSQL
- Household / shared wallet
- Người chi: An / Phong
- Thu nhập của từng người
- Budget theo category
- Recurring expense
- Dashboard theo tháng / quý / năm
- Docker
- Alembic migration
- Test bằng pytest
- Deploy Render / Railway / Fly.io


## User accounts

Each account can upload or remove its avatar using the photo next to the username
or **Đổi ảnh đại diện**. Supported formats are PNG, JPEG, and WebP, up to 5 MB
and 16 megapixels.
Before saving, a dialog previews the avatar in a circular frame. Drag the photo
or use arrow keys to position it, and use the zoom slider to adjust the crop.
**Hủy** or Escape closes the dialog without changing the saved avatar.
The selected crop is saved as a 256×256 PNG in the
`user_avatars` table. Existing accounts show their initial until they choose a photo.
Install the updated requirements and restart the server after this update.

Authenticated avatar endpoints: `PUT /api/auth/avatar` (raw image body),
`GET /api/auth/avatar`, and `DELETE /api/auth/avatar`.

Create an account using **T?o t?i kho?n**, or sign in using **??ng nh?p**.
Usernames are case-insensitive, 3?50 characters (letters, numbers, `_`, `.`, `-`).
Passwords must be 8?128 characters. Use **??ng xu?t** to sign out.

Each user has their own monthly income, expenses, summary, and CSV exports.
Passwords are stored as salted scrypt hashes. Login sessions expire after seven days
and use an HttpOnly, SameSite=Strict cookie. Set `COOKIE_SECURE=1` when serving over HTTPS.

New tables: `users`, `login_sessions`, `user_monthly_incomes`, and `user_expenses`.
Existing shared `monthly_incomes` and `expenses` tables remain untouched; their
records are not automatically assigned to any account. New accounts start empty.
The optional `DATABASE_URL` environment variable overrides the SQLite database URL.

Run the account and record isolation tests:

```bash
pip install httpx
python -m unittest discover -s tests
```

## Family groups

In **Quản lý gia đình**, create a group, select it in **Sổ thu chi**, and invite an
existing account by username. The invited user signs in, clicks **Làm mới nhóm và
lời mời**, and accepts or declines the invitation. Only accepted members can view
the group's records. A user can belong to multiple groups.

The selected ledger determines where income and expenses are saved. Personal
records remain private. In a family ledger, each user sets their own monthly
income contribution; the dashboard sums all contributions and shared expenses.
These contributions are recorded separately from personal income, so only enter
the amount intended for the shared budget. Remaining balance is income minus
expenses for the selected month, rather than a separate savings account.

Expenses show their author. Members can edit/delete their own expenses; the owner
can edit/delete any group expense, remove members, invite users, and clear a group
month. Removing a member immediately revokes access but retains their historical
income and expenses in the family ledger. The owner cannot remove themselves.

Family features use new tables and leave existing personal data unchanged.
Savings goals are reserved for a later version.

Group API:

```text
GET    /api/groups
POST   /api/groups                         {"name": "Family"}
GET    /api/groups/{group_id}/members
POST   /api/groups/{group_id}/invitations   {"username": "existing_user"}
DELETE /api/groups/{group_id}/members/{member_id}
GET    /api/invitations
POST   /api/invitations/{group_id}/accept
DELETE /api/invitations/{group_id}
```

Append `?group_id={group_id}` to the existing income, expense, summary, clear-month,
and CSV endpoints to operate on a family ledger. Omitting it selects personal data.
All group requests check current membership; owner-only actions also check ownership.
