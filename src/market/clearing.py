"""Market clearing -- the economic half of the hybrid coordination mechanism.

Price for a slot is an absolute function of how loaded that slot is relative to
the feeder: at or below the soft target it sits at the floor; as load climbs
toward physical capacity the price rises linearly to the regulator's cap. When a
slot is at/above capacity the price pins to the cap -- and if it is *still*
overloaded there, economics are exhausted and the grid must escalate.

The per-round PriceGuard (ramp limit + hysteresis) smooths this signal so the
population cannot be whipped into an oscillation. This is intentionally a
transparent price-response model, not an optimal power flow; the README says so.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClearingResult:
    slot: int
    price: float
    at_cap: bool
    target_kw: float
    expected_load_kw: float


def clear_slot(
    slot: int,
    expected_load_kw: float,
    target_kw: float,
    price_cap: float,
    capacity_kw: float,
    floor: float = 0.05,
) -> ClearingResult:
    """Absolute congestion price for one slot, clamped to [floor, price_cap]."""
    if expected_load_kw <= target_kw:
        price = floor
    else:
        span = max(capacity_kw - target_kw, 1e-6)
        frac = min(1.0, (expected_load_kw - target_kw) / span)
        price = floor + (price_cap - floor) * frac
    at_cap = price >= price_cap - 1e-9
    return ClearingResult(
        slot=slot,
        price=round(price, 4),
        at_cap=at_cap,
        target_kw=target_kw,
        expected_load_kw=expected_load_kw,
    )
