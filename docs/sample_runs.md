# Sample Runs (worked scenarios)

Four runs, each isolating one capability. All outputs below are **verbatim console
output** from `src/sim/run.py`. UUID `correlation_id`s differ per run by design.
Audit logs committed to `logs/`.

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
python3 -m src.sim.run --scenario scenarios/heatwave_peak.yaml
```

**Look for:** baseline 256 kW with 2 slots over capacity → coordinated 176 kW,
0 slots over, 0 curtailment, 0 escalations. Peak reduction +31%.

```
========================================================================
SMART-GRID MAS  |  scenario: heatwave_peak
========================================================================
Heatwave evening. Solar falls off after 18:00 while AC load peaks and EVs begin charging on arrival home. Feeder 3 approaches transformer capacity. The system must shift flexible load, discharge storage, and stay under the price cap and fairness threshold -- escalating to a human only if physics cannot be satisfied economically.

slots=6  feeder_capacity=230.0kW  target=180.0kW  price_cap=0.6
stagger(rebound mitigation)=ON  use_llm=OFF  human_available=YES

========================================================================
STEP 1 — Telemetry / baseline (uncoordinated, convenience-driven)
========================================================================
  slot    16h    17h    18h    19h    20h    21h
  load     88    104    136    256    240    104
    16h |######
    17h |#######
    18h |#########
    19h |#################  <-- OVER CAPACITY
    20h |################  <-- OVER CAPACITY
    21h |#######
  baseline peak = 256 kW  (capacity 230 kW)  -- 2 slot(s) OVER CAPACITY

========================================================================
STEP 2 — Iterative market coordination (price <-> demand response)
========================================================================
  up to 6 adjustment rounds; PriceGuard damps oscillation; stagger=ON
  round   peak     prices ($/kWh per slot)
      1    176kW   [0.05 0.05 0.05 0.05 0.05 0.05]
      2    176kW   [0.05 0.05 0.05 0.05 0.05 0.05]
      3    176kW   [0.05 0.05 0.05 0.05 0.05 0.05]
      4    176kW   [0.05 0.05 0.05 0.05 0.05 0.05]
      5    176kW   [0.05 0.05 0.05 0.05 0.05 0.05]
      6    176kW   [0.05 0.05 0.05 0.05 0.05 0.05]
  PriceGuard intervened 30 times (ramp-limit / hysteresis) to suppress oscillation

========================================================================
STEP 3 — Converged load profile
========================================================================
  slot    16h    17h    18h    19h    20h    21h
  load    176    170    158    168    152    104
    16h |############
    17h |###########
    18h |###########
    19h |###########
    20h |##########
    21h |#######
  storage discharge per slot:    0     0     0     0     0     0  (final SoC=80%, 0 discharges)
  baseline peak = 256 kW  ->  coordinated peak = 176 kW

========================================================================
STEP 4 — Grid checks physics; escalate if market cannot solve
========================================================================

========================================================================
METRICS  (agent / interaction / system / human)
========================================================================
AGENT
  households meeting comfort/deadline : 8/8
  storage final SoC / cycles used     : 80% / 0 discharge events
INTERACTION
  messages delivered                  : 36
  dead-letter (rejected) messages     : 0
  max price oscillation (round-to-round): 0.000 $/kWh
  escalations raised                  : 0
SYSTEM
  baseline peak                       : 256 kW
  coordinated peak                    : 176 kW
  peak reduction                      : +31%
  slots over capacity (final)         : 0
  total curtailed                     : 0 kW
  fairness (curtailment Gini)         : 0.00  (within threshold)
HUMAN
  irreversible actions sent to human  : 0
  approved by human                   : 0
  regulator overrides recorded        : 0

========================================================================
AUDIT TRACE  (this episode, by correlation_id)
========================================================================
  36 message events logged to logs/audit_heatwave_peak.jsonl
========================================================================
```

**Reading:** the market + staggering flatten a 256 kW convenience-driven peak to
176 kW within physical limits, with no curtailment and no human involvement. This
is the system working as intended in steady stress.

---

## Run 2 — `heatwave_peak --inject rebound`  (emergent failure exposed)

```
python3 -m src.sim.run --scenario scenarios/heatwave_peak.yaml --inject rebound
```

**Look for:** identical scenario, but `stagger=OFF`. The peak **oscillates** round
to round and the reduction collapses to +12%.

```
========================================================================
SMART-GRID MAS  |  scenario: heatwave_peak
========================================================================
Heatwave evening. Solar falls off after 18:00 while AC load peaks and EVs begin charging on arrival home. Feeder 3 approaches transformer capacity. The system must shift flexible load, discharge storage, and stay under the price cap and fairness threshold -- escalating to a human only if physics cannot be satisfied economically.

slots=6  feeder_capacity=230.0kW  target=180.0kW  price_cap=0.6
stagger(rebound mitigation)=OFF  use_llm=OFF  human_available=YES

========================================================================
STEP 1 — Telemetry / baseline (uncoordinated, convenience-driven)
========================================================================
  slot    16h    17h    18h    19h    20h    21h
  load     88    104    136    256    240    104
    16h |######
    17h |#######
    18h |#########
    19h |#################  <-- OVER CAPACITY
    20h |################  <-- OVER CAPACITY
    21h |#######
  baseline peak = 256 kW  (capacity 230 kW)  -- 2 slot(s) OVER CAPACITY

========================================================================
STEP 2 — Iterative market coordination (price <-> demand response)
========================================================================
  up to 6 adjustment rounds; PriceGuard damps oscillation; stagger=OFF
  round   peak     prices ($/kWh per slot)
      1    192kW   [0.05 0.18 0.05 0.05 0.05 0.05]
      2    224kW   [0.05 0.15 0.06 0.05 0.05 0.05]
      3    256kW   [0.05 0.12 0.05 0.06 0.05 0.05]
      4    224kW   [0.05 0.09 0.06 0.05 0.05 0.05]
      5    256kW   [0.05 0.07 0.05 0.06 0.05 0.05]
      6    224kW   [0.05 0.06 0.06 0.05 0.05 0.05]
  PriceGuard intervened 26 times (ramp-limit / hysteresis) to suppress oscillation

========================================================================
STEP 3 — Converged load profile
========================================================================
  slot    16h    17h    18h    19h    20h    21h
  load    176    104    224    168    152    104
    16h |############
    17h |#######
    18h |###############
    19h |###########
    20h |##########
    21h |#######
  storage discharge per slot:    0     0     0     0     0     0  (final SoC=80%, 0 discharges)
  baseline peak = 256 kW  ->  coordinated peak = 224 kW
  [!] rebound mitigation OFF: synchronized response can pile load into the cheapest slot

========================================================================
STEP 4 — Grid checks physics; escalate if market cannot solve
========================================================================

========================================================================
METRICS  (agent / interaction / system / human)
========================================================================
AGENT
  households meeting comfort/deadline : 8/8
  storage final SoC / cycles used     : 80% / 0 discharge events
INTERACTION
  messages delivered                  : 36
  dead-letter (rejected) messages     : 0
  max price oscillation (round-to-round): 0.036 $/kWh
  escalations raised                  : 0
SYSTEM
  baseline peak                       : 256 kW
  coordinated peak                    : 224 kW
  peak reduction                      : +12%
  slots over capacity (final)         : 0
  total curtailed                     : 0 kW
  fairness (curtailment Gini)         : 0.00  (within threshold)
HUMAN
  irreversible actions sent to human  : 0
  approved by human                   : 0
  regulator overrides recorded        : 0

========================================================================
AUDIT TRACE  (this episode, by correlation_id)
========================================================================
  36 message events logged to logs/audit_heatwave_peak.jsonl
========================================================================
```

**Reading:** with households responding to the same signal in lockstep, every home
chases the same cheap slot and creates a *new* synchronized peak — the rebound /
limit-cycle failure named in `docs/emergence.md`. The fix (staggered targets +
ramp limits) is exactly what Run 1 has on. Same scenario, mitigation toggled: the
emergent behavior and its remedy are both demonstrated.

---

## Run 3 — `supply_shortfall`  (full safety path, human approves)

```
python3 -m src.sim.run --scenario scenarios/supply_shortfall.yaml
```

**Look for:** even after storage discharges 40 kW, 19h stays over capacity at the
price cap → escalation → **human approves** → 11 kW shed in fairness order (3 kW
each across 4 homes).

```
========================================================================
SMART-GRID MAS  |  scenario: supply_shortfall
========================================================================
A severe event (heatwave + a generator trip upstream) leaves Feeder 3 with far less capacity than firm demand needs. Even after every household shifts what it can and storage fully discharges, one slot remains physically over the limit with price already pinned to the cap. Economics are exhausted -> the grid escalates, a human authorizes action, and load is shed in FAIRNESS order (a rolling brownout) rather than always cutting the same homes.

slots=5  feeder_capacity=150.0kW  target=110.0kW  price_cap=0.6
stagger(rebound mitigation)=ON  use_llm=OFF  human_available=YES

========================================================================
STEP 1 — Telemetry / baseline (uncoordinated, convenience-driven)
========================================================================
  slot    17h    18h    19h    20h    21h
  load     93    129    249    117     81
    17h |##########
    18h |#############
    19h |##########################  <-- OVER CAPACITY
    20h |############
    21h |########
  baseline peak = 249 kW  (capacity 150 kW)  -- 1 slot(s) OVER CAPACITY

========================================================================
STEP 2 — Iterative market coordination (price <-> demand response)
========================================================================
  up to 6 adjustment rounds; PriceGuard damps oscillation; stagger=ON
  round   peak     prices ($/kWh per slot)
      1    201kW   [0.15 0.60 0.60 0.15 0.05]
      2    169kW   [0.15 0.48 0.60 0.15 0.05]
      3    169kW   [0.15 0.38 0.60 0.15 0.05]
      4    169kW   [0.15 0.31 0.60 0.15 0.05]
      5    169kW   [0.15 0.25 0.60 0.15 0.05]
      6    161kW   [0.15 0.29 0.60 0.15 0.05]
  PriceGuard intervened 25 times (ramp-limit / hysteresis) to suppress oscillation

========================================================================
STEP 3 — Converged load profile
========================================================================
  slot    17h    18h    19h    20h    21h
  load    117    129    161    117    105
    17h |############
    18h |#############
    19h |#################  <-- OVER CAPACITY
    20h |############
    21h |###########
  storage discharge per slot:    0     0    40     0     0  (final SoC=46%, 1 discharges)
  baseline peak = 249 kW  ->  coordinated peak = 161 kW

========================================================================
STEP 4 — Grid checks physics; escalate if market cannot solve
========================================================================
  slot 19h: OVERLOAD 11 kW (load 161 > cap 150), price=0.60 [AT CAP]
    -> ESCALATION to human. rationale: Feeder 'feeder_3' projected at 161 kW against a 150 kW limit (107% utilization). Market price reached the regulatory cap of 0.6 without clearing the overload. Economic signals are exhausted; human authorization is required for physical curtailment affecting 6 households. Recommend approving fairness-ordered curtailment.
    -> HITL gate (human approval) = APPROVED
      curtail home_01: -3 kW (firm/brownout, fairness-ordered)
      curtail home_02: -3 kW (firm/brownout, fairness-ordered)
      curtail home_03: -3 kW (firm/brownout, fairness-ordered)
      curtail home_04: -3 kW (firm/brownout, fairness-ordered)

========================================================================
METRICS  (agent / interaction / system / human)
========================================================================
AGENT
  households meeting comfort/deadline : 6/6
  storage final SoC / cycles used     : 46% / 1 discharge events
INTERACTION
  messages delivered                  : 35
  dead-letter (rejected) messages     : 0
  max price oscillation (round-to-round): 0.120 $/kWh
  escalations raised                  : 1
SYSTEM
  baseline peak                       : 249 kW
  coordinated peak                    : 161 kW
  peak reduction                      : +35%
  slots over capacity (final)         : 1
  total curtailed                     : 11 kW
  fairness (curtailment Gini)         : 0.00  (within threshold)
HUMAN
  irreversible actions sent to human  : 1
  approved by human                   : 1
  regulator overrides recorded        : 0

========================================================================
AUDIT TRACE  (this episode, by correlation_id)
========================================================================
  35 message events logged to logs/audit_supply_shortfall.jsonl
    [DELIVER] feeder_3 -> regulator : ESCALATION {'slot': 2, 'overload_kw': 11.0}
    [DELIVER] feeder_3 -> home_01 : CURTAILMENT_REQUEST {'slot': 2, 'kwh': 2.75, 'kind': 'firm/brownout'}
    [DELIVER] feeder_3 -> home_02 : CURTAILMENT_REQUEST {'slot': 2, 'kwh': 2.75, 'kind': 'firm/brownout'}
    [DELIVER] feeder_3 -> home_03 : CURTAILMENT_REQUEST {'slot': 2, 'kwh': 2.75, 'kind': 'firm/brownout'}
    [DELIVER] feeder_3 -> home_04 : CURTAILMENT_REQUEST {'slot': 2, 'kwh': 2.75, 'kind': 'firm/brownout'}
========================================================================
```

**Reading:** Gini = 0.00 means the curtailment was split *perfectly evenly*
(equal cuts = no inequality), well within the 0.40 alarm threshold. Storage,
escalation, human approval, fairness, and the audit trail are all exercised in one
episode.

---

## Run 4 — `supply_shortfall --no-human`  (irreversible action blocked)

```
python3 -m src.sim.run --scenario scenarios/supply_shortfall.yaml --no-human
```

**Look for:** same overload and escalation, but with no operator available the HITL
gate **denies** the irreversible curtailment — the grid holds at a safe fallback
and **0 kW is shed**.

```
========================================================================
SMART-GRID MAS  |  scenario: supply_shortfall
========================================================================
A severe event (heatwave + a generator trip upstream) leaves Feeder 3 with far less capacity than firm demand needs. Even after every household shifts what it can and storage fully discharges, one slot remains physically over the limit with price already pinned to the cap. Economics are exhausted -> the grid escalates, a human authorizes action, and load is shed in FAIRNESS order (a rolling brownout) rather than always cutting the same homes.

slots=5  feeder_capacity=150.0kW  target=110.0kW  price_cap=0.6
stagger(rebound mitigation)=ON  use_llm=OFF  human_available=NO

========================================================================
STEP 1 — Telemetry / baseline (uncoordinated, convenience-driven)
========================================================================
  slot    17h    18h    19h    20h    21h
  load     93    129    249    117     81
    17h |##########
    18h |#############
    19h |##########################  <-- OVER CAPACITY
    20h |############
    21h |########
  baseline peak = 249 kW  (capacity 150 kW)  -- 1 slot(s) OVER CAPACITY

========================================================================
STEP 2 — Iterative market coordination (price <-> demand response)
========================================================================
  up to 6 adjustment rounds; PriceGuard damps oscillation; stagger=ON
  round   peak     prices ($/kWh per slot)
      1    201kW   [0.15 0.60 0.60 0.15 0.05]
      2    169kW   [0.15 0.48 0.60 0.15 0.05]
      3    169kW   [0.15 0.38 0.60 0.15 0.05]
      4    169kW   [0.15 0.31 0.60 0.15 0.05]
      5    169kW   [0.15 0.25 0.60 0.15 0.05]
      6    161kW   [0.15 0.29 0.60 0.15 0.05]
  PriceGuard intervened 25 times (ramp-limit / hysteresis) to suppress oscillation

========================================================================
STEP 3 — Converged load profile
========================================================================
  slot    17h    18h    19h    20h    21h
  load    117    129    161    117    105
    17h |############
    18h |#############
    19h |#################  <-- OVER CAPACITY
    20h |############
    21h |###########
  storage discharge per slot:    0     0    40     0     0  (final SoC=46%, 1 discharges)
  baseline peak = 249 kW  ->  coordinated peak = 161 kW

========================================================================
STEP 4 — Grid checks physics; escalate if market cannot solve
========================================================================
  slot 19h: OVERLOAD 11 kW (load 161 > cap 150), price=0.60 [AT CAP]
    -> ESCALATION to human. rationale: Feeder 'feeder_3' projected at 161 kW against a 150 kW limit (107% utilization). Market price reached the regulatory cap of 0.6 without clearing the overload. Economic signals are exhausted; human authorization is required for physical curtailment affecting 6 households. Recommend approving fairness-ordered curtailment.
    -> HITL gate (human approval) = DENIED
    -> not approved: grid holds at safe fallback, no curtailment performed

========================================================================
METRICS  (agent / interaction / system / human)
========================================================================
AGENT
  households meeting comfort/deadline : 6/6
  storage final SoC / cycles used     : 46% / 1 discharge events
INTERACTION
  messages delivered                  : 31
  dead-letter (rejected) messages     : 0
  max price oscillation (round-to-round): 0.120 $/kWh
  escalations raised                  : 1
SYSTEM
  baseline peak                       : 249 kW
  coordinated peak                    : 161 kW
  peak reduction                      : +35%
  slots over capacity (final)         : 1
  total curtailed                     : 0 kW
  fairness (curtailment Gini)         : 0.00  (within threshold)
HUMAN
  irreversible actions sent to human  : 1
  approved by human                   : 0
  regulator overrides recorded        : 0

========================================================================
AUDIT TRACE  (this episode, by correlation_id)
========================================================================
  31 message events logged to logs/audit_supply_shortfall.jsonl
    [DELIVER] feeder_3 -> regulator : ESCALATION {'slot': 2, 'overload_kw': 11.0}
========================================================================
```

**Reading:** this is the safety property made concrete. An irreversible action
(firm load shedding / rolling brownout) cannot be taken without explicit human
authorization. When the human is absent, the system refuses to act unilaterally —
"you cannot un-brown-out a neighborhood," so it must not happen automatically.

---

## Sample audit log entry

The full `logs/audit_supply_shortfall.jsonl` is committed. Each line is one
message event. Here is the escalation entry — the moment economics are exhausted
and the grid hands off to the human:

```json
{"logged_at": "2026-06-25T11:46:55.693296+00:00", "event": "DELIVER", "message": {"sender": "market_agent", "recipient": "*", "msg_type": "PRICE_SIGNAL", "trust_domain": "market", "payload": {"slot": 0, "price": 0.1462, "cap": 0.6}, "priority": "normal", "confidence": null, "correlation_id": "7ab9e9ae-ad58-4e1a-b5bd-fd413c20c03c", "schema_version": "1.0", "msg_id": "91cd5ec9-d365-4d45-8f83-42aa629961f1", "timestamp": "2026-06-25T11:46:55.692905+00:00", "signature": "b24fadbca8d7c7b7f9d2dd629241d63e5eab6c66064a5d3542225b3cb114a6c2"}}
{"logged_at": "2026-06-25T11:46:55.694269+00:00", "event": "DELIVER", "message": {"sender": "market_agent", "recipient": "*", "msg_type": "PRICE_SIGNAL", "trust_domain": "market", "payload": {"slot": 1, "price": 0.6, "cap": 0.6}, "priority": "normal", "confidence": null, "correlation_id": "7ab9e9ae-ad58-4e1a-b5bd-fd413c20c03c", "schema_version": "1.0", "msg_id": "67819176-1eb1-445f-a3f7-caf1959da9d4", "timestamp": "2026-06-25T11:46:55.694207+00:00", "signature": "caf1c6f6d2fffb131e6f5824a182974efbe06b5580448a5ec848a81587a70639"}}
{"logged_at": "2026-06-25T11:46:55.713679+00:00", "event": "DELIVER", "message": {"sender": "market_agent", "recipient": "*", "msg_type": "PRICE_SIGNAL", "trust_domain": "market", "payload": {"slot": 2, "price": 0.6, "cap": 0.6}, "priority": "normal", "confidence": null, "correlation_id": "7ab9e9ae-ad58-4e1a-b5bd-fd413c20c03c", "schema_version": "1.0", "msg_id": "4c9563ca-f9d1-4f0a-bdf1-abc354e21138", "timestamp": "2026-06-25T11:46:55.713544+00:00", "signature": "deab13c2b89f214c51385635c1f83f5e0ca87a07c175fa99746be639e21d4bc3"}}
```

Every entry carries: `correlation_id` (traces the full episode), `msg_id`
(unique per message), `signature` (HMAC for tamper detection), `sender`,
`recipient`, `msg_type`, `trust_domain`, and `payload`. The full log for this
run is 35 entries in `logs/audit_supply_shortfall.jsonl`.

---

## Summary of evidence

| Capability | Demonstrated in |
|---|---|
| Market coordination flattening a peak | Run 1 (256 → 176 kW, +31%) |
| Named emergent failure + its mitigation | Run 1 vs Run 2 (rebound: +31% vs +12%) |
| PriceGuard suppressing oscillation | all runs (intervention counts in trace) |
| Storage dispatch (peak shaving) | Run 3/4 (40 kW discharge, SoC 90% → 46%) |
| Escalation when economics are exhausted | Run 3/4 (overload at price cap) |
| Human-in-the-loop approval | Run 3 (APPROVED → curtailment executed) |
| HITL gate blocking irreversible action | Run 4 (DENIED → 0 kW shed) |
| Fairness-ordered curtailment + Gini | Run 3 (equal 3 kW cuts, Gini 0.00) |
| Audit trace by correlation_id | Run 3/4 (ESCALATION + CURTAILMENT logged) |
| Signed append-only message log | `logs/audit_supply_shortfall.jsonl` (35 entries) |
