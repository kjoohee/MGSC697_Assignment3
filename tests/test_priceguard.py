"""Tests for PriceGuard (ramp limit + hysteresis).

These turn the README/emergence claim -- "PriceGuard damps price changes so the
market cannot whip the whole population into an oscillation / limit cycle" --
into an executable guarantee.

Run with:  python -m pytest -q     (or)     python -m unittest -q
"""
import unittest

from src.safety.guards import PriceGuard


class TestPriceGuard(unittest.TestCase):
    def test_first_apply_passes_through(self):
        g = PriceGuard()
        self.assertEqual(g.apply(0.30), 0.30)
        self.assertEqual(g.last_price, 0.30)

    def test_hysteresis_holds_small_change(self):
        g = PriceGuard(max_ramp=0.20, hysteresis_band=0.05)
        g.apply(1.00)                      # seed last_price
        out = g.apply(1.02)                # +2% < 5% band -> ignored
        self.assertEqual(out, 1.00)
        self.assertTrue(any("hysteresis" in e for e in g.events))

    def test_ramp_limit_clamps_large_change(self):
        g = PriceGuard(max_ramp=0.20, hysteresis_band=0.05)
        g.apply(1.00)                      # seed last_price
        out = g.apply(2.00)                # +100% requested -> clamp to +20%
        self.assertAlmostEqual(out, 1.20, places=6)
        self.assertTrue(any("ramp-limit" in e for e in g.events))

    def test_sawtooth_input_does_not_full_swing(self):
        # Feed a violent alternating signal; every accepted step must stay within
        # the ramp limit, so the output can never complete a full-amplitude swing
        # round to round -> no limit cycle.
        g = PriceGuard(max_ramp=0.20, hysteresis_band=0.05)
        g.apply(0.50)
        outputs = [0.50]
        for _ in range(10):
            outputs.append(g.apply(2.00))
            outputs.append(g.apply(0.10))
        for prev, cur in zip(outputs, outputs[1:]):
            frac = abs(cur - prev) / max(prev, 1e-6)
            self.assertLessEqual(frac, 0.20 + 1e-9)


if __name__ == "__main__":
    unittest.main()
