# Safety & Governance Plan

## Human-in-the-loop (HITL) and reversibility classes

Every action the system can take is classified by reversibility
(`src/safety/guards.py::HITLGate`):

| Class | Examples | Handling |
|---|---|---|
| Reversible | price-band nudge, non-binding signal | auto-approved, auto-restorable |
| Semi-reversible | battery dispatch within limits | auto-approved with SoC/degradation limits |
| **Irreversible** | physical curtailment / rolling brownout, contract termination | **requires human approval; blocks if no operator** |

Demonstrated: `supply_shortfall` escalates and a modeled operator approves;
`supply_shortfall --no-human` shows the gate **deny** the irreversible action,
leaving the grid at a safe fallback with **zero** curtailment performed.

## Rollback principle

The system never auto-commits an irreversible action. Reversible actions can be
withdrawn; irreversible ones are gated before they happen, because "you cannot
un-brown-out a neighborhood." This is rollback-by-prevention.

## Audit log

`logs/audit_<scenario>.jsonl` is append-only. Every delivered message and every
NACK is recorded with a `correlation_id`, so any curtailment or escalation can be
traced back through the exact message conversation that produced it
(`AuditLog.for_correlation`).

## Observability

The runner prints the full trace: telemetry -> per-round prices -> converged
profile -> feasibility check -> escalation/rationale -> HITL decision ->
fairness-ordered curtailment -> four-level metrics -> audit excerpt.

## Abuse & failure cases (and responses)

1. **Rebound peak** — staggering + ramp limits.
2. **Price oscillation** — hysteresis + ramp limit (PriceGuard).
3. **Sensor fault / spoofed telemetry** — sanity checks, conservative fail-safe, escalate.
4. **Baseline gaming for DR payments** — baseline audit / counterfactuals.
5. **Storage market manipulation / collusion** — price cap + market monitoring.
6. **Agent dropout (aggregator offline)** — graceful degradation, safe defaults, dead-letter isolation.
7. **Escalation diffusion (nobody escalates)** — explicit ownership + watchdog.
8. **Discriminatory curtailment** — fairness ordering + Gini alarm.
9. **Privacy leakage** — data minimization; only aggregates cross the A2A boundary.
10. **Malformed/forged messages** — schema validation + signature check -> NACK + dead-letter.
