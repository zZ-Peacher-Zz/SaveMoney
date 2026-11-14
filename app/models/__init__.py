"""Register all SQLAlchemy models against the shared database Base."""
from app.models.presence import UserPresence
from app.models.chat import GroupMessage
from app.models.user import LoginSession, User, UserAvatar
from app.models.finance import Expense, MonthlyIncome
from app.models.group import FamilyGroup, GroupExpense, GroupIncome, GroupInvitation, GroupMember

__all__ = [
    "UserPresence", "GroupMessage", "User", "UserAvatar", "LoginSession", "Expense", "MonthlyIncome", "FamilyGroup",
    "GroupExpense", "GroupIncome", "GroupInvitation", "GroupMember",
]
