import os
import unittest

os.environ["DATABASE_URL"] = "sqlite://"
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from main import app
from app.database import Base, get_db
from app.security import COOKIE_NAME


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        factory = sessionmaker(bind=self.engine)
        def database():
            with factory() as db:
                yield db
        app.dependency_overrides[get_db] = database
        self.alice = TestClient(app)
        self.bob = TestClient(app)
        self.payload = {"expense_date": "2026-11-07", "category": "Food", "amount": 100, "note": "Lunch"}

    def tearDown(self):
        self.alice.close()
        self.bob.close()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def register(self, client, name):
        response = client.post("/api/auth/register", json={"username": name, "password": "test-password"})
        self.assertEqual(response.status_code, 201)
        return response

    def test_authentication_and_logout(self):
        self.assertEqual(self.alice.get("/api/months/2026-11/summary").status_code, 401)
        response = self.register(self.alice, "Alice")
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertEqual(self.alice.get("/api/auth/me").json(), {"username": "alice", "avatar_url": None})
        token = self.alice.cookies.get(COOKIE_NAME)
        self.assertEqual(self.alice.post("/api/auth/logout").status_code, 204)
        self.alice.cookies.set(COOKIE_NAME, token)
        self.assertEqual(self.alice.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.alice.post("/api/auth/login", json={"username": "alice", "password": "wrong-password"}).status_code, 401)
        self.assertEqual(self.alice.post("/api/auth/login", json={"username": "ALICE", "password": "test-password"}).status_code, 200)
        self.assertEqual(self.bob.post("/api/auth/register", json={"username": "ALICE", "password": "another-password"}).status_code, 409)

    def test_records_are_private(self):
        self.register(self.alice, "alice")
        self.register(self.bob, "bob")
        for client, amount in [(self.alice, 1000), (self.bob, 2000)]:
            self.assertEqual(client.put("/api/months/2026-11/income", json={"amount": amount}).status_code, 200)
        response = self.alice.post("/api/expenses", json=self.payload)
        self.assertEqual(response.status_code, 201)
        expense_id = response.json()["id"]
        self.assertEqual(self.bob.get("/api/months/2026-11/expenses").json(), [])
        self.assertEqual(self.bob.put(f"/api/expenses/{expense_id}", json=self.payload).status_code, 404)
        self.assertEqual(self.bob.delete(f"/api/expenses/{expense_id}").status_code, 404)
        self.assertNotIn("Lunch", self.bob.get("/api/months/2026-11/export.csv").text)
        self.assertIn("Lunch", self.alice.get("/api/months/2026-11/export.csv").text)
        summary = self.alice.get("/api/months/2026-11/summary").json()
        self.assertEqual(summary["remaining"], 900)
        self.assertEqual(self.bob.get("/api/months/2026-11/summary").json()["income"], 2000)
        self.assertEqual(self.bob.delete("/api/months/2026-11").status_code, 204)
        self.assertEqual(self.alice.get("/api/months/2026-11/summary").json()["remaining"], 900)
        self.assertEqual(self.alice.put(f"/api/expenses/{expense_id}", json={**self.payload, "amount": 150}).status_code, 200)
        self.assertEqual(self.alice.delete(f"/api/expenses/{expense_id}").status_code, 204)

    def test_unauthenticated_routes_and_validation(self):
        for method, url, payload in [
            ("get", "/api/months/2026-11/expenses", None),
            ("get", "/api/months/2026-11/export.csv", None),
            ("put", "/api/months/2026-11/income", {"amount": 500}),
            ("post", "/api/expenses", self.payload),
            ("put", "/api/expenses/1", self.payload),
            ("delete", "/api/expenses/1", None),
            ("delete", "/api/months/2026-11", None),
        ]:
            self.assertEqual(self.alice.request(method, url, json=payload).status_code, 401)
        self.assertEqual(self.alice.post("/api/auth/register", json={"username": "a", "password": "short"}).status_code, 422)

    def family(self):
        self.register(self.alice, "alice")
        self.register(self.bob, "bob")
        response = self.alice.post("/api/groups", json={"name": "Our family"})
        self.assertEqual(response.status_code, 201)
        group = response.json()["id"]
        self.assertEqual(self.alice.post(f"/api/groups/{group}/invitations", json={"username": "BOB"}).status_code, 201)
        self.assertEqual(self.bob.post(f"/api/invitations/{group}/accept").status_code, 204)
        return group, f"?group_id={group}"

    def test_family_invitations_require_consent_and_owner(self):
        self.register(self.alice, "alice")
        self.register(self.bob, "bob")
        group = self.alice.post("/api/groups", json={"name": "Family"}).json()["id"]
        self.assertEqual(self.bob.get("/api/groups").json(), [])
        self.assertEqual(self.bob.post(f"/api/invitations/{group}/accept").status_code, 404)
        self.assertEqual(self.bob.post(f"/api/groups/{group}/invitations", json={"username": "alice", "avatar_url": None}).status_code, 404)
        self.assertEqual(self.alice.post(f"/api/groups/{group}/invitations", json={"username": "bob"}).status_code, 201)
        self.assertEqual(self.alice.post(f"/api/groups/{group}/invitations", json={"username": "bob"}).status_code, 409)
        self.assertEqual(self.bob.get(f"/api/months/2026-11/summary?group_id={group}").status_code, 404)
        self.assertEqual(self.bob.get("/api/invitations").json()[0]["name"], "Family")
        self.assertEqual(self.bob.delete(f"/api/invitations/{group}").status_code, 204)
        self.assertEqual(self.bob.get("/api/invitations").json(), [])
        self.alice.post(f"/api/groups/{group}/invitations", json={"username": "bob"})
        self.assertEqual(self.bob.post(f"/api/invitations/{group}/accept").status_code, 204)
        self.assertEqual(self.bob.post(f"/api/groups/{group}/invitations", json={"username": "alice", "avatar_url": None}).status_code, 403)

    def test_family_income_and_private_records(self):
        group, scope = self.family()
        self.alice.put("/api/months/2026-11/income", json={"amount": 9000})
        self.alice.post("/api/expenses", json={**self.payload, "note": "Private lunch"})
        for client, amount in [(self.alice, 1000), (self.bob, 2000)]:
            self.assertEqual(client.put("/api/months/2026-11/income" + scope, json={"amount": amount}).status_code, 200)
        self.bob.put("/api/months/2026-11/income" + scope, json={"amount": 3000})
        self.assertEqual(self.bob.post("/api/expenses" + scope, json=self.payload).status_code, 201)
        for client, mine in [(self.alice, 1000), (self.bob, 3000)]:
            summary = client.get("/api/months/2026-11/summary" + scope).json()
            self.assertEqual(summary["income"], 4000)
            self.assertEqual(summary["my_income"], mine)
            self.assertEqual(summary["remaining"], 3900)
            items = client.get("/api/months/2026-11/expenses" + scope).json()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["username"], "bob")
            self.assertNotIn("Private lunch", client.get("/api/months/2026-11/export.csv" + scope).text)
        self.assertEqual(self.alice.get("/api/months/2026-11/summary").json()["income"], 9000)
        self.assertEqual(self.bob.get("/api/months/2026-11/expenses").json(), [])
        other = self.alice.post("/api/groups", json={"name": "Other family"}).json()["id"]
        self.assertEqual(self.alice.get(f"/api/months/2026-11/summary?group_id={other}").json()["income"], 0)
        self.assertEqual(self.bob.get(f"/api/months/2026-11/summary?group_id={other}").status_code, 404)
        self.assertEqual(self.bob.delete("/api/months/2026-11" + scope).status_code, 403)
        self.assertEqual(self.alice.delete("/api/months/2026-11" + scope).status_code, 204)
        self.assertEqual(self.bob.get("/api/months/2026-11/summary" + scope).json()["income"], 0)
        self.assertEqual(self.alice.get("/api/months/2026-11/summary").json()["income"], 9000)

    def test_family_expense_permissions_and_removal(self):
        group, scope = self.family()
        own = self.alice.post("/api/expenses" + scope, json=self.payload).json()["id"]
        other = self.bob.post("/api/expenses" + scope, json=self.payload).json()["id"]
        self.assertEqual(self.bob.put(f"/api/expenses/{own}" + scope, json=self.payload).status_code, 403)
        self.assertEqual(self.bob.delete(f"/api/expenses/{own}" + scope).status_code, 403)
        self.assertEqual(self.bob.put(f"/api/expenses/{other}" + scope, json=self.payload).status_code, 200)
        self.assertEqual(self.alice.put(f"/api/expenses/{other}" + scope, json=self.payload).status_code, 200)
        members = self.alice.get(f"/api/groups/{group}/members").json()
        owner = next(m["id"] for m in members if m["is_owner"])
        member = next(m["id"] for m in members if not m["is_owner"])
        self.assertEqual(self.bob.delete(f"/api/groups/{group}/members/{owner}").status_code, 403)
        self.assertEqual(self.alice.delete(f"/api/groups/{group}/members/{owner}").status_code, 400)
        self.assertEqual(self.alice.delete(f"/api/groups/{group}/members/{member}").status_code, 204)
        for url in ["/api/months/2026-11/summary", "/api/months/2026-11/expenses", "/api/months/2026-11/export.csv"]:
            self.assertEqual(self.bob.get(url + scope).status_code, 404)
        self.assertEqual(self.bob.post("/api/expenses" + scope, json=self.payload).status_code, 404)
        self.assertEqual(self.bob.put(f"/api/expenses/{other}" + scope, json=self.payload).status_code, 404)
        self.assertEqual(self.bob.get(f"/api/groups/{group}/members").status_code, 404)
        self.assertEqual(self.bob.get("/api/groups").json(), [])
        self.assertEqual(len(self.alice.get("/api/months/2026-11/expenses" + scope).json()), 2)
        self.assertEqual(self.alice.delete(f"/api/expenses/{other}" + scope).status_code, 204)

    def test_avatar_upload_is_private_and_validated(self):
        from io import BytesIO
        from PIL import Image
        image = BytesIO()
        Image.new("RGB", (400, 300), "blue").save(image, "JPEG")
        data = image.getvalue()
        self.assertEqual(self.alice.put("/api/auth/avatar", content=data).status_code, 401)
        self.register(self.alice, "alice")
        self.register(self.bob, "bob")
        self.assertEqual(self.alice.put("/api/auth/avatar", content=data).status_code, 200)
        avatar = self.alice.get("/api/auth/avatar")
        self.assertEqual(avatar.status_code, 200)
        self.assertEqual(Image.open(BytesIO(avatar.content)).size, (256, 256))
        self.assertEqual(avatar.headers["content-type"], "image/png")
        self.assertEqual(self.bob.get("/api/auth/avatar").status_code, 404)
        self.assertEqual(self.alice.get("/api/auth/me").json()["avatar_url"], "/api/auth/avatar")
        self.assertEqual(self.alice.put("/api/auth/avatar", content=b"not an image").status_code, 400)
        self.assertEqual(self.alice.put("/api/auth/avatar", content=b"x" * (5 * 1024 * 1024 + 1)).status_code, 413)
        self.assertEqual(self.alice.get("/api/auth/avatar").content, avatar.content)
        self.alice.post("/api/auth/logout")
        self.alice.post("/api/auth/login", json={"username": "alice", "password": "test-password"})
        self.assertEqual(self.alice.get("/api/auth/avatar").content, avatar.content)
        self.assertEqual(self.alice.delete("/api/auth/avatar").status_code, 204)
        self.assertEqual(self.alice.get("/api/auth/me").json()["avatar_url"], None)
        self.assertEqual(self.alice.get("/api/auth/avatar").status_code, 404)

    def test_member_avatars_require_shared_membership(self):
        from io import BytesIO
        from PIL import Image
        group, scope = self.family()
        image = BytesIO()
        Image.new("RGB", (32, 32), "red").save(image, "PNG")
        self.bob.put("/api/auth/avatar", content=image.getvalue())
        members = self.alice.get(f"/api/groups/{group}/members").json()
        bob = next(m for m in members if m["username"] == "bob")
        alice = next(m for m in members if m["username"] == "alice")
        self.assertIsNone(alice["avatar_url"])
        url = bob["avatar_url"]
        self.assertEqual(self.alice.get(url).status_code, 200)
        self.assertEqual(self.alice.get(url).content, self.bob.get("/api/auth/avatar").content)
        other = self.alice.post("/api/groups", json={"name": "Other"}).json()["id"]
        self.assertEqual(self.alice.get(f"/api/groups/{other}/members/{bob['id']}/avatar").status_code, 404)
        self.alice.delete(f"/api/groups/{group}/members/{bob['id']}")
        self.assertEqual(self.alice.get(url).status_code, 404)
        self.assertEqual(self.bob.get(f"/api/groups/{group}/members/{alice['id']}/avatar").status_code, 404)

    def test_home_redirects_without_valid_session(self):
        response = self.alice.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(self.alice.get("/").status_code, 200)
        self.register(self.alice, "alice")
        response = self.alice.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="dashboard"', response.text)
        self.alice.post("/api/auth/logout")
        self.assertEqual(self.alice.get("/", follow_redirects=False).status_code, 303)
        for path in ("/login", "/register", "/forgot-password", "/reset-password", "/verify-email"):
            self.assertEqual(self.alice.get(path, follow_redirects=False).status_code, 200)


if __name__ == "__main__":
    unittest.main()
