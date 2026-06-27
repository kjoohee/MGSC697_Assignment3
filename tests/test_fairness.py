"""Tests for fairness-ordered curtailment and the curtailment-Gini metric.

These turn the README/safety claim -- "shedding rotates rather than always
hitting the same homes, and we alarm on a fairness (Gini) breach" -- into an
executable guarantee. The expected Gini values are hand-computed from the
formula in FairnessTracker.gini() so the test is self-checking, not circular.

Run with:  python -m pytest -q     (or)     python -m unittest -q
"""
import unittest

from src.safety.guards import FairnessTracker


class TestGini(unittest.TestCase):
    def test_gini_empty_is_zero(self):
        self.assertEqual(FairnessTracker().gini(), 0.0)

    def test_gini_equal_distribution_is_zero(self):
        ft = FairnessTracker()
        for name in ("a", "b", "c"):
            ft.record(name, 2.0)
        self.assertAlmostEqual(ft.gini(), 0.0, places=6)

    def test_gini_known_vector(self):
        # vals=[1,2,3]: cum=1*1+2*2+3*3=14, sum=6, n=3
        # gini = 2*14/(3*6) - 4/3 = 28/18 - 4/3 = 0.2222...
        ft = FairnessTracker()
        ft.record("a", 1.0)
        ft.record("b", 2.0)
        ft.record("c", 3.0)
        self.assertAlmostEqual(ft.gini(), 2.0 / 9.0, places=6)

    def test_gini_concentrated_higher_than_spread(self):
        spread = FairnessTracker()
        for name, kwh in (("a", 1.0), ("b", 2.0), ("c", 3.0)):
            spread.record(name, kwh)
        concentrated = FairnessTracker()
        for name, kwh in (("a", 0.0), ("b", 0.0), ("c", 6.0)):
            concentrated.record(name, kwh)
        self.assertGreater(concentrated.gini(), spread.gini())


class TestFairnessOrdering(unittest.TestCase):
    def test_least_curtailed_first(self):
        ft = FairnessTracker()
        ft.record("a", 5.0)
        ft.record("b", 1.0)
        ft.record("c", 3.0)
        self.assertEqual(ft.order_by_fairness(["a", "b", "c"]), ["b", "c", "a"])

    def test_unrecorded_home_is_treated_as_zero(self):
        ft = FairnessTracker()
        ft.record("a", 5.0)
        # "new" was never curtailed -> should be first in line
        self.assertEqual(ft.order_by_fairness(["a", "new"])[0], "new")

    def test_curtailment_rotates(self):
        ft = FairnessTracker()
        ft.record("a", 5.0)
        ft.record("b", 1.0)
        ft.record("c", 3.0)
        first = ft.order_by_fairness(["a", "b", "c"])[0]  # "b"
        ft.record(first, 5.0)  # curtail the one we just picked
        # after rotation, the previously-least home is no longer first
        self.assertNotEqual(ft.order_by_fairness(["a", "b", "c"])[0], first)


if __name__ == "__main__":
    unittest.main()
