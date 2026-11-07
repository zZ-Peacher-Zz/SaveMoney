"""Authorization and selection of a personal or family ledger."""
from typing import Optional

from fastapi import Depends, HTTPException
from app.database import MongoSession as Session

from app.database import get_db
from app.models.finance import Expense, MonthlyIncome
from app.models.group import FamilyGroup, GroupExpense, GroupIncome, GroupMember
from app.models.user import User
from app.security import current_user


def require_group(db, group_id, user, owner=False):
    group = db.get(FamilyGroup, group_id)
    if group is None or db.get(GroupMember, (group_id, user.id)) is None:
        raise HTTPException(404, "Group not found")
    if owner and group.owner_id != user.id:
        raise HTTPException(403, "Only the group owner can do this")
    return group


class Ledger:
    def __init__(self, user, group=None):
        self.user = user
        self.group = group
        self.income = GroupIncome if group else MonthlyIncome
        self.expense = GroupExpense if group else Expense
        self.values = {"user_id": user.id}
        if group:
            self.values["group_id"] = group.id

    def filter(self, model):
        return {"group_id": self.group.id} if self.group else {"user_id": self.user.id}

    def can_edit(self, item):
        return item.user_id == self.user.id or (self.group and self.group.owner_id == self.user.id)


def current_ledger(group_id: Optional[int] = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    group = require_group(db, group_id, user) if group_id is not None else None
    return Ledger(user, group)
