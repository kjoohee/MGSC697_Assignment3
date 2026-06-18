# Coordination Mechanism

**Choice: a hybrid of (1) a price market for economic allocation, (2) a
hierarchical safety supervisor for physics and fairness, and (3) a blackboard for
shared state.**

## Trade-off table

| Mechanism | Strengths | Why insufficient alone here | Role in our hybrid |
|---|---|---|---|
| Market / auction | distributed, privacy-preserving, price discovery, scales | blind to transformer/voltage limits; no fairness guarantee; can be gamed/collude | **primary** economic layer (clears price per slot under cap) |
| Central supervisor | simple control, easy audit/HITL chokepoint | cannot scale; centralizes all private data; single point of failure | **top layer** holds physics + emergency authority only |
| Consensus | agreement, fault tolerance | too slow for real-time; we need a clearing price, not unanimity | not used |
| Contract net | great for discrete task allocation w/ heterogeneous bidders | DER response is continuous + price-driven, not task tenders | not used (could fit a discrete repair/dispatch sub-task) |
| Blackboard | shared, observable, opportunistic state | no allocation *decision* mechanism | **substrate** for telemetry/price/forecast |

## How the layers interact

1. **Market layer** clears a congestion price per time slot, bounded by the
   regulator's cap, and broadcasts it. Agents respond locally. This repeats
   (closed loop) until load settles — `src/sim/run.py`, `src/market/clearing.py`.
2. **Safety supervisor** (Grid + Regulator) treats physical capacity and fairness
   as *hard constraints*. When the market clears something infeasible at the price
   cap, the grid escalates rather than letting the market "win".
3. **Blackboard** lets any agent read current price/telemetry/forecast without
   point-to-point chatter for every fact.

## One-line defense

> Economics through a distributed market (for efficiency and privacy), physical
> safety and fairness through inviolable hierarchical constraints — two different
> mechanisms deliberately assigned to two different concerns. Neither a pure
> market (unsafe, unfair) nor a pure supervisor (unscalable, privacy-destroying)
> would do.
