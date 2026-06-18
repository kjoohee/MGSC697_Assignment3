"""Market agent — runs the auction/price-clearing mechanism.

It clears a price per slot under the regulator's cap and broadcasts it. It does
not know or care about physics; that separation is deliberate (see grid.py).
Prices pass through the PriceGuard before broadcast so the population cannot be
whipped into oscillation.
"""
from __future__ import annotations

from ..agents.base import Agent
from ..market.clearing import clear_slot, ClearingResult
from ..messages import MsgType, TrustDomain, Priority, new_message
from ..safety.guards import PriceGuard


class Market(Agent):
    accepts = (MsgType.BID, MsgType.CONSTRAINT)

    def __init__(self, name, bus, price_cap, capacity_kw, guards: list[PriceGuard]):
        super().__init__(name, TrustDomain.MARKET, bus, permissions={"set:price", "broadcast:price"})
        self.price_cap = price_cap
        self.capacity_kw = capacity_kw
        self.guards = guards  # one PriceGuard per slot
        self.history: list[ClearingResult] = []

    def clear(self, slot, expected_load_kw, target_kw) -> ClearingResult:
        res = clear_slot(slot, expected_load_kw, target_kw, self.price_cap, self.capacity_kw)
        guarded = self.guards[slot].apply(res.price)
        res.price = round(guarded, 4)
        res.at_cap = res.price >= self.price_cap - 1e-9 and expected_load_kw > target_kw
        self.history.append(res)
        return res

    def broadcast_price(self, slot, price, correlation_id) -> None:
        msg = new_message(
            sender=self.name,
            recipient="*",
            msg_type=MsgType.PRICE_SIGNAL,
            trust_domain=TrustDomain.MARKET,
            correlation_id=correlation_id,
            priority=Priority.NORMAL,
            payload={"slot": slot, "price": price, "cap": self.price_cap},
        )
        self.bus.publish(msg)
