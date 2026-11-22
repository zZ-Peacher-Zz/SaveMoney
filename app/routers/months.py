import csv
import re
from datetime import date
from io import StringIO

from fastapi.responses import StreamingResponse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import Ledger, current_ledger
from app.helpers import month_bounds, validate_month
from app.models.user import User
from app.models.savings import SavingsGoal, AnnualSavingsGoal
from app.schemas.finance import IncomePayload

router = APIRouter()


def savings_scope(ledger):
    return f"group:{ledger.group.id}" if ledger.group else f"user:{ledger.user.id}"


def validate_year(year):
    if not re.fullmatch(r"[0-9]{4}", year) or not 1 <= int(year) <= 9998:
        raise HTTPException(400, "Invalid year")


@router.get("/api/years/{year}/savings-summary")
def year_savings_summary(year: str, db: Session = Depends(get_db), ledger: Ledger = Depends(current_ledger)):
    validate_year(year)
    Income, Expense = ledger.income, ledger.expense
    income = db.scalar(select(func.coalesce(func.sum(Income.amount), 0)).where(
        ledger.filter(Income), Income.month >= f"{year}-01", Income.month <= f"{year}-12"))
    expense = db.scalar(select(func.coalesce(func.sum(Expense.amount), 0)).where(
        ledger.filter(Expense), Expense.expense_date >= date(int(year), 1, 1), Expense.expense_date < date(int(year) + 1, 1, 1)))
    goal = db.get(AnnualSavingsGoal, (savings_scope(ledger), year))
    return {"year": year, "income": income, "total_expense": expense,
            "remaining": round(income - expense, 2), "savings_goal": goal.amount if goal else 0,
            "can_edit_savings_goal": not ledger.group or ledger.group.owner_id == ledger.user.id}


@router.put("/api/years/{year}/savings-goal")
def set_year_savings_goal(year: str, payload: IncomePayload, db: Session = Depends(get_db), ledger: Ledger = Depends(current_ledger)):
    validate_year(year)
    if ledger.group and ledger.group.owner_id != ledger.user.id:
        raise HTTPException(403, "Chỉ chủ nhóm được thay đổi mục tiêu tiết kiệm chung.")
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    statement = insert(AnnualSavingsGoal).values(scope=savings_scope(ledger), year=year, amount=payload.amount)
    db.execute(statement.on_conflict_do_update(index_elements=["scope", "year"], set_={"amount": payload.amount}))
    db.commit()
    return {"year": year, "amount": payload.amount}


@router.put("/api/months/{month}/savings-goal")
def set_savings_goal(month: str, payload: IncomePayload, db: Session = Depends(get_db), ledger: Ledger = Depends(current_ledger)):
    validate_month(month)
    if ledger.group and ledger.group.owner_id != ledger.user.id:
        raise HTTPException(403, "Chỉ chủ nhóm được thay đổi mục tiêu tiết kiệm chung.")
    values = {"scope": savings_scope(ledger), "month": month, "amount": payload.amount}
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    statement = insert(SavingsGoal).values(**values)
    db.execute(statement.on_conflict_do_update(index_elements=["scope", "month"], set_={"amount": payload.amount}))
    db.commit()
    return {"month": month, "amount": payload.amount}


@router.get("/api/months/{month}/summary")
def get_summary(month: str, db: Session = Depends(get_db), ledger: Ledger = Depends(current_ledger)):
    MonthlyIncome, Expense = ledger.income, ledger.expense
    start, end = month_bounds(month)

    income_rows = db.scalars(
        select(MonthlyIncome).where(MonthlyIncome.month == month, ledger.filter(MonthlyIncome))
    ).all()
    income = sum(row.amount for row in income_rows)
    my_income = sum(row.amount for row in income_rows if row.user_id == ledger.user.id)

    expenses = db.scalars(
        select(Expense)
        .where(ledger.filter(Expense), Expense.expense_date >= start, Expense.expense_date < end)
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
    ).all()

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
        "savings_goal": (goal.amount if (goal := db.get(SavingsGoal, (savings_scope(ledger), month))) else 0),
        "can_edit_savings_goal": not ledger.group or ledger.group.owner_id == ledger.user.id,
    }


@router.put("/api/months/{month}/income")
def set_income(month: str, payload: IncomePayload, db: Session = Depends(get_db), ledger: Ledger = Depends(current_ledger)):
    MonthlyIncome, Expense = ledger.income, ledger.expense
    validate_month(month)

    row = db.scalar(
        select(MonthlyIncome).where(MonthlyIncome.month == month, ledger.filter(MonthlyIncome), MonthlyIncome.user_id == ledger.user.id)
    )
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

    db.execute(
        delete(Expense).where(
            ledger.filter(Expense),
            Expense.expense_date >= start,
            Expense.expense_date < end,
        )
    )
    db.execute(
        delete(MonthlyIncome).where(MonthlyIncome.month == month, ledger.filter(MonthlyIncome))
    )
    db.execute(delete(SavingsGoal).where(SavingsGoal.scope == savings_scope(ledger), SavingsGoal.month == month))
    db.commit()


@router.get("/api/months/{month}/export.csv")
def export_csv(month: str, db: Session = Depends(get_db), ledger: Ledger = Depends(current_ledger)):
    MonthlyIncome, Expense = ledger.income, ledger.expense
    start, end = month_bounds(month)

    items = db.scalars(
        select(Expense)
        .where(ledger.filter(Expense), Expense.expense_date >= start, Expense.expense_date < end)
        .order_by(Expense.expense_date.asc(), Expense.id.asc())
    ).all()

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
