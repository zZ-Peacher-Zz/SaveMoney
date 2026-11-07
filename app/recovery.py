"""One-use recovery links and SMTP delivery; raw tokens never enter the database."""
import hashlib
import json
import os
import secrets
import smtplib
import ssl
import time
from email.message import EmailMessage
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from urllib.error import URLError

from fastapi import HTTPException
from sqlalchemy import delete

from app.models.recovery import RecoveryLimit, RecoveryToken


def delivery_configured():
    return bool(os.getenv("APP_BASE_URL") and (os.getenv("EMAIL_FROM") or os.getenv("SMTP_FROM"))
                and (os.getenv("RESEND_API_KEY") or os.getenv("SMTP_HOST")))


def send_mail(email, subject, link):
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("EMAIL_FROM") or os.getenv("SMTP_FROM")
    api_key = os.getenv("RESEND_API_KEY")
    if not sender or not (host or api_key):
        raise HTTPException(503, "Email delivery is not configured. Please contact the administrator.")
    text = f"SaveMoney\n\n{subject}\n\n{link}\n\nThis link expires in 30 minutes and can only be used once.\nIf you did not request this, ignore this email."
    if api_key:
        request = Request("https://api.resend.com/emails", method="POST",
                          data=json.dumps({"from": sender, "to": [email], "subject": subject, "text": text}).encode(),
                          headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": "SaveMoney/1.0"})
        try:
            with urlopen(request, timeout=15) as response:
                if response.status >= 300:
                    raise HTTPException(503, "Could not send email. Please try again later.")
        except (URLError, OSError):
            raise HTTPException(503, "Could not send email. Please try again later.")
        return
    message = EmailMessage()
    message["From"] = sender
    message["To"] = email
    message["Subject"] = subject
    message.set_content(text)
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        connection = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
        with connection(host, port, timeout=15) as smtp:
            if port != 465:
                smtp.starttls(context=ssl.create_default_context())
            if os.getenv("SMTP_USER"):
                smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError, KeyError):
        raise HTTPException(503, "Could not send email. Please try again later.")


def limit_requests(db, key, seconds, maximum, commit=True):
    key = hashlib.sha256(key.encode()).hexdigest()
    now = int(time.time())
    limit = db.get(RecoveryLimit, key)
    if limit is None:
        db.add(RecoveryLimit(key=key, started_at=now, count=1))
    elif now - limit.started_at >= seconds:
        limit.started_at, limit.count = now, 1
    elif limit.count >= maximum:
        retry_after = max(1, seconds - (now - limit.started_at))
        raise HTTPException(429, f"Bạn thao tác quá nhanh. Vui lòng thử lại sau {retry_after} giây.",
                            headers={"Retry-After": str(retry_after)})
    else:
        limit.count += 1
    if commit:
        db.commit()


def issue_link(db, user_id, email, purpose):
    base = os.getenv("APP_BASE_URL", "").rstrip("/")
    parsed = urlsplit(base)
    if not parsed.netloc or parsed.query or parsed.fragment or parsed.username or (parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"})):
        raise HTTPException(503, "APP_BASE_URL must be configured for email links")
    token = secrets.token_urlsafe(32)
    db.execute(delete(RecoveryToken).where(RecoveryToken.user_id == user_id, RecoveryToken.purpose == purpose))
    db.add(RecoveryToken(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user_id,
                         email=email, purpose=purpose, expires_at=int(time.time()) + 1800))
    # Fragments keep secrets out of HTTP access logs and Referer headers.
    path = "/verify-email" if purpose == "verify" else "/reset-password"
    link = base + path + "#" + urlencode({"action": purpose, "token": token})
    send_mail(email, "Verify recovery email" if purpose == "verify" else "Reset your password", link)


def consume_token(db, token, purpose):
    digest = hashlib.sha256(token.encode()).hexdigest()
    row = db.get(RecoveryToken, digest)
    if row is None or row.purpose != purpose or row.expires_at <= int(time.time()):
        raise HTTPException(400, "This link is invalid or expired. Please request a new one.")
    result = db.execute(delete(RecoveryToken).where(RecoveryToken.token_hash == digest,
                        RecoveryToken.purpose == purpose, RecoveryToken.expires_at > int(time.time())),
                        execution_options={"synchronize_session": False})
    if result.rowcount != 1:
        raise HTTPException(400, "This link has already been used")
    return row
