# Evaluation Plan

Metrics are emitted at the end of every run (`src/sim/run.py`) at four levels.

## Agent level
- Households meeting comfort/deadline (did flexible load still complete in time?)
- Storage final SoC and number of discharge cycles (degradation proxy)
- Per-agent cost paid / revenue earned (extension point)

## Interaction level
- Messages delivered; **dead-letter (rejected) count** (protocol health)
- **Max price oscillation amplitude** round-to-round (stability)
- Escalations raised; bid acceptance rate (extension point)
- Message latency distribution (extension point in a networked version)

## System level
- Baseline vs. coordinated **peak**, and **peak reduction %**
- Slots over capacity (physical violations)
- Total curtailed (kW of firm load shed)
- **Fairness: curtailment Gini** (0 = perfectly even, alarms above threshold)
- Renewable utilization, total cost, reliability indices (SAIDI/SAIFI-like) — extensions

## Human level
- Irreversible actions routed to a human
- Approval rate; operator response time (extension)
- Regulator overrides recorded
- False-alarm rate / trust calibration (are we escalating too often?)

## How to use these for grading-style evidence

| Run | Expect |
|---|---|
| `normal_day` | low peak, 0 escalations (control) |
| `heatwave_peak` | large peak reduction (256->176), 0 curtailment (coordination alone suffices) |
| `--inject rebound` | high oscillation amplitude, peak swings (failure visible) |
| `supply_shortfall` | storage discharges, escalation=1, fair curtailment, Gini within threshold |
| `supply_shortfall --no-human` | escalation=1, **0 curtailed** (gate blocks irreversible action) |
