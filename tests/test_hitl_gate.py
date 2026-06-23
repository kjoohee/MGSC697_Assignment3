"""Tests for the human-in-the-loop gate (reversibility-classed approvals).

These turn the README/safety claim -- "irreversible actions require a human, and
when no operator is available the irreversible action is blocked" -- into an
executable guarantee.

Run with:  python -m pytest -q     (or)     python -m unittest -q
"""
import unittest

from src.safety.guards import HITLGate


class TestHITLGate(unittest.TestCase):
    def test_reversible_auto_approved(self):
        gate = HITLGate(auto_approve_human=True)
        self.assertTrue(gate.request("price nudge", "reversible", {}))
        self.assertEqual(gate.decisions[-1]["via"], "auto")

    def test_semi_auto_approved(self):
        gate = HITLGate(auto_approve_human=True)
        self.assertTrue(gate.request("battery dispatch", "semi", {}))
        self.assertEqual(gate.decisions[-1]["via"], "auto")

    def test_irreversible_takes_human_path(self):
        gate = HITLGate(auto_approve_human=True)  # operator present and approves
        approved = gate.request("brownout", "irreversible", {"slot": 2})
        self.assertTrue(approved)
        self.assertEqual(gate.decisions[-1]["via"], "human")

    def test_irreversible_blocked_when_no_human(self):
        # The --no-human path: no operator available must block irreversible action.
        gate = HITLGate(auto_approve_human=False)
        approved = gate.request("brownout", "irreversible", {"slot": 2})
        self.assertFalse(approved)
        self.assertEqual(gate.decisions[-1]["via"], "human")

    def test_no_human_still_allows_reversible(self):
        # Absence of a human must not block low-risk reversible/semi actions.
        gate = HITLGate(auto_approve_human=False)
        self.assertTrue(gate.request("price nudge", "reversible", {}))
        self.assertTrue(gate.request("battery dispatch", "semi", {}))

    def test_every_decision_is_recorded(self):
        gate = HITLGate(auto_approve_human=True)
        gate.request("a", "reversible", {})
        gate.request("b", "irreversible", {})
        self.assertEqual(len(gate.decisions), 2)
        for d in gate.decisions:
            self.assertIn("action", d)
            self.assertIn("reversibility", d)
            self.assertIn("approved", d)
            self.assertIn("via", d)


if __name__ == "__main__":
    unittest.main()
