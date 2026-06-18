"""Household Energy Management System (HEMS) agent.

Owns ONLY its own devices. It never sees other households' data and cannot be
directly controlled by the grid; it only responds to broadcast prices. This is
the privacy + permission boundary that motivates a multi-agent design.

Local objective: minimize cost subject to a comfort/deadline constraint.
"""
from __future__ import annotations

from ..agents.base import Agent
from ..messages import MsgType, TrustDomain


class Household(Agent):
    accepts = (MsgType.PRICE_SIGNAL, MsgType.CURTAILMENT_REQUEST, MsgType.NACK)

    def __init__(self, name, bus, base_load, flex_kw, flex_slots_needed, deadline_slot):
        super().__init__(name, TrustDomain.CONSUMER, bus, permissions={"control:self_devices"})
        self.base_load = list(base_load)            # fixed load per slot (kW)
        self.flex_kw = flex_kw                       # flexible load magnitude (e.g. EV)
        self.flex_slots_needed = flex_slots_needed   # how many slots it must run
        self.deadline_slot = deadline_slot           # must finish by this slot
        self.assigned_slot = None                    # set by staggering, if enabled
        self.scheduled_slots: list[int] = []
        self.curtailed_kwh = 0.0

    def schedule(self, prices: list[float], stagger_slot: int | None = None) -> list[int]:
        """Pick the cheapest feasible slots for the flexible block.

        With staggering, the household is nudged toward an assigned slot to avoid
        everyone piling into the single cheapest one (rebound mitigation).
        """
        n = len(prices)
        feasible = [s for s in range(n) if s <= self.deadline_slot]
        if stagger_slot is not None and stagger_slot in feasible:
            # Honor the assigned slot first, then fill remaining by price.
            ordered = [stagger_slot] + sorted(
                [s for s in feasible if s != stagger_slot], key=lambda s: prices[s]
            )
        else:
            ordered = sorted(feasible, key=lambda s: prices[s])
        self.scheduled_slots = sorted(ordered[: self.flex_slots_needed])
        return self.scheduled_slots

    def load_at(self, slot: int) -> float:
        load = self.base_load[slot] if slot < len(self.base_load) else 0.0
        if slot in self.scheduled_slots:
            load += self.flex_kw
        return load

    def handle(self, msg) -> None:
        if msg.msg_type == MsgType.CURTAILMENT_REQUEST:
            kwh = msg.payload.get("kwh", 0.0)
            self.curtailed_kwh += kwh
