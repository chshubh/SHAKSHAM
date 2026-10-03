import os, re, tempfile, unittest

os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")
import app as shaksham  # noqa: E402


def token(client, path="/login"):
    html = client.get(path).get_data(as_text=True)
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return m.group(1)


FORM = {"age_group": "30-44", "experience": "beginner", "activity_level": "light", "duration": "15",
        "equipment": ["chair"], "goal": "strength", "limitations": ["none"], "health_status": "good",
        "injury_status": "none", "professional_restriction": "no", "confirm": "1"}


class AppTests(unittest.TestCase):
    def setUp(self):
        self.c = shaksham.app.test_client()

    def login(self):
        t = token(self.c)
        return self.c.post("/login", data={"csrf_token": t, "email": "demo@shaksham.app", "password": "Demo@1234"}, follow_redirects=True)

    def test_public_pages(self):
        for p in ["/", "/login", "/register", "/exercises", "/exercises?category=balance", "/exercise/seated-march"]:
            self.assertEqual(self.c.get(p).status_code, 200, p)
        self.assertEqual(self.c.get("/exercise/nope").status_code, 404)

    def test_protected_redirect(self):
        self.assertEqual(self.c.get("/dashboard").status_code, 302)

    def test_csrf_required(self):
        self.assertEqual(self.c.post("/login", data={"email": "a@b.c", "password": "x"}).status_code, 400)

    def test_demo_login_and_pages(self):
        r = self.login()
        self.assertIn(b"Start workout", r.data)
        for p in ["/dashboard", "/progress", "/achievements", "/profile", "/assessment"]:
            self.assertEqual(self.c.get(p).status_code, 200, p)

    def test_register_assessment_workout_flow(self):
        t = token(self.c, "/register")
        r = self.c.post("/register", data={"csrf_token": t, "name": "Asha Rao", "email": "asha@example.com", "password": "longenough1"}, follow_redirects=True)
        self.assertIn(b"Step 1 of 5", r.data)
        self.assertNotIn(b"checked", r.data.split(b'name="age_group"')[1][:200])
        t = token(self.c, "/assessment")
        r = self.c.post("/assessment", data={**FORM, "csrf_token": t}, follow_redirects=True)
        self.assertIn(b"Start workout", r.data)
        pid = int(re.search(rb"/workout/(\d+)", r.data).group(1))
        self.assertEqual(self.c.get(f"/workout/{pid}").status_code, 200)
        h = {"X-CSRF-Token": t}
        r = self.c.post(f"/workout/{pid}/feedback", json={"exercise": "seated-march", "rating": "easy"}, headers=h)
        self.assertTrue(r.get_json()["ok"])
        r = self.c.post(f"/workout/{pid}/complete", json={"duration_seconds": 600, "completed": True}, headers=h)
        self.assertTrue(r.get_json()["recorded"])
        self.assertIn("First Step", r.get_json()["achievements"])

    def test_red_flag_blocks_plan(self):
        t = token(self.c, "/register")
        self.c.post("/register", data={"csrf_token": t, "name": "Ben", "email": "ben@example.com", "password": "longenough1"})
        t = token(self.c, "/assessment")
        r = self.c.post("/assessment", data={**FORM, "csrf_token": t, "symptoms": ["chest_pain"]}, follow_redirects=True)
        self.assertIn(b"paused your workout plan", r.data)
        self.assertNotIn(b"Start workout", r.data)

    def test_pain_feedback_flags_session(self):
        self.login()
        t = token(self.c, "/dashboard") if False else self.c.get("/dashboard").get_data(as_text=True)
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', t).group(1)
        pid = int(re.search(r"/workout/(\d+)", t).group(1))
        h = {"X-CSRF-Token": csrf}
        r = self.c.post(f"/workout/{pid}/feedback", json={"exercise": "seated-march", "rating": "pain"}, headers=h)
        self.assertTrue(r.get_json()["stop"])
        self.c.post(f"/workout/{pid}/complete", json={"duration_seconds": 90, "completed": False}, headers=h)
        self.assertIn(b"ended early", self.c.get("/dashboard").data)

    def test_validation_errors(self):
        t = token(self.c, "/register")
        self.c.post("/register", data={"csrf_token": t, "name": "Cy", "email": "cy@example.com", "password": "longenough1"})
        t = token(self.c, "/assessment")
        r = self.c.post("/assessment", data={"csrf_token": t, "goal": "strength"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
