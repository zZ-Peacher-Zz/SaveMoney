import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pymongo.errors import DuplicateKeyError
from app.database import MongoSession as Session

from app.database import get_db
from app.models.recovery import RecoveryEmail, RecoveryToken
from app.models.user import LoginSession, User
from app.recovery import consume_token, delivery_configured, issue_link, limit_requests
from app.schemas.recovery import EmailPayload, ResetPassword, SetRecoveryEmail, TokenPayload
from app.security import COOKIE_NAME, current_user, hash_password

router = APIRouter(prefix="/api/auth")


@router.get("/recovery-email")
def recovery_email(user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(RecoveryEmail, user.id)
    return {"email": row.email if row else None}


@router.put("/recovery-email")
def set_recovery_email(payload: SetRecoveryEmail, user: User = Depends(current_user), db: Session = Depends(get_db)):
    limit_requests(db, f"setup:{user.id}", 60, 3)
    salt, stored = user.password_hash.split(":")
    if not secrets.compare_digest(hash_password(payload.password, salt), stored):
        raise HTTPException(400, "Current password is incorrect")
    issue_link(db, user.id, str(payload.email), "verify")
    db.commit()
    return {"message": "Check your email to confirm your recovery address."}


@router.post("/verify-email")
def verify_email(payload: TokenPayload, db: Session = Depends(get_db)):
    token = consume_token(db, payload.token, "verify")
    email = db.get(RecoveryEmail, token.user_id)
    if email is None:
        db.add(RecoveryEmail(user_id=token.user_id, email=token.email))
    else:
        email.email = token.email
    try:
        db.delete_many(RecoveryToken, {"user_id": token.user_id})
        db.commit()
    except DuplicateKeyError:
        db.rollback()
        raise HTTPException(400, "This recovery email cannot be used. Please choose another email.")
    return {"message": "Recovery email verified. You can now reset your password by email."}


@router.post("/forgot-password")
def forgot_password(payload: EmailPayload, request: Request, db: Session = Depends(get_db)):
    # Apply the same limits to known and unknown addresses, without exposing accounts.
    client = request.client.host if request.client else "unknown"
    limit_requests(db, f"forgot-ip:{client}", 900, 20)
    limit_requests(db, f"forgot-email:{payload.email}", 60, 1)
    # Report missing delivery configuration for all addresses consistently.
    if not delivery_configured():
        raise HTTPException(503, "Email delivery is not configured. Please contact the administrator.")
    row = db.one(RecoveryEmail, {"email": str(payload.email)})
    if row:
        try:
            issue_link(db, row.user_id, row.email, "reset")
            db.commit()
        except HTTPException:
            # A provider failure must not reveal that this address belongs to an account.
            db.rollback()
    return {"message": "If this email is registered and verified, a reset link will be sent."}


@router.post("/reset-password")
def reset_password(payload: ResetPassword, response: Response, db: Session = Depends(get_db)):
    token = consume_token(db, payload.token, "reset")
    user = db.get(User, token.user_id)
    email = db.get(RecoveryEmail, token.user_id)
    if user is None or email is None or email.email != token.email:
        raise HTTPException(400, "This link is no longer valid")
    salt = secrets.token_hex(16)
    user.password_hash = salt + ":" + hash_password(payload.password, salt)
    db.delete_many(LoginSession, {"user_id": user.id})
    db.delete_many(RecoveryToken, {"user_id": user.id})
    db.commit()
    response.delete_cookie(COOKIE_NAME)
    return {"message": "Password updated. Please log in with your new password."}
