# Sample Runs (worked scenarios)

Four runs, each isolating one capability. All outputs below are real console
output from `src/sim/run.py`. UUID `correlation_id`s differ per run by design.

| # | Command | What it proves | Rubric target |
|---|---|---|---|
| 1 | `heatwave_peak` | coordination alone fixes an overloaded feeder; nobody curtailed | Coordination (6), Prototype (5) |
| 2 | `heatwave_peak --inject rebound` | a **named emergent failure** (rebound oscillation) appears when mitigation is off | Coordination (6), Eval/Safety (6) |
| 3 | `supply_shortfall` | full safety path: escalate → **human approves** → fairness-ordered curtailment | Eval/Safety (6) |
| 4 | `supply_shortfall --no-human` | HITL gate **blocks** an irreversible action when no operator is available | Eval/Safety (6) |

**How to read the contrast that matters most:** runs 1 and 2 are the *same
scenario*; the only difference is rebound mitigation (staggering). Run 1 holds a
flat 176 kW peak across all rounds; run 2 oscillates (192 → 224 → 256 → 224 →
256 → 224 kW) and only reaches a +12% reduction vs. +31%. That is the emergent
failure, and the mitigation, shown side by side.

---

## Run 1 — `heatwave_peak`  (success: coordination suffices)

```
py -m src.sim.run --scenario scenarios/heatwave_peak.yaml
```

**Look for:** baseline 256 kW with 2 slots over capacity → coordinated 176 kW,
0 slots over, 0 curtailment, 0 escalations. Peak reduction +31%.

```
========================================================================
SMART-GRID MAS  |  scenario: heatwave_peak
========================================================================
slots=6  feeder_capacity=230.0kW  target=180.0kW  price_cap=0.6
stagger(rebound mitigation)=ON  use_llm=OFF  human_available=YES

STEP 1 — Telemetry / baseline (uncoordinated, convenience-driven)
  slot    16h    17h    18h    19h    20h    21h
  load     88    104    136    256    240    104
  baseline peak = 256 kW  (capacity 230 kW)  -- 2 slot(s) OVER CAPACITY

STEP 2 — Iterative market coordination (price <-> demand response)
  round   peak     prices ($/kWh per slot)
      1    176kW   [0.05 0.05 0.05 0.05 0.05 0.05]
      ...  (flat 176 kW every round)
      6    176kW   [0.05 0.05 0.05 0.05 0.05 0.05]
  PriceGuard intervened 30 times (ramp-limit / hysteresis)

STEP 3 — Converged load profile
  slot    16h    17h    18h    19h    20h    21h
  load    176    170    158    168    152    104
  baseline peak = 256 kW  ->  coordinated peak = 176 kW

STEP 4 — Grid checks physics; escalate if market cannot solve
  (no overload; nothing to escalate)

METRICS
  AGENT        households meeting comfort/deadline : 8/8
  INTERACTION  messages delivered : 36   escalations raised : 0
  SYSTEM       baseline 256 kW -> coordinated 176 kW   peak reduction : +31%
               slots over capacity (final) : 0   total curtailed : 0 kW
               fairness (Gini) : 0.00 (within threshold)
  HUMAN        irreversible actions sent to human : 0
```

**Reading:** the market + staggering flatten a 256 kW convenience-driven peak to
176 kW within physical limits, with no curtailment and no human involvement. This
is the system working as intended in steady stress.

---

## Run 2 — `heatwave_peak --inject rebound`  (emergent failure exposed)

```
py -m src.sim.run --scenario scenarios/heatwave_peak.yaml --inject rebound
```

**Look for:** identical scenario, but `stagger=OFF`. The peak **oscillates** round
to round and the reduction collapses to +12%.

```
stagger(rebound mitigation)=OFF  use_llm=OFF  human_available=YES

STEP 2 — Iterative market coordination
  round   peak     prices ($/kWh per slot)
      1    192kW   [0.05 0.18 0.05 0.05 0.05 0.05]
      2    224kW   [0.05 0.15 0.06 0.05 0.05 0.05]
      3    256kW   [0.05 0.12 0.05 0.06 0.05 0.05]
      4    224kW   [0.05 0.09 0.06 0.05 0.05 0.05]
      5    256kW   [0.05 0.07 0.05 0.06 0.05 0.05]
      6    224kW   [0.05 0.06 0.06 0.05 0.05 0.05]
  PriceGuard intervened 26 times (ramp-limit / hysteresis)

STEP 3 — Converged load profile
  baseline peak = 256 kW  ->  coordinated peak = 224 kW
  [!] rebound mitigation OFF: synchronized response can pile load into the cheapest slot

METRICS
  INTERACTION  max price oscillation (round-to-round) : 0.036 $/kWh
  SYSTEM       peak reduction : +12%   (vs +31% with mitigation on)
```

**Reading:** with households responding to the same signal in lockstep, every home
chases the same cheap slot and creates a *new* synchronized peak — the rebound /
limit-cycle failure named in `docs/emergence.md`. The fix (staggered targets +
ramp limits) is exactly what Run 1 has on. Same scenario, mitigation toggled: the
emergent behavior and its remedy are both demonstrated.

---

## Run 3 — `supply_shortfall`  (full safety path, human approves)

```
py -m src.sim.run --scenario scenarios/supply_shortfall.yaml
```

**Look for:** even after storage discharges 40 kW, 19h stays over capacity at the
price cap → escalation → **human approves** → 11 kW shed in fairness order (3 kW
each across 4 homes).

```
STEP 3 — Converged load profile
  storage discharge per slot:    0     0    40     0     0  (final SoC=46%, 1 discharges)
  baseline peak = 249 kW  ->  coordinated peak = 161 kW

STEP 4 — Grid checks physics; escalate if market cannot solve
  slot 19h: OVERLOAD 11 kW (load 161 > cap 150), price=0.60 [AT CAP]
    -> ESCALATION to human. rationale: Feeder 'feeder_3' projected at 161 kW against
       a 150 kW limit (107% utilization). Market price reached the regulatory cap of
       0.6 without clearing the overload. Economic signals are exhausted; human
       authorization is required for physical curtailment affecting 6 households.
    -> HITL gate (human approval) = APPROVED
      curtail home_01: -3 kW (firm/brownout, fairness-ordered)
      curtail home_02: -3 kW (firm/brownout, fairness-ordered)
      curtail home_03: -3 kW (firm/brownout, fairness-ordered)
      curtail home_04: -3 kW (firm/brownout, fairness-ordered)

METRICS
  SYSTEM  peak reduction : +35%   total curtailed : 11 kW   fairness (Gini) : 0.00
  HUMAN   irreversible actions sent to human : 1   approved by human : 1

AUDIT TRACE
    [DELIVER] feeder_3 -> regulator : ESCALATION {'slot': 2, 'overload_kw': 11.0}
    [DELIVER] feeder_3 -> home_01 : CURTAILMENT_REQUEST {'kwh': 2.75, 'kind': 'firm/brownout'}
    ... (one per curtailed home)
```

**Reading:** Gini = 0.00 here means the curtailment was split *perfectly evenly*
(equal cuts = no inequality), well within the 0.40 alarm threshold. Storage,
escalation, human approval, fairness, and the audit trail are all exercised in one
episode.

---

## Run 4 — `supply_shortfall --no-human`  (irreversible action blocked)

```
py -m src.sim.run --scenario scenarios/supply_shortfall.yaml --no-human
```

**Look for:** same overload and escalation, but with no operator available the HITL
gate **denies** the irreversible curtailment — the grid holds at a safe fallback
and **0 kW is shed**.

```
stagger(rebound mitigation)=ON  use_llm=OFF  human_available=NO

STEP 4 — Grid checks physics; escalate if market cannot solve
  slot 19h: OVERLOAD 11 kW (load 161 > cap 150), price=0.60 [AT CAP]
    -> ESCALATION to human. rationale: ...human authorization is required...
    -> HITL gate (human approval) = DENIED
    -> not approved: grid holds at safe fallback, no curtailment performed

METRICS
  SYSTEM  total curtailed : 0 kW
  HUMAN   irreversible actions sent to human : 1   approved by human : 0
```

**Reading:** this is the safety property made concrete. An irreversible action
(firm load shedding / rolling brownout) cannot be taken without explicit human
authorization. When the human is absent, the system refuses to act unilaterally —
"you cannot un-brown-out a neighborhood," so it must not happen automatically.

---

## Summary of evidence

| Capability | Demonstrated in |
|---|---|
| Market coordination flattening a peak | Run 1 (256 → 176 kW) |
| Named emergent failure + its mitigation | Run 1 vs Run 2 (rebound oscillation) |
| PriceGuard suppressing oscillation | all runs (intervention counts) |
| Storage dispatch (peak shaving) | Run 3/4 (40 kW discharge, SoC 90% → 46%) |
| Escalation when economics are exhausted | Run 3/4 (overload at price cap) |
| Human-in-the-loop approval | Run 3 (approved) |
| HITL gate blocking irreversible action | Run 4 (denied → 0 kW shed) |
| Fairness-ordered curtailment + Gini | Run 3 (even 3 kW cuts, Gini 0.00) |
| Audit trace by correlation_id | Run 3/4 (ESCALATION + CURTAILMENT logged) |
```
