from dataclasses import dataclass
from datetime import date
from typing import ClassVar, Optional

from app.models.document import Document


@dataclass(kw_only=True)
class RecoveryEmail(Document):
    collection: ClassVar[str] = 'recovery_emails'
    key_fields: ClassVar[tuple] = ('user_id',)
    unique_fields: ClassVar[tuple] = (('email',),)
    user_id: int
    email: str


@dataclass(kw_only=True)
class RecoveryToken(Document):
    collection: ClassVar[str] = 'recovery_tokens'
    key_fields: ClassVar[tuple] = ('token_hash',)
    unique_fields: ClassVar[tuple] = ()
    token_hash: str
    user_id: int
    email: str
    purpose: str
    expires_at: int


@dataclass(kw_only=True)
class RecoveryLimit(Document):
    collection: ClassVar[str] = 'recovery_limits'
    key_fields: ClassVar[tuple] = ('key',)
    unique_fields: ClassVar[tuple] = ()
    key: str
    started_at: int
    count: int
