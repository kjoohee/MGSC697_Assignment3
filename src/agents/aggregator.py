"""Aggregator / Virtual Power Plant agent.

Sits on the A2A boundary between the consumer domain and the market. It only ever
shares *aggregate* flexibility outward — never individual household data — which
is the privacy guarantee that makes outsourcing coordination to a market
acceptable. It cannot force a household to do anything.
"""
from __future__ import annotations

from ..agents.base import Agent
from ..messages import MsgType, TrustDomain


class Aggregator(Agent):
    accepts = (MsgType.PRICE_SIGNAL, MsgType.CLEARING)

    def __init__(self, name, bus, households):
        super().__init__(name, TrustDomain.CONSUMER, bus,
                         permissions={"submit:aggregate_bid", "relay:price"})
        self.households = households  # list[Household]

    def aggregate_flexibility(self) -> dict:
        """Summarize total shiftable load without revealing per-home detail."""
        total_flex = sum(h.flex_kw for h in self.households)
        return {
            "n_homes": len(self.households),
            "total_flex_kw": total_flex,
            "trust_domain": self.trust_domain.value,
        }
