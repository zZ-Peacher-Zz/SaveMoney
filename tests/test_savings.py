import unittest
import test_accounts


class SavingsTests(unittest.TestCase):
    setUp = test_accounts.AccountTests.setUp
    tearDown = test_accounts.AccountTests.tearDown
    register = test_accounts.AccountTests.register

    def test_annual_target_and_progress_are_independent_of_months(self):
        self.register(self.alice, "alice")
        self.register(self.bob, "bob")
        self.alice.put("/api/months/2026-01/income", json={"amount": 1000})
        self.alice.put("/api/months/2026-11/income", json={"amount": 2000})
        self.alice.put("/api/months/2025-12/income", json={"amount": 9999})
        self.alice.post("/api/expenses", json=self.payload)
        self.alice.put("/api/months/2026-11/savings-goal", json={"amount": 500})
        url = "/api/years/2026/savings-goal"
        self.assertEqual(self.alice.put(url, json={"amount": 10000}).status_code, 200)
        data = self.alice.get("/api/years/2026/savings-summary").json()
        self.assertEqual(data["savings_goal"], 10000)
        self.assertEqual(data["remaining"], 2900)
        self.assertEqual(self.bob.get("/api/years/2026/savings-summary").json()["savings_goal"], 0)
        self.assertEqual(self.alice.get("/api/years/2025/savings-summary").json()["savings_goal"], 0)
        self.assertEqual(self.alice.get("/api/months/2026-11/summary").json()["savings_goal"], 500)
        self.assertEqual(self.alice.put(url, json={"amount": -1}).status_code, 422)
        self.assertEqual(self.alice.get("/api/years/99999/savings-summary").status_code, 400)
        self.alice.delete("/api/months/2026-11")
        self.assertEqual(self.alice.get("/api/years/2026/savings-summary").json()["savings_goal"], 10000)

    def test_personal_goals_are_monthly_private_and_cleared_with_month(self):
        url = "/api/months/2026-11/savings-goal"
        self.assertEqual(self.alice.put(url, json={"amount": 1000}).status_code, 401)
        self.register(self.alice, "alice")
        self.register(self.bob, "bob")
        self.assertEqual(self.alice.put(url, json={"amount": -1}).status_code, 422)
        self.assertEqual(self.alice.put(url, json={"amount": 1000}).status_code, 200)
        self.alice.put(url, json={"amount": 2000})
        self.assertEqual(self.alice.get("/api/months/2026-11/summary").json()["savings_goal"], 2000)
        self.assertEqual(self.bob.get("/api/months/2026-11/summary").json()["savings_goal"], 0)
        self.assertEqual(self.alice.get("/api/months/2026-12/summary").json()["savings_goal"], 0)
        self.assertEqual(self.alice.put("/api/months/invalid/savings-goal", json={"amount": 1}).status_code, 400)
        self.alice.delete("/api/months/2026-11")
        self.assertEqual(self.alice.get("/api/months/2026-11/summary").json()["savings_goal"], 0)

    def test_group_goal_requires_membership_and_owner_to_write(self):
        self.register(self.alice, "alice")
        self.register(self.bob, "bob")
        group = self.alice.post("/api/groups", json={"name": "Family"}).json()["id"]
        url = f"/api/months/2026-11/savings-goal?group_id={group}"
        summary = f"/api/months/2026-11/summary?group_id={group}"
        self.assertEqual(self.bob.put(url, json={"amount": 1}).status_code, 404)
        self.alice.post(f"/api/groups/{group}/invitations", json={"username": "bob"})
        self.bob.post(f"/api/invitations/{group}/accept")
        self.assertEqual(self.bob.put(url, json={"amount": 1000}).status_code, 403)
        self.assertEqual(self.alice.put(url, json={"amount": 1000}).status_code, 200)
        data = self.bob.get(summary).json()
        self.assertEqual(data["savings_goal"], 1000)
        self.assertFalse(data["can_edit_savings_goal"])
        annual = f"/api/years/2026/savings-goal?group_id={group}"
        self.assertEqual(self.bob.put(annual, json={"amount": 10000}).status_code, 403)
        self.assertEqual(self.alice.put(annual, json={"amount": 10000}).status_code, 200)
        self.assertEqual(self.bob.get(f"/api/years/2026/savings-summary?group_id={group}").json()["savings_goal"], 10000)
        self.assertEqual(self.bob.get("/api/years/2026/savings-summary?group_id=99999").status_code, 404)
        self.assertEqual(self.alice.get("/api/months/2026-11/summary").json()["savings_goal"], 0)
        self.alice.put(url, json={"amount": 0})
        self.assertEqual(self.bob.get(summary).json()["savings_goal"], 0)
