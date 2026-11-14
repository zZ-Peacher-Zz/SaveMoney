import time

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_group
from app.models.chat import GroupMessage
from app.models.user import User, UserAvatar
from app.models.group import GroupMember
from app.security import current_user

router = APIRouter(prefix="/api/groups/{group_id}/messages")


class MessagePayload(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def clean_content(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value.strip()


def serialize(message, username, user, avatar_ids=()):
    return {"id": message.id, "username": username, "content": message.content,
            "created_at": message.created_at, "is_mine": message.user_id == user.id,
            "user_id": message.user_id,
            "avatar_url": f"/api/groups/{message.group_id}/members/{message.user_id}/avatar" if message.user_id in avatar_ids else None}


@router.get("")
def list_messages(group_id: int, response: Response,
                  after_id: int | None = Query(default=None, ge=0),
                  before_id: int | None = Query(default=None, ge=1),
                  db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_group(db, group_id, user)
    response.headers["Cache-Control"] = "no-store"
    if after_id is not None and before_id is not None:
        raise HTTPException(400, "Use either after_id or before_id")
    query = select(GroupMessage, User.username).join(User, User.id == GroupMessage.user_id).where(GroupMessage.group_id == group_id)
    if after_id is not None:
        query = query.where(GroupMessage.id > after_id).order_by(GroupMessage.id)
    else:
        if before_id is not None:
            query = query.where(GroupMessage.id < before_id)
        query = query.order_by(GroupMessage.id.desc())
    rows = db.execute(query.limit(101)).all()
    more = len(rows) > 100
    rows = rows[:100]
    if after_id is None:
        rows.reverse()
    author_ids = {message.user_id for message, _ in rows}
    avatar_ids = set(db.scalars(select(UserAvatar.user_id).join(
        GroupMember, GroupMember.user_id == UserAvatar.user_id
    ).where(GroupMember.group_id == group_id, UserAvatar.user_id.in_(author_ids))).all()) if author_ids else set()
    return {"messages": [serialize(message, username, user, avatar_ids) for message, username in rows], "has_more": more}


@router.post("", status_code=201)
def send_message(group_id: int, payload: MessagePayload, response: Response,
                 db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_group(db, group_id, user)
    message = GroupMessage(group_id=group_id, user_id=user.id, content=payload.content,
                           created_at=int(time.time() * 1000))
    db.add(message)
    db.commit()
    db.refresh(message)
    response.headers["Cache-Control"] = "no-store"
    avatar_ids = {user.id} if db.scalar(select(UserAvatar.user_id).where(UserAvatar.user_id == user.id)) is not None else set()
    return serialize(message, user.username, user, avatar_ids)
