import json
import unittest
from logic.recommendation import recommend_exercises
from logic.workout_generator import build_workout
from logic.progress_tracker import streak, calculate_completion
from datetime import date, timedelta

EX = json.load(open("data/exercises.json"))


class WorkoutTests(unittest.TestCase):
    def test_fits_time_and_has_structure(self):
        p = {"goal": "mobility", "equipment": ["chair"], "difficulty": "beginner", "limitations": []}
        el, rep = recommend_exercises(p, EX)
        w = build_workout(el, p, 15, rep)
        roles = [e["role"] for e in w["exercises"]]
        self.assertEqual(roles[0], "warmup")
        self.assertEqual(roles[-1], "cooldown")
        self.assertIn("main", roles)
        self.assertLessEqual(w["estimated_minutes"], 16)
        self.assertTrue(all(e["why"] for e in w["exercises"]))

    def test_fatigue_reduces_sets(self):
        p = {"goal": "strength", "equipment": ["chair"], "difficulty": "beginner", "limitations": ["fatigue"]}
        el, _ = recommend_exercises(p, EX)
        w = build_workout(el, p, 15)
        self.assertTrue(all(e["sets"] <= 2 for e in w["exercises"]))
        self.assertTrue(all(e["rest_seconds"] == 30 for e in w["exercises"]))

    def test_streak_and_completion(self):
        t = date(2026, 10, 3)
        self.assertEqual(streak({t, t - timedelta(1), t - timedelta(2)}, t), 3)
        self.assertEqual(streak({t - timedelta(1)}, t), 1)
        self.assertEqual(streak({t - timedelta(3)}, t), 0)
        self.assertEqual(calculate_completion(1, 4), 25)


if __name__ == "__main__":
    unittest.main()
