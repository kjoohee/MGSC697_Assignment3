# Incentive Analysis

## Local objectives vs. the global objective

| Agent | Local objective | Conflicts with global when... |
|---|---|---|
| Household | minimize bill s.t. comfort/deadline | everyone chases the same cheap slot -> synchronized rebound peak |
| Storage | arbitrage (charge cheap, discharge dear) | the most profitable discharge time is not the time the grid needs support |
| Aggregator | maximize flexibility revenue | over-committing flexibility it cannot actually deliver |
| Market | clear efficiently | efficient price can still be physically infeasible or unfair |
| Grid | physical safety | safest action (shed load) is costly and unfair if always the same homes |

**Global objective:** keep the feeder within physical limits, minimize cost,
maximize renewable utilization, and keep curtailment fair and decarbonization on
track.

## The central misalignment

Each household optimizing locally is individually rational but collectively
produces a **new peak** — the classic local-optimum / global-pessimum failure.
This is *emergent*, not a bug in any one agent.

## Alignment levers (mechanism design)

- **Decorrelated price signals** (`stagger_targets`) so responses don't synchronize.
- **Ramp limits + hysteresis** (`PriceGuard`) so the population can't be whipped.
- **Closed-loop repricing** so the price reflects the load it just caused.
- **Pay storage for grid services** (ancillary value), not only arbitrage, so
  peak shaving and profit point the same direction.
- **Fairness weighting** in curtailment so the cost of last-resort actions rotates.

## Failure-of-incentives to watch

- **Goodhart / reward hacking:** if homes are paid for "reduction vs. baseline",
  they may inflate the baseline. -> audit baselines, use counterfactual estimates.
- **Free-riding:** non-participants still enjoy a stable grid. -> participation
  incentives / tariff design.
- **Principal-agent gap:** the aggregator's revenue motive can diverge from both
  the household's comfort and the grid's safety. -> aggregate-only authority +
  the grid retains veto.
