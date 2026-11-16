import unittest
import test_accounts
from fastapi.testclient import TestClient
from main import app


class PasswordTests(unittest.TestCase):
    setUp = test_accounts.AccountTests.setUp
    tearDown = test_accounts.AccountTests.tearDown
    register = test_accounts.AccountTests.register

    def test_change_requires_current_password_and_rotates_sessions(self):
        url = "/api/auth/password"
        payload = {"current_password": "test-password", "new_password": "new-password-123"}
        self.assertEqual(self.alice.put(url, json=payload).status_code, 401)
        self.register(self.alice, "alice")
        self.register(self.bob, "bob")
        other = TestClient(app)
        try:
            other.post("/api/auth/login", json={"username": "alice", "password": "test-password"})
            self.assertEqual(self.alice.put(url, json={**payload, "current_password": "wrong"}).status_code, 400)
            self.assertEqual(self.alice.put(url, json={**payload, "new_password": "short"}).status_code, 422)
            self.assertEqual(self.alice.put(url, json={**payload, "new_password": "test-password"}).status_code, 400)
            self.assertEqual(other.get("/api/auth/me").status_code, 200)
            self.assertEqual(self.alice.put(url, json=payload).status_code, 200)
            self.assertEqual(self.alice.get("/api/auth/me").status_code, 200)
            self.assertEqual(other.get("/api/auth/me").status_code, 401)
            self.assertEqual(self.bob.get("/api/auth/me").status_code, 200)
            self.assertEqual(other.post("/api/auth/login", json={"username": "alice", "password": "test-password"}).status_code, 401)
            self.assertEqual(other.post("/api/auth/login", json={"username": "alice", "password": "new-password-123"}).status_code, 200)
        finally:
            other.close()
