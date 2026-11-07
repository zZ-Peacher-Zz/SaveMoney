from dataclasses import dataclass
from datetime import date
from typing import ClassVar, Optional

from app.models.document import Document


@dataclass(kw_only=True)
class User(Document):
    collection: ClassVar[str] = 'users'
    key_fields: ClassVar[tuple] = ('id',)
    unique_fields: ClassVar[tuple] = (('username',),)
    id: int = None
    username: str
    password_hash: str


@dataclass(kw_only=True)
class LoginSession(Document):
    collection: ClassVar[str] = 'login_sessions'
    key_fields: ClassVar[tuple] = ('token_hash',)
    unique_fields: ClassVar[tuple] = ()
    token_hash: str
    user_id: int
    expires_at: int


@dataclass(kw_only=True)
class UserAvatar(Document):
    collection: ClassVar[str] = 'user_avatars'
    key_fields: ClassVar[tuple] = ('user_id',)
    unique_fields: ClassVar[tuple] = ()
    user_id: int
    image: bytes
