import unittest
from logic.safety_checker import safety_check


class SafetyTests(unittest.TestCase):
    def test_red_flag_blocks(self):
        for k in ("chest_pain", "fainting", "severe_breathlessness", "severe_acute_pain",
                  "recent_serious_injury", "professional_exercise_restriction"):
            r = safety_check({k: True})
            self.assertFalse(r["safe_to_generate"], k)
            self.assertIn(k, r["flags"])

    def test_no_flags_ok(self):
        self.assertTrue(safety_check({})["safe_to_generate"])


if __name__ == "__main__":
    unittest.main()
