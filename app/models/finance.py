from dataclasses import dataclass
from datetime import date
from typing import ClassVar, Optional

from app.models.document import Document


@dataclass(kw_only=True)
class MonthlyIncome(Document):
    collection: ClassVar[str] = 'user_monthly_incomes'
    key_fields: ClassVar[tuple] = ('id',)
    unique_fields: ClassVar[tuple] = (('user_id', 'month'),)
    user_id: int
    id: int = None
    month: str
    amount: float = 0


@dataclass(kw_only=True)
class Expense(Document):
    collection: ClassVar[str] = 'user_expenses'
    key_fields: ClassVar[tuple] = ('id',)
    unique_fields: ClassVar[tuple] = ()
    user_id: int
    id: int = None
    expense_date: date
    category: str
    amount: float
    note: Optional[str] = None
