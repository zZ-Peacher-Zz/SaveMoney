from fastapi import APIRouter, Depends, HTTPException
from app.database import MongoSession as Session

from app.database import get_db
from app.dependencies import Ledger, current_ledger
from app.helpers import month_bounds, serialize_ledger_expense
from app.schemas.finance import ExpensePayload

router = APIRouter()


@router.get("/api/months/{month}/expenses")
def list_expenses(month: str, db: Session = Depends(get_db), ledger: Ledger = Depends(current_ledger)):
    Expense = ledger.expense
    start, end = month_bounds(month)

    items = db.find(Expense, {**ledger.filter(Expense), "expense_date": {"$gte": start.isoformat(), "$lt": end.isoformat()}},
                    sort=[("expense_date", -1), ("id", -1)])

    return [serialize_ledger_expense(item, ledger, db) for item in items]


@router.post("/api/expenses", status_code=201)
def create_expense(payload: ExpensePayload, db: Session = Depends(get_db), ledger: Ledger = Depends(current_ledger)):
    Expense = ledger.expense
    item = Expense(
        **ledger.values,
        expense_date=payload.expense_date,
        category=payload.category,
        amount=payload.amount,
        note=payload.note,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return serialize_ledger_expense(item, ledger, db)


@router.put("/api/expenses/{expense_id}")
def update_expense(
    expense_id: int,
    payload: ExpensePayload,
    db: Session = Depends(get_db),
    ledger: Ledger = Depends(current_ledger),
):
    Expense = ledger.expense
    item = db.one(Expense, {"id": expense_id, **ledger.filter(Expense)})
    if not item:
        raise HTTPException(status_code=404, detail="Expense not found")
    if not ledger.can_edit(item):
        raise HTTPException(status_code=403, detail="Only the author or group owner can change this expense")

    item.expense_date = payload.expense_date
    item.category = payload.category
    item.amount = payload.amount
    item.note = payload.note

    db.commit()
    db.refresh(item)
    return serialize_ledger_expense(item, ledger, db)


@router.delete("/api/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int, db: Session = Depends(get_db), ledger: Ledger = Depends(current_ledger)):
    Expense = ledger.expense
    item = db.one(Expense, {"id": expense_id, **ledger.filter(Expense)})
    if not item:
        raise HTTPException(status_code=404, detail="Expense not found")
    if not ledger.can_edit(item):
        raise HTTPException(status_code=403, detail="Only the author or group owner can change this expense")

    db.delete(item)
    db.commit()
