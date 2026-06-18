# Emergence

Multi-agent systems produce behavior no single agent was programmed to produce.
We name each expected failure mode, how it arises, how we detect it, and how we
mitigate it. Two of these are demonstrable from the command line.

## Unwanted emergence

| Name | Mechanism | Detection | Mitigation | Demo |
|---|---|---|---|---|
| Rebound / "avalanche" peak | every home shifts flexible load to the same cheapest slot, creating a NEW synchronized peak (local optima sum to a global pessimum) | peak appears in a slot that was previously cheap; peak variance across rounds | `stagger_targets` decorrelates households across cheap slots; ramp limits | `--inject rebound` vs default |
| Price oscillation / limit cycle | price up -> all shed -> price down -> all return -> repeat | round-to-round price swing amplitude metric | `PriceGuard` hysteresis (ignore tiny changes) + ramp limit (clamp big ones) | guard interventions printed in trace |
| Algorithmic collusion | storage/prosumer bidders learn to keep prices high without explicit communication | sustained near-cap prices with low volume | regulatory price cap + market monitoring | cap enforced in `clearing.py` |
| Responsibility diffusion | each agent assumes another escalated; nobody does | missing ESCALATION when overload + at-cap | explicit ownership (Grid owns escalation) + watchdog/heartbeat | escalation is unconditional in `run.py` |
| Discriminatory curtailment | the same homes are always shed first | curtailment-Gini above threshold | fairness-ordered shedding (least-curtailed first) + Gini alarm | `FairnessTracker`, shortfall scenario |
| Cascading dropout | one agent fails -> others overreact -> more failures | telemetry gaps, NACK spikes | graceful degradation + safe defaults + dead-letter isolation | bus dead-letter queue |

## Wanted (designed-for) emergence

- **Self-flattening load:** independent price responses, once decorrelated,
  produce a smooth aggregate profile no one dictated (heatwave run: 256 kW -> 176 kW).
- **Graceful degradation:** non-critical/flexible load yields before firm load;
  irreversible firm shedding is the last resort and gated by a human.
- **VPP aggregation:** many small flexibilities behave as one dispatchable resource.

## The headline demonstration

```
# mitigation ON  (staggered): peak is flat across rounds
python -m src.sim.run --scenario scenarios/heatwave_peak.yaml

# mitigation OFF (synchronized): peak oscillates round to round -> the rebound
python -m src.sim.run --scenario scenarios/heatwave_peak.yaml --inject rebound
```
