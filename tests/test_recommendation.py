import json
import unittest
from logic.recommendation import recommend_exercises

EX = json.load(open("data/exercises.json"))


def names(profile):
    return {e["id"] for e in recommend_exercises(profile, EX)[0]}


class RecommendationTests(unittest.TestCase):
    def test_blocked_returns_nothing(self):
        self.assertEqual(recommend_exercises({"safety_block": True}, EX)[0], [])

    def test_equipment_filter(self):
        self.assertNotIn("seated-march", names({"equipment": []}))
        self.assertIn("seated-march", names({"equipment": ["chair"]}))

    def test_standing_limitation_removes_standing_and_wall(self):
        got = recommend_exercises({"equipment": ["chair"], "limitations": ["standing"], "difficulty": "advanced"}, EX)[0]
        self.assertTrue(got)
        self.assertFalse({e["position"] for e in got} & {"standing", "wall", "floor"})

    def test_balance_caps_to_beginner_and_blocks_unsupported_standing(self):
        got = recommend_exercises({"equipment": ["chair"], "limitations": ["balance"], "difficulty": "advanced"}, EX)[0]
        self.assertTrue(all(e["difficulty"] == "beginner" for e in got))
        self.assertNotIn("standing", {e["position"] for e in got})

    def test_upper_body_removes_upper_body_moves(self):
        self.assertNotIn("wall-push-up", names({"equipment": [], "limitations": ["upper_body"]}))


if __name__ == "__main__":
    unittest.main()
