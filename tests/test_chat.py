import unittest

import test_accounts
from sqlalchemy.orm import Session

from app.models.chat import GroupMessage


class ChatTests(unittest.TestCase):
    setUp = test_accounts.AccountTests.setUp
    tearDown = test_accounts.AccountTests.tearDown
    register = test_accounts.AccountTests.register

    def family(self):
        self.register(self.alice, "alice")
        self.register(self.bob, "bob")
        group = self.alice.post("/api/groups", json={"name": "Family"}).json()["id"]
        return group, f"/api/groups/{group}/messages"

    def test_messages_require_membership_and_persist(self):
        group, url = self.family()
        self.assertEqual(self.bob.get(url).status_code, 404)
        self.assertEqual(self.bob.post(url, json={"content": "hello"}).status_code, 404)
        self.alice.post(f"/api/groups/{group}/invitations", json={"username": "bob"})
        self.assertEqual(self.bob.get(url).status_code, 404)
        self.bob.post(f"/api/invitations/{group}/accept")
        sent = self.bob.post(url, json={"content": "  Hello family!  "})
        self.assertEqual(sent.status_code, 201)
        message = sent.json()
        self.assertEqual(message["username"], "bob")
        self.assertEqual(message["content"], "Hello family!")
        self.assertTrue(message["is_mine"])
        response = self.alice.get(url)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertFalse(response.json()["messages"][0]["is_mine"])
        with Session(self.engine) as db:
            self.assertEqual(db.get(GroupMessage, message["id"]).content, "Hello family!")
        self.alice.delete(f"/api/groups/{group}/members/" + str(self.bob.get(f"/api/groups/{group}/members").json()[1]["id"]))
        self.assertEqual(self.bob.get(url).status_code, 404)
        self.assertEqual(self.bob.post(url, json={"content": "no access"}).status_code, 404)

    def test_pagination_validation_and_group_isolation(self):
        group, url = self.family()
        other = self.alice.post("/api/groups", json={"name": "Other"}).json()["id"]
        self.assertEqual(self.alice.post(url, json={"content": "   "}).status_code, 422)
        self.assertEqual(self.alice.post(url, json={"content": "x" * 2001}).status_code, 422)
        with Session(self.engine) as db:
            from app.models.user import User
            from sqlalchemy import select
            user = db.scalar(select(User).where(User.username == "alice"))
            for i in range(105):
                db.add(GroupMessage(group_id=group, user_id=user.id, content=str(i), created_at=1000+i))
            db.commit()
        latest = self.alice.get(url).json()
        self.assertEqual(len(latest["messages"]), 100)
        self.assertTrue(latest["has_more"])
        self.assertEqual(latest["messages"][0]["content"], "5")
        first_id = latest["messages"][0]["id"]
        older = self.alice.get(url, params={"before_id": first_id}).json()
        self.assertEqual(len(older["messages"]), 5)
        self.assertFalse(older["has_more"])
        updates = self.alice.get(url, params={"after_id": 0}).json()
        self.assertEqual(updates["messages"][0]["content"], "0")
        self.assertTrue(updates["has_more"])
        last_id = updates["messages"][-1]["id"]
        self.assertEqual(len(self.alice.get(url, params={"after_id": last_id}).json()["messages"]), 5)
        self.assertEqual(self.alice.get(f"/api/groups/{other}/messages").json()["messages"], [])
        self.assertEqual(self.alice.get(url, params={"after_id": -1}).status_code, 422)
        self.assertEqual(self.alice.get(url, params={"before_id": 10, "after_id": 1}).status_code, 400)
        self.alice.post("/api/auth/logout")
        self.assertEqual(self.alice.get(url).status_code, 401)
