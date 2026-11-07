import csv
from io import StringIO

from fastapi.responses import StreamingResponse

from fastapi import APIRouter, Depends, HTTPException
from app.database import MongoSession as Session

from app.database import get_db
from app.dependencies import Ledger, current_ledger
from app.helpers import month_bounds, validate_month
from app.models.user import User
from app.schemas.finance import IncomePayload

router = APIRouter()


@router.get("/api/months/{month}/summary")
def get_summary(month: str, db: Session = Depends(get_db), ledger: Ledger = Depends(current_ledger)):
    MonthlyIncome, Expense = ledger.income, ledger.expense
    start, end = month_bounds(month)

    income_rows = db.find(MonthlyIncome, {"month": month, **ledger.filter(MonthlyIncome)})
    income = sum(row.amount for row in income_rows)
    my_income = sum(row.amount for row in income_rows if row.user_id == ledger.user.id)

    expenses = db.find(Expense, {**ledger.filter(Expense), "expense_date": {"$gte": start.isoformat(), "$lt": end.isoformat()}},
                       sort=[("expense_date", -1), ("id", -1)])

    total_expense = sum(x.amount for x in expenses)
    remaining = income - total_expense
    saving_rate = (remaining / income * 100) if income > 0 else 0

    category_totals = {}
    for item in expenses:
        category_totals[item.category] = category_totals.get(item.category, 0) + item.amount

    categories = [
        {"category": category, "amount": round(amount, 2)}
        for category, amount in sorted(
            category_totals.items(),
            key=lambda pair: pair[1],
            reverse=True,
        )
    ]

    return {
        "month": month,
        "income": round(income, 2),
        "my_income": round(my_income, 2),
        "total_expense": round(total_expense, 2),
        "remaining": round(remaining, 2),
        "saving_rate": round(saving_rate, 1),
        "expense_count": len(expenses),
        "categories": categories,
    }


@router.put("/api/months/{month}/income")
def set_income(month: str, payload: IncomePayload, db: Session = Depends(get_db), ledger: Ledger = Depends(current_ledger)):
    MonthlyIncome, Expense = ledger.income, ledger.expense
    validate_month(month)

    row = db.one(MonthlyIncome, {**ledger.filter(MonthlyIncome), "month": month, "user_id": ledger.user.id})
    if row:
        row.amount = payload.amount
    else:
        row = MonthlyIncome(**ledger.values, month=month, amount=payload.amount)
        db.add(row)

    db.commit()
    db.refresh(row)

    return {
        "month": month,
        "amount": round(row.amount, 2),
    }


@router.delete("/api/months/{month}", status_code=204)
def clear_month(month: str, db: Session = Depends(get_db), ledger: Ledger = Depends(current_ledger)):
    MonthlyIncome, Expense = ledger.income, ledger.expense
    start, end = month_bounds(month)
    if ledger.group and ledger.group.owner_id != ledger.user.id:
        raise HTTPException(403, "Only the group owner can clear the month")

    db.delete_many(Expense, {**ledger.filter(Expense), "expense_date": {"$gte": start.isoformat(), "$lt": end.isoformat()}})
    db.delete_many(MonthlyIncome, {"month": month, **ledger.filter(MonthlyIncome)})
    db.commit()


@router.get("/api/months/{month}/export.csv")
def export_csv(month: str, db: Session = Depends(get_db), ledger: Ledger = Depends(current_ledger)):
    MonthlyIncome, Expense = ledger.income, ledger.expense
    start, end = month_bounds(month)

    items = db.find(Expense, {**ledger.filter(Expense), "expense_date": {"$gte": start.isoformat(), "$lt": end.isoformat()}},
                    sort=[("expense_date", 1), ("id", 1)])

    output = StringIO()
    writer = csv.writer(output)
    columns = ["Ngày", "Phân loại", "Ghi chú", "Số tiền"]
    if ledger.group:
        columns.append("Người ghi")
    writer.writerow(columns)

    for item in items:
        row = [
            item.expense_date.isoformat(),
            item.category,
            item.note or "",
            item.amount,
        ]
        if ledger.group:
            author = db.get(User, item.user_id)
            row.append(author.username if author else "")
        writer.writerow(row)

    content = "\ufeff" + output.getvalue()
    headers = {
        "Content-Disposition": f'attachment; filename="chi-tieu-{month}.csv"'
    }

    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )
