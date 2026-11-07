from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MonthlyIncome(Base):
    __tablename__ = "user_monthly_incomes"
    __table_args__ = (UniqueConstraint("user_id", "month"),)
    user_id: Mapped[int] = mapped_column(Integer, index=True)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    amount: Mapped[float] = mapped_column(Float, default=0)


class Expense(Base):
    __tablename__ = "user_expenses"
    user_id: Mapped[int] = mapped_column(Integer, index=True)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    expense_date: Mapped[date] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    amount: Mapped[float] = mapped_column(Float)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
