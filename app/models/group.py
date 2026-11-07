from dataclasses import dataclass
from datetime import date
from typing import ClassVar, Optional

from app.models.document import Document


@dataclass(kw_only=True)
class FamilyGroup(Document):
    collection: ClassVar[str] = 'family_groups'
    key_fields: ClassVar[tuple] = ('id',)
    unique_fields: ClassVar[tuple] = ()
    id: int = None
    name: str
    owner_id: int


@dataclass(kw_only=True)
class GroupMember(Document):
    collection: ClassVar[str] = 'group_members'
    key_fields: ClassVar[tuple] = ('group_id', 'user_id')
    unique_fields: ClassVar[tuple] = ()
    group_id: int
    user_id: int


@dataclass(kw_only=True)
class GroupInvitation(Document):
    collection: ClassVar[str] = 'group_invitations'
    key_fields: ClassVar[tuple] = ('group_id', 'user_id')
    unique_fields: ClassVar[tuple] = ()
    group_id: int
    user_id: int


@dataclass(kw_only=True)
class GroupIncome(Document):
    collection: ClassVar[str] = 'group_incomes'
    key_fields: ClassVar[tuple] = ('id',)
    unique_fields: ClassVar[tuple] = (('group_id', 'user_id', 'month'),)
    id: int = None
    group_id: int
    user_id: int
    month: str
    amount: float


@dataclass(kw_only=True)
class GroupExpense(Document):
    collection: ClassVar[str] = 'group_expenses'
    key_fields: ClassVar[tuple] = ('id',)
    unique_fields: ClassVar[tuple] = ()
    id: int = None
    group_id: int
    user_id: int
    expense_date: date
    category: str
    amount: float
    note: Optional[str] = None
