from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FamilyGroup(Base):
    __tablename__ = "family_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    owner_id: Mapped[int] = mapped_column(Integer)


class GroupMember(Base):
    __tablename__ = "group_members"
    group_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)


class GroupInvitation(Base):
    __tablename__ = "group_invitations"
    group_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)


class GroupIncome(Base):
    __tablename__ = "group_incomes"
    __table_args__ = (UniqueConstraint("group_id", "user_id", "month"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int] = mapped_column(Integer)
    month: Mapped[str] = mapped_column(String(7))
    amount: Mapped[float] = mapped_column(Float)


class GroupExpense(Base):
    __tablename__ = "group_expenses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int] = mapped_column(Integer)
    expense_date: Mapped[date] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(String(50))
    amount: Mapped[float] = mapped_column(Float)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
