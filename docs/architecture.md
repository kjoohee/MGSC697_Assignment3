# Architecture & Agent Roster

## Diagram

The four subgraphs are **A2A trust boundaries** (separate organizations). Tool
and data access *inside* an agent is the **MCP boundary**.

```mermaid
flowchart TB
    subgraph Consumer["Consumer domain — A2A boundary"]
        H1[Household 1<br/>HEMS]
        H2[Household 2<br/>HEMS]
        Hn[Household N<br/>HEMS]
        AGG[Aggregator / VPP]
    end
    subgraph MarketD["Market domain — A2A boundary"]
        PS[Market Agent<br/>price clearing under cap]
    end
    subgraph GridD["Grid / DSO domain — A2A boundary"]
        GA[Grid Agent<br/>physical feasibility]
        ST[Storage Agent<br/>arbitrage + peak shaving]
    end
    subgraph Gov["Governance domain — A2A boundary"]
        REG[Regulator Agent<br/>cap + fairness]
        HUMAN([Human Operator — HITL])
    end
    BB[(Blackboard<br/>telemetry · price · forecast)]

    H1 --> AGG
    H2 --> AGG
    Hn --> AGG
    AGG -- BID --> PS
    ST -- BID --> PS
    PS -- "PRICE_SIGNAL (broadcast)" --> BB
    BB -. read .-> AGG
    BB -. read .-> ST
    GA -- CONSTRAINT --> PS
    GA -- telemetry --> BB
    ST -- SoC --> BB
    PS -- DISPATCH --> ST
    PS -- CLEARING --> AGG
    GA -- "ESCALATION (price exhausted)" --> REG
    REG --> HUMAN
    HUMAN -- "OVERRIDE / approve curtailment" --> GA
    REG -. "price cap + fairness constraints" .-> PS
```

## Control flow (one episode)

```mermaid
sequenceDiagram
    participant H as Households
    participant M as Market
    participant G as Grid
    participant R as Regulator
    participant Hu as Human
    loop iterative coordination (until settled)
        M->>H: PRICE_SIGNAL (per slot, under cap)
        H->>H: reschedule flexible load (staggered)
        H-->>M: resulting load (via blackboard)
        M->>M: reprice (PriceGuard damps oscillation)
    end
    G->>G: check physical feasibility
    alt feasible
        G-->>R: nominal
    else overload AND price at cap
        G->>R: ESCALATION (+ rationale)
        R->>Hu: request approval (irreversible action)
        Hu-->>G: APPROVE / DENY
        opt approved
            G->>H: CURTAILMENT_REQUEST (fairness-ordered)
        end
    end
```

## Agent roster (detail)

| Agent | Trust domain | Responsibilities | Tools (MCP) | Memory | Permissions |
|---|---|---|---|---|---|
| Household (HEMS) | consumer | minimize cost s.t. comfort/deadline; respond to price | smart meter, HVAC/EV/water-heater control, local PV+battery | usage pattern, comfort range, EV schedule | `control:self_devices` (own devices only; no access to other homes) |
| Aggregator / VPP | consumer | bundle homes, bid to market, relay price, preserve privacy | aggregate of homes, market API | aggregate flexibility, contracts | `submit:aggregate_bid`, `relay:price` (aggregate-only; cannot force a home) |
| Grid (DSO) | grid | guarantee physical feasibility; issue constraints; escalate | SCADA/telemetry, constraint publishing | topology, capacity limits, load history | `issue:constraint`, `request:curtailment`, `escalate` (no direct device control) |
| Storage | grid | arbitrage + grid services (peak shaving) | BMS charge/discharge, bidding | SoC, degradation, price history | `control:self_battery`, `submit:bid` (within SoC/degradation limits) |
| Market | market | run the auction; clear price under the cap; broadcast | bid aggregation, clearing | bid history, elasticity estimate | `set:price`, `broadcast:price` (cap-bounded) |
| Regulator + Human | governance | enforce cap + fairness; approve/override; audit | policy injection, override, audit log | regulations, audit records | `set:price_cap`, `override:market`, `approve:curtailment` |

### Why Grid and Market are separate agents

If one agent owned both economics and physics, an overloaded-but-cleared schedule
would be invisible — there would be no internal disagreement to surface. By
splitting them, the *market clears* and the *grid vetoes/escalates*, which gives
us a natural escalation trigger, a clean human-in-the-loop chokepoint, and a clear
audit boundary. This separation is the backbone of the coordination, emergence,
and safety designs.
