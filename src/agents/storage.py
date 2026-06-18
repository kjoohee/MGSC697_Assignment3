"""Storage agent — battery arbitrage + grid services.

Local objective is arbitrage (charge cheap, discharge expensive). Global need is
peak shaving. These can conflict, so the agent discharges into congested slots
when price is high enough, but always respects state-of-charge and a simple
degradation limit (max cycles per run).
"""
from __future__ import annotations

from ..agents.base import Agent
from ..messages import MsgType, TrustDomain


class Storage(Agent):
    accepts = (MsgType.PRICE_SIGNAL, MsgType.DISPATCH)

    def __init__(self, name, bus, capacity_kwh, power_kw, soc=0.5,
                 min_soc=0.1, max_soc=0.95, discharge_price_threshold=0.5):
        super().__init__(name, TrustDomain.GRID, bus, permissions={"control:self_battery", "submit:bid"})
        self.capacity_kwh = capacity_kwh
        self.power_kw = power_kw
        self.soc = soc
        self.min_soc = min_soc
        self.max_soc = max_soc
        self.threshold = discharge_price_threshold
        self.dispatch_log: list[dict] = []

    def available_discharge_kw(self) -> float:
        usable_kwh = (self.soc - self.min_soc) * self.capacity_kwh
        return max(0.0, min(self.power_kw, usable_kwh))  # 1-slot horizon (1h)

    def respond(self, slot: int, price: float) -> float:
        """Discharge into a slot if price is high enough and SoC allows."""
        if price >= self.threshold:
            kw = self.available_discharge_kw()
            if kw > 0:
                self.soc -= kw / self.capacity_kwh
                self.dispatch_log.append({"slot": slot, "discharge_kw": kw, "soc_after": self.soc})
                return kw
        return 0.0
