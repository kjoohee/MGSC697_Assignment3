"""Regulator + Human-in-the-loop agent.

Holds the governance constraints (price cap, fairness threshold) and is the
endpoint of escalations. The "human" is modeled as an approval authority for
irreversible actions; in production this is a real person and the HITLGate blocks
on their decision. The regulator can also override the market (stop trading /
force the cap) — modeled here as a recorded authority.
"""
from __future__ import annotations

from ..agents.base import Agent
from ..messages import MsgType, TrustDomain


class Regulator(Agent):
    accepts = (MsgType.ESCALATION,)

    def __init__(self, name, bus, price_cap, fairness_gini_threshold=0.4):
        super().__init__(name, TrustDomain.GOVERNANCE, bus,
                         permissions={"set:price_cap", "override:market", "approve:curtailment"})
        self.price_cap = price_cap
        self.fairness_gini_threshold = fairness_gini_threshold
        self.overrides: list[dict] = []

    def review_fairness(self, gini: float) -> bool:
        """Return True if a fairness breach requires intervention."""
        breach = gini > self.fairness_gini_threshold
        if breach:
            self.overrides.append({"type": "fairness_breach", "gini": gini})
        return breach
