import unittest
from unittest.mock import patch

import test_accounts


class PresenceTests(unittest.TestCase):
    setUp = test_accounts.AccountTests.setUp
    tearDown = test_accounts.AccountTests.tearDown
    register = test_accounts.AccountTests.register

    def test_presence_membership_expiry_and_heartbeat(self):
        self.assertEqual(self.alice.post("/api/auth/presence").status_code, 401)
        self.register(self.alice, "alice")
        self.register(self.bob, "bob")
        group = self.alice.post("/api/groups", json={"name": "Family"}).json()["id"]
        url = f"/api/groups/{group}/presence"
        self.assertEqual(self.bob.get(url).status_code, 404)
        self.alice.post(f"/api/groups/{group}/invitations", json={"username": "bob"})
        self.assertEqual(self.bob.get(url).status_code, 404)
        self.bob.post(f"/api/invitations/{group}/accept")
        with patch("app.routers.presence.time.time", return_value=1000):
            self.assertEqual(self.alice.post("/api/auth/presence").status_code, 204)
            self.assertEqual(self.alice.post("/api/auth/presence").status_code, 204)
            response = self.bob.get(url)
            self.assertEqual(response.headers["cache-control"], "no-store")
            users = {row["username"]: row for row in response.json()}
            self.assertTrue(users["alice"]["online"])
            self.assertFalse(users["bob"]["online"])
        with patch("app.routers.presence.time.time", return_value=1076):
            self.assertFalse(any(row["online"] for row in self.bob.get(url).json()))
            self.bob.post("/api/auth/presence")
            self.assertTrue(next(row["online"] for row in self.alice.get(url).json() if row["username"] == "bob"))
        self.alice.delete(f"/api/groups/{group}/members/{users['bob']['user_id']}")
        self.assertEqual(self.bob.get(url).status_code, 404)
        self.assertEqual(len(self.alice.get(url).json()), 1)
