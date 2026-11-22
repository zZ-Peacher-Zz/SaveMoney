from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SavingsGoal(Base):
    __tablename__ = "monthly_savings_goals"
    scope: Mapped[str] = mapped_column(String(40), primary_key=True)
    month: Mapped[str] = mapped_column(String(7), primary_key=True)
    amount: Mapped[float] = mapped_column(Float)


class AnnualSavingsGoal(Base):
    __tablename__ = "annual_savings_goals"
    scope: Mapped[str] = mapped_column(String(40), primary_key=True)
    year: Mapped[str] = mapped_column(String(4), primary_key=True)
    amount: Mapped[float] = mapped_column(Float)
