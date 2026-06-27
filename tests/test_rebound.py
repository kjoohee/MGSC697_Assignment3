"""Tests for the rebound-peak mitigation (stagger_targets).

These turn the README/emergence claim -- "naive coordination tells everyone the
single cheapest slot and creates a NEW synchronized peak; staggering spreads
households across the cheap slots instead" -- into an executable guarantee.

Run with:  python -m pytest -q     (or)     python -m unittest -q
"""
import unittest
from collections import Counter

from src.safety.guards import stagger_targets


class TestStaggerTargets(unittest.TestCase):
    def test_spreads_homes_across_cheap_slots(self):
        homes = ["h%d" % i for i in range(6)]
        cheap = [1, 3]
        mapping = stagger_targets(homes, cheap)
        counts = Counter(mapping.values())
        # both cheap slots are used and the split is balanced (no pile-up)
        self.assertEqual(set(counts.keys()), {1, 3})
        self.assertLessEqual(abs(counts[1] - counts[3]), 1)

    def test_no_single_slot_pileup(self):
        # the failure mode is "everyone in one slot"; assert that never happens
        homes = ["h%d" % i for i in range(8)]
        cheap = [0, 2, 4]
        mapping = stagger_targets(homes, cheap)
        counts = Counter(mapping.values())
        self.assertGreater(len(counts), 1)
        self.assertLess(max(counts.values()), len(homes))

    def test_deterministic(self):
        homes = ["b", "a", "c", "d"]
        cheap = [1, 5]
        self.assertEqual(stagger_targets(homes, cheap),
                         stagger_targets(homes, cheap))

    def test_empty_cheap_slots_returns_empty(self):
        self.assertEqual(stagger_targets(["a", "b"], []), {})


if __name__ == "__main__":
    unittest.main()
