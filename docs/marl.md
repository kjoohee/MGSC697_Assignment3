# MARL Bridge — is multi-agent RL appropriate?

## Verdict
**Not for the system as a whole, at least not now.** Use rules + market +
explicit coordination today; consider MARL only for a narrow, well-simulated
sub-problem later, wrapped in a safety shield.

## Why MARL is the wrong tool for the whole system here
- **Non-stationarity:** as each household's policy learns, every other agent's
  environment becomes non-stationary, so convergence and stability are not
  guaranteed — dangerous for a physical grid.
- **Sim-to-real gap is fatal:** the cost of a bad exploratory action is a real
  outage. You cannot train online on a live feeder.
- **Needs a high-fidelity simulator:** credible training requires a power-flow
  digital twin we do not have in a prototype.
- **Interpretability / auditability:** regulators need to know *why* load was
  shed. A learned black-box policy is hard to audit; our rule + market + HITL
  pipeline is traceable by `correlation_id`.
- **Credit assignment & sample efficiency:** attributing a system outcome to one
  agent's action is hard and data-hungry.

## Where MARL *could* fit later
A narrow quantitative sub-problem with a clear reward and a good simulator — e.g.
**storage charge/discharge timing** or **HVAC pre-cooling** policy. Recommended
shape:
- **Offline training in a digital twin**, never online on the live grid.
- **CTDE** (centralized training, decentralized execution).
- **Safe RL / action shielding:** a hard safety layer vetoes any action that
  would violate physical constraints — i.e. the same Grid-agent veto we already
  have, used as the shield.

## One-line summary
> Rules and a market now; a shielded, offline-trained MARL policy for one narrow
> dispatch decision later. Handing whole-system coordination to MARL is
> inappropriate because of non-stationarity, interpretability, and safety.
