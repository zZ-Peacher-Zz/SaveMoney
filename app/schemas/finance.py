from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class IncomePayload(BaseModel):
    amount: float = Field(ge=0, allow_inf_nan=False)


class ExpensePayload(BaseModel):
    expense_date: date
    category: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0, allow_inf_nan=False)
    note: Optional[str] = Field(default=None, max_length=255)

    @field_validator("category")
    @classmethod
    def strip_category(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("category cannot be blank")
        return value

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: Optional[str]):
        if value is None:
            return None
        value = value.strip()
        return value or None
