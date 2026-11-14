import time

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database import get_db
from app.dependencies import require_group
from app.models.group import GroupMember
from app.models.presence import UserPresence
from app.models.user import User
from app.security import current_user

router = APIRouter()
ONLINE_SECONDS = 75


@router.post("/api/auth/presence", status_code=204)
def heartbeat(response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
    now = int(time.time())
    statement = insert(UserPresence).values(user_id=user.id, last_seen=now)
    db.execute(statement.on_conflict_do_update(index_elements=[UserPresence.user_id], set_={"last_seen": now}))
    db.commit()
    response.headers["Cache-Control"] = "no-store"


@router.get("/api/groups/{group_id}/presence")
def group_presence(group_id: int, response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_group(db, group_id, user)
    rows = db.execute(select(User.id, User.username, UserPresence.last_seen).join(
        GroupMember, GroupMember.user_id == User.id
    ).outerjoin(UserPresence, UserPresence.user_id == User.id).where(GroupMember.group_id == group_id)).all()
    cutoff = int(time.time()) - ONLINE_SECONDS
    response.headers["Cache-Control"] = "no-store"
    return [{"user_id": row.id, "username": row.username, "online": row.last_seen is not None and row.last_seen >= cutoff} for row in rows]
