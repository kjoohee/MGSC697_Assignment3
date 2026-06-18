"""Grid (DSO) agent — the physical-feasibility authority.

Critical design point: the Grid agent is SEPARATE from the Market agent. The
market optimizes economics; the grid enforces physics. They can disagree (the
market clears a schedule the transformer cannot carry), and that disagreement is
exactly what triggers escalation. The grid never controls devices directly — it
emits constraints and, only as a last resort and only through the HITL gate,
requests curtailment.
"""
from __future__ import annotations

from ..agents.base import Agent
from ..llm import escalation_rationale
from ..messages import MsgType, TrustDomain
from ..safety.guards import HITLGate, FairnessTracker


class Grid(Agent):
    accepts = (MsgType.TELEMETRY, MsgType.CLEARING)

    def __init__(self, name, bus, feeder_capacity_kw, gate: HITLGate, fairness: FairnessTracker,
                 use_llm: bool = False):
        super().__init__(name, TrustDomain.GRID, bus,
                         permissions={"issue:constraint", "request:curtailment", "escalate"})
        self.feeder_capacity_kw = feeder_capacity_kw
        self.gate = gate
        self.fairness = fairness
        self.use_llm = use_llm
        self.escalations: list[dict] = []

    def check_feasibility(self, slot_load_kw: float) -> float:
        """Return overload in kW (0 if feasible)."""
        return max(0.0, slot_load_kw - self.feeder_capacity_kw)

    def escalate(self, *, slot, load_kw, at_price_cap, price_cap, households):
        utilization = load_kw / max(self.feeder_capacity_kw, 1e-6)
        context = {
            "feeder": self.name,
            "slot": slot,
            "load_kw": load_kw,
            "capacity_kw": self.feeder_capacity_kw,
            "utilization": utilization,
            "price_cap": price_cap,
            "at_price_cap": at_price_cap,
            "households_at_risk": len(households),
        }
        rationale = escalation_rationale(context, use_llm=self.use_llm)
        # Irreversible physical action -> must pass the human-in-the-loop gate.
        approved = self.gate.request(
            action=f"curtail feeder {self.name} @ slot {slot}",
            reversibility="irreversible",
            context=context,
        )
        record = {**context, "rationale": rationale, "approved": approved}
        self.escalations.append(record)
        return record
