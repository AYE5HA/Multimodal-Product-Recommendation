"""Regression tests for the recommender's highest-risk intent rules."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from intent import _rule_plan
from service import _catalog_color_score, _matches
from service import RecommendRequest


class RelevanceTests(unittest.TestCase):
    def test_desi_wedding_overrides_generic_formal_filter(self):
        plan = _rule_plan("desi wedding guest, not the bride", "women", "formal", 6000)
        self.assertIn("traditional", plan.intents)
        self.assertIn("wedding", plan.intents)
        self.assertEqual(plan.occasion, "wedding")
        self.assertIn("bridal", plan.negative_terms)

    def test_explicit_color_is_extracted(self):
        plan = _rule_plan("romantic white outfits", "women", None, 6000)
        self.assertEqual(plan.colors, ["white"])

    def test_non_matching_color_scores_zero(self):
        items = [{"name": "Brown satin co-ord", "description": "brown solid outfit"}]
        self.assertEqual(_catalog_color_score(items, ["white"]), 0)

    def test_gender_remains_a_hard_constraint(self):
        request = RecommendRequest(query="look", gender="women")
        self.assertFalse(_matches({"gender": "men"}, request, [{"id": "1"}]))


if __name__ == "__main__":
    unittest.main()
