# A Multi-Agent Smart-Grid Coordination System

A small but credible **multi-agent system (MAS)** that coordinates distributed
energy resources (homes, batteries, EVs, storage) on a stressed electricity
feeder. It has a **real coordination mechanism** (a hybrid market + safety
supervisor + blackboard), a **real safety story** (human-in-the-loop gate, audit
log, reversibility-classed actions, fairness-ordered curtailment), and **evidence
of how it fails** (named emergent failure modes, one of which you can trigger
from the command line and watch the mitigation work).

> This is a *prototype*, not a production grid controller. The physics are a
> transparent congestion model, not an optimal power flow, and most external
> systems are mocked. The point is to think like someone who will eventually
> build the real thing. The repo is the artifact.

---

## TL;DR — run it in 30 seconds

No third-party dependencies required (pure standard library; PyYAML used if present).

```bash
# 1. successful coordination: an overloaded feeder made feasible, nobody curtailed
python -m src.sim.run --scenario scenarios/heatwave_peak.yaml

# 2. the safety path: demand exceeds capacity -> escalate -> human approves -> fair curtailment
python -m src.sim.run --scenario scenarios/supply_shortfall.yaml

# 3. an emergent FAILURE on purpose: rebound peak from naive synchronized response
python -m src.sim.run --scenario scenarios/heatwave_peak.yaml --inject rebound

# 4. what happens when no operator is available (irreversible action is blocked)
python -m src.sim.run --scenario scenarios/supply_shortfall.yaml --no-human

# tests
python -m unittest -q
```

Optional: set `ANTHROPIC_API_KEY` and add `--use-llm` to have the Grid agent
write its escalation rationale with an LLM (it falls back to a deterministic
template otherwise, so the control path never depends on the model).

---

## 1. System brief

**Use case.** Real-time coordination of a distribution feeder during stress
events (heatwaves, generator trips). Rooftop solar, home batteries, EV charging,
and flexible loads must be coordinated against physical limits, cost, renewable
utilization, and fairness.

**Anchor scenario.** A heatwave evening: solar falls off after 18:00 just as AC
load peaks and EVs start charging on arrival home. One feeder approaches
transformer capacity. The system must shift flexible load, discharge storage, and
stay under the regulatory price cap and a fairness threshold — escalating to a
human only when physics cannot be satisfied economically.

**Stakeholders and what failure costs them.**

| Stakeholder | Objective | Cost of failure |
|---|---|---|
| Households | cheap + comfortable | blackout, loss of cooling in a heatwave (health risk to the vulnerable), bill shock |
| DSO / grid operator | physical stability | transformer overload, outage, equipment damage |
| Aggregator / VPP | monetize flexibility | contract penalties, lost revenue |
| Market operator | efficient clearing | price manipulation, market failure |
| Regulator + public | fairness, reliability, decarbonization | price gouging, discriminatory shedding, missed carbon targets |

Failure stakes are **life-safety and outage scale**, which is what justifies the
weight placed on the safety layer below.

## 2. Why MAS — why one agent is not enough

A single central agent would have to (a) hold **every household's private data**
(comfort preferences, EV schedules) — a privacy and security problem; (b) hold
**direct control authority over every device** — a single point of failure and a
huge attack surface; and (c) collapse **structurally conflicting objectives**
(margin vs. comfort vs. physical safety vs. fairness) into one objective function,
which is dishonest and untunable. Decomposition gives us privacy by construction
(homes act on local data and only respond to a broadcast price), **permission
boundaries** (the agent that proposes spending is not the agent that approves
irreversible physical action), specialization, and fault isolation.

> The single sharpest argument: for one agent to be sufficient it would need to
> centralize all private data *and* hold direct control of every device. Both are
> unacceptable, so the system must be multi-agent.

## 3. Agent roster

See [`docs/architecture.md`](docs/architecture.md) for the full table. In short:

| Agent | Responsibility | Tools (MCP boundary) | Permissions |
|---|---|---|---|
| **Household (HEMS)** | local cost/comfort optimization, responds to price | meter, HVAC/EV/water-heater, local solar+battery | `control:self_devices` only |
| **Aggregator / VPP** | bundle homes, bid to market, relay price | aggregate of homes, market API | aggregate-only sharing; cannot force a home |
| **Grid (DSO)** | enforce physical feasibility; escalate | SCADA telemetry, constraint publishing | `issue:constraint`, `escalate`; **no direct device control** |
| **Storage** | arbitrage + peak shaving | BMS | `control:self_battery` within SoC/degradation limits |
| **Market** | run price clearing under the cap | bid aggregation, clearing | `set:price` within regulatory cap |
| **Regulator + Human** | enforce cap & fairness; approve/override | policy injection, override, audit | `override:market`, `approve:curtailment` |

**Deliberate design choice:** the **Grid agent and Market agent are separate**.
The market optimizes economics; the grid enforces physics. They can disagree —
the market clears a schedule the transformer cannot carry — and that disagreement
is exactly what triggers escalation. This single separation is what makes the
coordination, emergence, and safety stories all work.

## 4. Architecture

Full diagram in [`docs/architecture.md`](docs/architecture.md). The subgraph
boundaries are the **A2A trust boundaries**; tool access inside an agent is the
**MCP boundary** (see §8).

```
Consumer domain        Market domain        Grid/DSO domain        Governance
[Households]--agg-->[Aggregator]--BID-->[Market]<--CONSTRAINT--[Grid]   [Regulator]
                                          |  PRICE_SIGNAL (broadcast)      |  + [Human]
                                          v                               ^
                                   [ Blackboard: telemetry/price/forecast ]
   Grid --ESCALATION--> Regulator --> Human --OVERRIDE/approval--> Grid
```

## 5. Communication contract

A strict message envelope (`src/messages.py`): `sender, recipient, msg_type,
trust_domain, payload, priority, confidence, correlation_id, schema_version,
msg_id, timestamp, signature`. Highlights:

- **`correlation_id`** groups one coordination round so any downstream action
  (a curtailment, an escalation) is traceable end-to-end in the audit log.
- **`signature` + `trust_domain`** matter on **A2A boundaries** (cross-org
  messages); a tampered message fails validation (`tests/test_messages.py`).
- **Malformed messages are never silently processed.** The bus validates every
  message; failures are NACK'd to the sender and parked in a **dead-letter
  queue**. Unknown recipients are rejected, not dropped.

Routing: `PRICE_SIGNAL` is **broadcast** (pub/sub via the blackboard);
`BID/CONSTRAINT/DISPATCH/ESCALATION/CURTAILMENT_REQUEST` are **direct**.
Escalation path: `Grid → Regulator → Human`. Full schema in
[`docs/communication_contract.md`](docs/communication_contract.md).

## 6. Coordination mechanism — hybrid (defended)

**Market (price auction) for economics + a hierarchical safety supervisor
(Grid/Regulator) for physics & fairness + a blackboard for shared state.**

Why not each alternative on its own:

- **Pure market/auction** — distributed, privacy-preserving, great price
  discovery (so we keep it as the first layer) — but it is blind to transformer
  limits and to fairness. Insufficient alone.
- **Pure central supervisor** — cannot scale to thousands of homes and would
  centralize all private data. Rejected — but we *do* put physics and emergency
  authority at a hierarchical top layer.
- **Pure consensus** — too slow for real-time balancing, and we need a clearing
  price, not unanimous agreement.
- **Pure contract net** — good for discrete task allocation, awkward for
  continuous price-driven DER response.
- **Pure blackboard** — great for shared state, but provides no allocation
  *decision* mechanism; kept only as the shared-state substrate.

> One-line defense: **economics via a distributed market (efficiency + privacy),
> physical safety and fairness via inviolable hierarchical constraints — two
> different mechanisms for two different concerns, on purpose.**

Details and trade-off table: [`docs/coordination.md`](docs/coordination.md).

## 7. Incentives

Each agent has a local objective that can conflict with the global one
(`docs/incentives.md`). The headline conflict, which you can watch happen:
every household locally chasing the cheapest slot produces a **new synchronized
peak** (local optima summing to a global pessimum). Alignment levers: staggered /
decorrelated price signals, ramp limits, closed-loop repricing, fairness
weighting, and paying storage for grid services so arbitrage doesn't fight peak
shaving. We also flag **Goodhart risk** (gaming a "peak reduction" baseline) and
**free-riding** by non-participants.

## 8. Interoperability — A2A vs MCP

- **MCP boundaries (agent ↔ tools/data):** a household reading its meter and
  driving its thermostat; the grid reading SCADA telemetry; storage commanding a
  BMS. These are standardized *tool/data* accesses.
- **A2A boundaries (agent ↔ agent, across trust domains):** household/aggregator
  (consumer-owned) ↔ grid (utility) ↔ market (independent operator) ↔ regulator
  (government). These are different organizations, so they need capability
  discovery, authentication, and a signed message contract — exactly the A2A
  use case. The four subgraphs in the architecture are these A2A boundaries.

More in [`docs/interoperability.md`](docs/interoperability.md).

## 9. Emergence — named, with detection and mitigation

Full table in [`docs/emergence.md`](docs/emergence.md). Each failure mode is
paired with how we detect and suppress it:

- **Rebound / "avalanche" peak** — synchronized response to one signal creates a
  *new* peak. Mitigation: staggered targets + ramp limits. **You can trigger this
  with `--inject rebound` and watch the peak oscillate vs. the staggered run.**
- **Price oscillation / limit cycle** — price up → everyone sheds → price down →
  everyone returns. Mitigation: `PriceGuard` hysteresis + ramp limit (counts its
  interventions in the trace).
- **Algorithmic collusion** — bidders converging on high prices without explicit
  communication. Mitigation: price cap + market monitoring.
- **Responsibility diffusion** — nobody escalates. Mitigation: explicit ownership
  + watchdog.
- **Discriminatory curtailment** — the same homes always cut. Mitigation:
  fairness-ordered shedding + a curtailment-Gini alarm.

## 10. Evaluation plan (agent / interaction / system / human)

Printed at the end of every run (`src/sim/run.py`), and described in
[`docs/evaluation.md`](docs/evaluation.md):

- **Agent:** comfort/deadline satisfaction, storage SoC & cycles.
- **Interaction:** messages delivered, dead-letter count, **price oscillation
  amplitude**, escalations raised.
- **System:** baseline vs. coordinated peak, peak reduction, slots over capacity,
  total curtailed, **fairness (curtailment Gini)**.
- **Human:** irreversible actions sent to a human, approvals, overrides.

## 11. Safety / governance

Full plan in [`docs/safety.md`](docs/safety.md). Core mechanisms:

- **Human-in-the-loop gate** with **reversibility classes**: reversible
  (auto), semi (auto with limits), **irreversible (requires human)**. Physical
  curtailment / brownout is irreversible, so `--no-human` blocks it and the grid
  holds at a safe fallback — the gate is a real chokepoint, demonstrated.
- **Append-only audit log** (`logs/*.jsonl`) keyed by `correlation_id` — every
  delivered message and every NACK is recorded.
- **Rollback by reversibility**: the system never auto-commits an irreversible
  action; "you cannot un-brown-out a neighborhood" is the governing principle.
- **Fairness-ordered curtailment** so shedding rotates rather than always hitting
  the same homes.
- **Abuse/failure cases** enumerated in `docs/safety.md` (sensor spoofing,
  baseline gaming, storage manipulation, agent dropout, privacy leakage).

## 12. MARL bridge — is multi-agent RL appropriate?

Short answer (full version in [`docs/marl.md`](docs/marl.md)): **not for the
system as a whole, yet.** Reasons: **non-stationarity** (every learning household
makes every other agent's environment non-stationary), a fatal sim-to-real gap
(failure = outage), the need for a high-fidelity power-flow simulator, and weak
interpretability/auditability in a regulated setting. Where it *could* fit: a
narrow, well-simulated quantitative sub-problem (e.g. storage charge/discharge
policy) trained offline in a digital twin with **CTDE** and a **safety shield**
that vetoes constraint-violating actions. Rules + market now; shielded MARL for a
narrow policy later.

---

## What is mocked vs. real

| Real (genuinely implemented) | Mocked / simplified |
|---|---|
| Message envelope, signing, validation, dead-letter | Asymmetric per-domain key material (we use one HMAC key) |
| Pub/sub + direct routing bus, append-only audit log | Network transport (in-process function calls) |
| Blackboard shared state | Persistent datastore |
| Iterative market clearing + PriceGuard (ramp/hysteresis) | Optimal power flow / real physics (we use a congestion model) |
| Household scheduling, storage SoC dispatch, fairness/Gini | Real device APIs, SCADA, BMS |
| HITL gate with reversibility classes, escalation flow | A real human (operator is modeled; `--no-human` simulates absence) |
| Emergent rebound + oscillation and their mitigations | Continuous-time grid dynamics |
| Optional real LLM call for escalation rationale | LLM in the control path (kept out by design) |

## Repository layout

```
smartgrid-mas/
├── README.md
├── requirements.txt
├── docs/                      # one file per required deliverable section
│   ├── architecture.md        # mermaid diagram + full agent roster
│   ├── communication_contract.md
│   ├── coordination.md
│   ├── emergence.md
│   ├── evaluation.md
│   ├── incentives.md
│   ├── interoperability.md
│   ├── marl.md
│   ├── safety.md
│   └── sample_runs.md
├── logs/ 
├── scenarios/                 # normal_day, heatwave_peak, failure_rebound, supply_shortfall
├── src/
│   ├── agents/                # household, aggregator, grid, storage, market, regulator
│   ├── market/clearing.py     # congestion price clearing under the cap
│   ├── safety/guards.py       # PriceGuard, FairnessTracker, HITLGate, stagger
│   ├── sim/                   # scenario loader + runner
│   ├── blackboard.py          # shared state
│   ├── bus.py                 # routing + dead-letter + append-only audit log
│   ├── llm.py                 # optional LLM hook (deterministic fallback)
│   └── messages.py            # communication contract: envelope, validation, signing
└── tests/test_messages.py
```

## Team contribution statement

_(Fill in — a few honest lines each.)_

- **Teammate A** — …
- **Teammate B** — …
- **Teammate C** — …
