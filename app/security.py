"""Password hashing, login session cookies, and user authentication."""
import hashlib
import os
import secrets
import time

from fastapi import Depends, HTTPException, Request, Response
from app.database import MongoSession as Session

from app.database import get_db
from app.models.user import LoginSession, User

COOKIE_NAME = "expense_session"
SESSION_SECONDS = 7 * 24 * 60 * 60


def hash_password(password: str, salt: str) -> str:
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME, "")
    session = db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest())
    if session is None or session.expires_at <= int(time.time()):
        raise HTTPException(status_code=401, detail="Please log in")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Please log in")
    return user


def start_session(response: Response, user: User, db: Session):
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=hashlib.sha256(token.encode()).hexdigest(),
                        user_id=user.id, expires_at=int(time.time()) + SESSION_SECONDS))
    db.commit()
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="strict",
                        secure=os.getenv("COOKIE_SECURE", "0") == "1", max_age=SESSION_SECONDS)
    return {"username": user.username}
