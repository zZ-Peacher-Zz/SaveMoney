"""Month validation and serialization shared by finance routes."""
from datetime import date
import re

from fastapi import HTTPException

from app.models.finance import Expense
from app.models.user import User

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def validate_month(month: str) -> str:
    if not MONTH_RE.match(month):
        raise HTTPException(status_code=400, detail="month must be YYYY-MM")
    return month


def month_bounds(month: str):
    validate_month(month)
    year, mon = map(int, month.split("-"))
    start = date(year, mon, 1)
    if mon == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, mon + 1, 1)
    return start, end


def serialize_expense(item: Expense):
    return {
        "id": item.id,
        "expense_date": item.expense_date.isoformat(),
        "category": item.category,
        "amount": round(item.amount, 2),
        "note": item.note,
    }


def serialize_ledger_expense(item, ledger, db):
    data = serialize_expense(item)
    author = db.get(User, item.user_id)
    data.update(username=author.username if author else "", can_edit=bool(ledger.can_edit(item)))
    return data
