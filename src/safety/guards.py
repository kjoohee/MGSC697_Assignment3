"""Safety guards — the supervisor overlay that sits above the market.

These are the mechanisms that turn "named failure modes" (see docs/emergence.md)
into runtime protections:

  - PriceGuard      : ramp limit + hysteresis  -> prevents price oscillation / limit cycles
  - FairnessTracker : per-household curtailment + Gini -> prevents discriminatory shedding
  - HITLGate        : irreversible actions require human approval -> rollback safety
  - stagger_targets : spreads load shifting -> prevents the synchronized rebound peak

Every guard is observable: it records what it did and why, which is what the
audit log and evaluation metrics consume.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PriceGuard:
    """Damps price changes so the market cannot oscillate the whole population."""
    max_ramp: float = 0.20          # max fractional change per round
    hysteresis_band: float = 0.05   # ignore changes smaller than this (anti-chatter)
    last_price: float | None = None
    events: list[str] = field(default_factory=list)

    def apply(self, proposed: float) -> float:
        if self.last_price is None:
            self.last_price = proposed
            return proposed
        change = (proposed - self.last_price) / max(self.last_price, 1e-6)
        if abs(change) < self.hysteresis_band:
            self.events.append(f"hysteresis: ignored {change:+.1%} change, hold {self.last_price:.3f}")
            return self.last_price
        clamped = max(-self.max_ramp, min(self.max_ramp, change))
        if clamped != change:
            self.events.append(f"ramp-limit: {change:+.1%} clamped to {clamped:+.1%}")
        new_price = self.last_price * (1 + clamped)
        self.last_price = new_price
        return new_price


@dataclass
class FairnessTracker:
    """Tracks cumulative curtailment per household and prefers least-curtailed first."""
    curtailment: dict[str, float] = field(default_factory=dict)

    def record(self, household: str, kwh: float) -> None:
        self.curtailment[household] = self.curtailment.get(household, 0.0) + kwh

    def order_by_fairness(self, households: list[str]) -> list[str]:
        # Curtail those who have been curtailed least so far, first.
        return sorted(households, key=lambda h: self.curtailment.get(h, 0.0))

    def gini(self) -> float:
        vals = sorted(self.curtailment.values())
        n = len(vals)
        if n == 0 or sum(vals) == 0:
            return 0.0
        cum = 0.0
        for i, v in enumerate(vals, start=1):
            cum += i * v
        return (2 * cum) / (n * sum(vals)) - (n + 1) / n


@dataclass
class HITLGate:
    """Gate for irreversible / high-impact actions.

    Reversibility classes:
      reversible    -> auto-approved (e.g. price-band nudge)
      semi          -> auto-approved with limits (e.g. battery dispatch)
      irreversible  -> REQUIRES human approval (e.g. physical curtailment / brownout)
    """
    auto_approve_human: bool = True   # simulate an available operator who approves
    decisions: list[dict] = field(default_factory=list)

    def request(self, action: str, reversibility: str, context: dict) -> bool:
        if reversibility in ("reversible", "semi"):
            approved = True
            via = "auto"
        else:
            # Irreversible: must pass through a human. In this sim the operator
            # is modeled; in production this blocks on a real approval.
            approved = self.auto_approve_human
            via = "human"
        self.decisions.append(
            {"action": action, "reversibility": reversibility, "approved": approved,
             "via": via, "context": context}
        )
        return approved


def stagger_targets(households: list[str], cheap_slots: list[int]) -> dict[str, int]:
    """Assign each household a *different* target slot to prevent a rebound peak.

    Naive coordination tells everyone the single cheapest slot, so everyone shifts
    there and creates a new synchronized peak. Staggering deterministically spreads
    households across the cheap slots instead.
    """
    if not cheap_slots:
        return {}
    return {h: cheap_slots[i % len(cheap_slots)] for i, h in enumerate(sorted(households))}
