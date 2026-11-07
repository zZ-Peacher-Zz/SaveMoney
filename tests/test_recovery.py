import os
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

import test_accounts
from app.models.recovery import RecoveryToken


class RecoveryTests(unittest.TestCase):
    setUp = test_accounts.AccountTests.setUp
    tearDown = test_accounts.AccountTests.tearDown
    register = test_accounts.AccountTests.register

    def setup_email(self, email="alice@example.com"):
        response = self.alice.put("/api/auth/recovery-email", json={"email": email, "password": "test-password"})
        self.assertEqual(response.status_code, 200, response.text)
        return self.token()

    def token(self):
        link = self.mail.call_args.args[2]
        return parse_qs(urlsplit(link).fragment)["token"][0]

    def run(self, result=None):
        with patch.dict(os.environ, {"APP_BASE_URL": "https://savemoney.example.com", "SMTP_HOST": "smtp.example.com", "SMTP_FROM": "sender@example.com", "RESEND_API_KEY": "", "EMAIL_FROM": ""}):
            with patch("app.recovery.send_mail") as self.mail:
                return super().run(result)

    def test_complete_reset_revokes_sessions_and_rejects_reuse(self):
        self.register(self.alice, "alice")
        token = self.setup_email()
        self.assertEqual(self.alice.get("/api/auth/recovery-email").json(), {"email": None})
        self.assertEqual(self.bob.post("/api/auth/verify-email", json={"token": token}).status_code, 200)
        self.assertEqual(self.bob.post("/api/auth/verify-email", json={"token": token}).status_code, 400)
        response = self.bob.post("/api/auth/forgot-password", json={"email": "ALICE@example.com"})
        self.assertEqual(response.status_code, 200)
        token = self.token()
        with Session(self.engine) as db:
            self.assertNotEqual(db.scalar(select(RecoveryToken)).token_hash, token)
        self.assertEqual(self.bob.post("/api/auth/reset-password", json={"token": token, "password": "new-password"}).status_code, 200)
        self.assertEqual(self.alice.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.bob.post("/api/auth/reset-password", json={"token": token, "password": "other-password"}).status_code, 400)
        self.assertEqual(self.alice.post("/api/auth/login", json={"username": "alice", "password": "test-password"}).status_code, 401)
        self.assertEqual(self.alice.post("/api/auth/login", json={"username": "alice", "password": "new-password"}).status_code, 200)

    def test_unverified_unknown_addresses_are_generic_and_limited(self):
        self.register(self.alice, "alice")
        self.setup_email()
        self.mail.reset_mock()
        known = self.bob.post("/api/auth/forgot-password", json={"email": "alice@example.com"})
        unknown = self.bob.post("/api/auth/forgot-password", json={"email": "unknown@example.com"})
        self.assertEqual(known.json(), unknown.json())
        self.assertEqual(known.status_code, 200)
        self.mail.assert_not_called()
        self.assertEqual(self.bob.post("/api/auth/forgot-password", json={"email": "alice@example.com"}).status_code, 429)

    def test_expiry_purpose_and_current_password(self):
        self.register(self.alice, "alice")
        self.assertEqual(self.alice.put("/api/auth/recovery-email", json={"email": "alice@example.com", "password": "wrong-password"}).status_code, 400)
        token = self.setup_email()
        self.assertEqual(self.bob.post("/api/auth/reset-password", json={"token": token, "password": "new-password"}).status_code, 400)
        with Session(self.engine) as db:
            db.scalar(select(RecoveryToken)).expires_at = int(time.time()) - 1
            db.commit()
        self.assertEqual(self.bob.post("/api/auth/verify-email", json={"token": token}).status_code, 400)
        self.assertEqual(self.alice.put("/api/auth/recovery-email", json={"email": "not-email", "password": "test-password"}).status_code, 422)

    def test_registration_verification_and_duplicate_email(self):
        response = self.alice.post("/api/auth/register", json={"username": "alice", "password": "test-password", "email": "alice@example.com"})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(self.alice.post("/api/auth/verify-email", json={"token": self.token()}).status_code, 200)
        self.register(self.bob, "bob")
        self.assertEqual(self.bob.put("/api/auth/recovery-email", json={"email": "alice@example.com", "password": "test-password"}).status_code, 200)
        self.assertEqual(self.bob.post("/api/auth/verify-email", json={"token": self.token()}).status_code, 400)
        self.assertEqual(self.alice.get("/api/auth/recovery-email").json()["email"], "alice@example.com")

    def test_missing_smtp_and_delivery_failure_preserve_account(self):
        self.register(self.alice, "alice")
        with patch.dict(os.environ, {"SMTP_HOST": ""}):
            self.assertEqual(self.bob.post("/api/auth/forgot-password", json={"email": "unknown@example.com"}).status_code, 503)
        from fastapi import HTTPException
        self.mail.side_effect = HTTPException(503, "Delivery failed")
        self.assertEqual(self.alice.put("/api/auth/recovery-email", json={"email": "alice@example.com", "password": "test-password"}).status_code, 503)
        with Session(self.engine) as db:
            self.assertIsNone(db.scalar(select(RecoveryToken)))
        self.assertEqual(self.alice.get("/api/auth/me").status_code, 200)

    def test_email_change_invalidates_old_reset_links(self):
        self.register(self.alice, "alice")
        verify = self.setup_email()
        self.assertEqual(urlsplit(self.mail.call_args.args[2]).path, "/verify-email")
        self.bob.post("/api/auth/verify-email", json={"token": verify})
        self.bob.post("/api/auth/forgot-password", json={"email": "alice@example.com"})
        reset = self.token()
        self.assertEqual(urlsplit(self.mail.call_args.args[2]).path, "/reset-password")
        verify = self.setup_email("new@example.com")
        self.assertEqual(self.alice.get("/api/auth/recovery-email").json()["email"], "alice@example.com")
        self.assertEqual(self.bob.post("/api/auth/verify-email", json={"token": verify}).status_code, 200)
        self.assertEqual(self.alice.get("/api/auth/recovery-email").json()["email"], "new@example.com")
        self.assertEqual(self.bob.post("/api/auth/reset-password", json={"token": reset, "password": "new-password"}).status_code, 400)

    def test_failed_registration_does_not_consume_quota(self):
        from fastapi import HTTPException
        from app.models.recovery import RecoveryLimit
        self.mail.side_effect = HTTPException(503, "Email unavailable")
        payload = {"username": "alice", "password": "test-password", "email": "alice@example.com"}
        for _ in range(6):
            self.assertEqual(self.alice.post("/api/auth/register", json=payload).status_code, 503)
        with Session(self.engine) as db:
            self.assertIsNone(db.scalar(select(RecoveryLimit)))
        self.mail.side_effect = None
        self.assertEqual(self.alice.post("/api/auth/register", json=payload).status_code, 201)
        response = self.bob.post("/api/auth/register", json={**payload, "username": "another"})
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response.headers["Retry-After"]), 0)


class MailTransportTests(unittest.TestCase):
    def test_resend_delivery_uses_https(self):
        import json
        from app.recovery import send_mail
        with patch.dict(os.environ, {"RESEND_API_KEY": "test-key", "EMAIL_FROM": "sender@example.com"}):
            with patch("app.recovery.urlopen") as urlopen:
                urlopen.return_value.__enter__.return_value.status = 200
                send_mail("recipient@example.com", "Reset", "https://example.com/#token=test")
                request = urlopen.call_args.args[0]
                self.assertEqual(request.full_url, "https://api.resend.com/emails")
                payload = json.loads(request.data)
                self.assertEqual(payload["to"], ["recipient@example.com"])
                self.assertIn("#token=test", payload["text"])

    def test_delivery_failure_is_safe(self):
        from urllib.error import URLError
        from fastapi import HTTPException
        from app.recovery import send_mail
        with patch.dict(os.environ, {"RESEND_API_KEY": "test-key", "EMAIL_FROM": "sender@example.com"}):
            with patch("app.recovery.urlopen", side_effect=URLError("failure")):
                with self.assertRaises(HTTPException) as error:
                    send_mail("recipient@example.com", "Reset", "https://example.com/#token=test")
                self.assertEqual(error.exception.status_code, 503)
                self.assertNotIn("test-key", error.exception.detail)
