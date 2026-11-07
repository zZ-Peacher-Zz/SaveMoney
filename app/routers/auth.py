import hashlib
import secrets

from fastapi import Request, Response
from sqlalchemy.exc import IntegrityError

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import LoginSession, User, UserAvatar
from app.schemas.auth import Credentials, Registration
from app.recovery import issue_link, limit_requests
from app.security import COOKIE_NAME, current_user, hash_password, start_session

router = APIRouter()


@router.post("/api/auth/register", status_code=201)
def register(payload: Registration, request: Request, response: Response, db: Session = Depends(get_db)):
    username = payload.username.lower()
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(status_code=409, detail="Username already exists")
    if payload.email:
        client = request.client.host if request.client else "unknown"
        # Commit quotas with the account so delivery/configuration failures don't consume them.
        limit_requests(db, f"registration-ip:{client}", 900, 5, commit=False)
        limit_requests(db, f"registration-email:{payload.email}", 60, 1, commit=False)
    salt = secrets.token_hex(16)
    user = User(username=username, password_hash=salt + ":" + hash_password(payload.password, salt))
    db.add(user)
    try:
        db.flush()
        if payload.email:
            issue_link(db, user.id, str(payload.email), "verify")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already exists")
    return start_session(response, user, db)


@router.post("/api/auth/login")
def login(payload: Credentials, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username.lower()))
    salt, stored = user.password_hash.split(":") if user else ("00" * 16, "")
    valid = secrets.compare_digest(hash_password(payload.password, salt), stored)
    if not user or not valid:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return start_session(response, user, db)


@router.get("/api/auth/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"username": user.username, "avatar_url": "/api/auth/avatar" if db.get(UserAvatar, user.id) else None}


@router.post("/api/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME, "")
    db.execute(delete(LoginSession).where(LoginSession.token_hash == hashlib.sha256(token.encode()).hexdigest()))
    db.commit()
    response.delete_cookie(COOKIE_NAME)
