"""Tests for the congestion price clearing (the economic half of coordination).

These turn the README/coordination claim -- "price sits at the floor below
target, rises toward the cap with congestion, and PINS at the cap once the slot
is at/over capacity (which is exactly the escalation trigger)" -- into an
executable guarantee.

Run with:  python -m pytest -q     (or)     python -m unittest -q
"""
import unittest

from src.market.clearing import clear_slot

CAP = 0.60
PRICE_CAP = CAP
CAPACITY = 200.0
TARGET = 100.0
FLOOR = 0.05


def price_for(load):
    return clear_slot(0, load, TARGET, PRICE_CAP, CAPACITY, floor=FLOOR)


class TestMarketClearing(unittest.TestCase):
    def test_floor_below_target(self):
        res = price_for(80.0)
        self.assertEqual(res.price, FLOOR)
        self.assertFalse(res.at_cap)

    def test_mid_between_floor_and_cap(self):
        res = price_for(150.0)              # halfway from target to capacity
        self.assertTrue(FLOOR < res.price < PRICE_CAP)
        self.assertFalse(res.at_cap)

    def test_pins_at_cap_at_capacity(self):
        res = price_for(CAPACITY)          # exactly at capacity
        self.assertAlmostEqual(res.price, PRICE_CAP, places=6)
        self.assertTrue(res.at_cap)        # this flag is the escalation trigger

    def test_pins_at_cap_over_capacity(self):
        res = price_for(250.0)             # over capacity
        self.assertAlmostEqual(res.price, PRICE_CAP, places=6)
        self.assertTrue(res.at_cap)

    def test_price_is_monotonic_in_load(self):
        loads = [50, 100, 120, 150, 180, 200, 250]
        prices = [price_for(x).price for x in loads]
        for a, b in zip(prices, prices[1:]):
            self.assertGreaterEqual(b, a)


if __name__ == "__main__":
    unittest.main()
