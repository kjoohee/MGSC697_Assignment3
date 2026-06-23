"""End-to-end simulation runner.

Drives one full coordination episode over the evening time slots and prints a
readable trace:

    telemetry -> market clears prices -> price broadcast -> households reschedule
    -> storage discharges -> grid checks physics -> (if infeasible at price cap)
    escalate to human -> fairness-ordered curtailment -> metrics

Run:
    python -m src.sim.run --scenario scenarios/heatwave_peak.yaml
    python -m src.sim.run --scenario scenarios/heatwave_peak.yaml --inject rebound
    python -m src.sim.run --scenario scenarios/heatwave_peak.yaml --use-llm
"""
from __future__ import annotations

import argparse
import os
import uuid

from ..blackboard import Blackboard
from ..bus import AuditLog, MessageBus
from ..messages import MsgType, TrustDomain, Priority, new_message
from ..safety.guards import PriceGuard, FairnessTracker, HITLGate, stagger_targets
from ..agents.household import Household as HouseholdAgent
from ..agents.aggregator import Aggregator
from ..agents.grid import Grid
from ..agents.storage import Storage
from ..agents.market import Market
from ..agents.regulator import Regulator
from .scenario import load_scenario


def hr(title=""):
    line = "=" * 72
    return f"\n{line}\n{title}\n{line}" if title else line


def load_profile(households, slots, discharge_per_slot):
    prof = [0.0] * slots
    for s in range(slots):
        prof[s] = sum(h.load_at(s) for h in households) - discharge_per_slot[s]
    return prof


def run(scenario_path: str, inject: str | None, use_llm: bool, no_human: bool,
        stagger_override: bool | None):
    sc = load_scenario(scenario_path)

    # --- flags / injections ------------------------------------------------
    stagger = sc.flags.get("stagger", True)
    if stagger_override is not None:
        stagger = stagger_override
    if inject == "rebound":
        stagger = False  # disable mitigation to expose the synchronized rebound peak

    print(hr(f"SMART-GRID MAS  |  scenario: {sc.name}"))
    print(sc.description)
    print(f"slots={sc.slots}  feeder_capacity={sc.feeder_capacity_kw}kW  "
          f"target={sc.target_kw}kW  price_cap={sc.price_cap}")
    print(f"stagger(rebound mitigation)={'ON' if stagger else 'OFF'}  "
          f"use_llm={'ON' if use_llm else 'OFF'}  human_available={'NO' if no_human else 'YES'}")

    # --- infrastructure ----------------------------------------------------
    os.makedirs("logs", exist_ok=True)
    audit = AuditLog(os.path.join("logs", f"audit_{sc.name}.jsonl"))
    bus = MessageBus(audit)
    bb = Blackboard()
    correlation_id = str(uuid.uuid4())

    # --- agents ------------------------------------------------------------
    households = [
        HouseholdAgent(h.name, bus, h.base_load, h.flex_kw, h.flex_slots_needed, h.deadline_slot)
        for h in sc.households
    ]
    aggregator = Aggregator("aggregator_A", bus, households)
    storage = Storage("storage_1", bus, **sc.storage)
    guards = [PriceGuard() for _ in range(sc.slots)]
    market = Market("market_agent", bus, sc.price_cap, sc.feeder_capacity_kw, guards)
    gate = HITLGate(auto_approve_human=not no_human)
    fairness = FairnessTracker()
    grid = Grid("feeder_3", bus, sc.feeder_capacity_kw, gate, fairness, use_llm=use_llm)
    regulator = Regulator("regulator", bus, sc.price_cap)

    for a in households + [aggregator, storage, market, grid, regulator]:
        for mt in getattr(a, "accepts", ()):  # subscribe to broadcast types they accept
            bus.subscribe(a.name, mt)

    # --- 0. baseline (uncoordinated, convenience-driven) -------------------
    # The realistic "do nothing" case: every household runs its flexible load
    # (EV, etc.) during its own highest-consumption hours -- i.e. right when they
    # get home and everything is already on. No price awareness. This is what the
    # coordination layer has to beat.
    for h in households:
        peak_slots = sorted(range(min(h.deadline_slot + 1, sc.slots)),
                            key=lambda s: h.base_load[s] if s < len(h.base_load) else 0,
                            reverse=True)
        h.scheduled_slots = sorted(peak_slots[: h.flex_slots_needed])
    discharge = [0.0] * sc.slots
    baseline = load_profile(households, sc.slots, discharge)
    bb.write("telemetry", "feeder_3_load_kw", baseline)
    bb.snapshot("baseline")

    print(hr("STEP 1 — Telemetry / baseline (uncoordinated, convenience-driven)"))
    print_profile(sc, baseline)
    over = sum(1 for v in baseline if v > sc.feeder_capacity_kw)
    print(f"  baseline peak = {max(baseline):.0f} kW  (capacity {sc.feeder_capacity_kw:.0f} kW)"
          f"{'  -- ' + str(over) + ' slot(s) OVER CAPACITY' if over else ''}")

    # --- STEP 2: iterative demand-response coordination --------------------
    # Real demand response is a feedback loop: the market reprices based on the
    # load its own signal produced, and agents respond again, until it settles.
    # This is where oscillation (a limit cycle) can emerge and where the
    # PriceGuard earns its keep. Staggering decorrelates the household responses.
    ROUNDS = 6
    prices = [sc.initial_price] * sc.slots
    initial_soc = storage.soc
    print(hr("STEP 2 — Iterative market coordination (price <-> demand response)"))
    print(f"  up to {ROUNDS} adjustment rounds; PriceGuard damps oscillation; "
          f"stagger={'ON' if stagger else 'OFF'}")
    print("  round   peak     prices ($/kWh per slot)")
    discharge = [0.0] * sc.slots
    for rnd in range(ROUNDS):
        # households respond to current prices (+ optional staggering)
        stagger_map = {}
        if stagger:
            cheap = sorted(range(sc.slots), key=lambda s: prices[s])[: max(2, sc.slots // 2)]
            stagger_map = stagger_targets([h.name for h in households], cheap)
        for h in households:
            h.schedule(prices, stagger_slot=stagger_map.get(h.name))
        # storage re-dispatched fresh each round under current prices
        storage.soc = initial_soc
        storage.dispatch_log = []
        discharge = [storage.respond(s, prices[s]) for s in range(sc.slots)]
        load = load_profile(households, sc.slots, discharge)
        # market reprices each slot from the resulting congestion (PriceGuard inside)
        prices = []
        for s in range(sc.slots):
            res = market.clear(s, load[s], sc.target_kw)
            prices.append(res.price)
            market.broadcast_price(s, res.price, correlation_id)
        print(f"   {rnd + 1:>4}   {max(load):4.0f}kW   [" + " ".join(f"{p:4.2f}" for p in prices) + "]")
    bb.write("price", "slots", prices)
    bb.write("telemetry", "feeder_3_load_kw", load)
    bb.snapshot("coordinated")
    coordinated = load

    guard_actions = sum(len(g.events) for g in guards)
    if guard_actions:
        print(f"  PriceGuard intervened {guard_actions} times (ramp-limit / hysteresis) "
              f"to suppress oscillation")

    print(hr("STEP 3 — Converged load profile"))
    print_profile(sc, coordinated)
    print(f"  storage discharge per slot: " +
          "  ".join(f"{d:4.0f}" for d in discharge) + f"  (final SoC={storage.soc:.0%}, "
          f"{len(storage.dispatch_log)} discharges)")
    print(f"  baseline peak = {max(baseline):.0f} kW  ->  coordinated peak = {max(coordinated):.0f} kW")
    if not stagger:
        print("  [!] rebound mitigation OFF: synchronized response can pile load into the cheapest slot")

    # --- 4. grid checks physical feasibility; escalate if needed -----------
    print(hr("STEP 4 — Grid checks physics; escalate if market cannot solve"))
    curtailed_total = 0.0
    for s in range(sc.slots):
        overload = grid.check_feasibility(coordinated[s])
        if overload <= 0:
            continue
        at_cap = prices[s] >= sc.price_cap - 1e-9
        print(f"  slot {sc.slot_labels[s]}: OVERLOAD {overload:.0f} kW "
              f"(load {coordinated[s]:.0f} > cap {sc.feeder_capacity_kw:.0f}), "
              f"price={prices[s]:.2f}{' [AT CAP]' if at_cap else ''}")
        if not at_cap:
            print("    -> price has headroom; market would raise price further (no curtailment yet)")
            continue
        # price exhausted -> escalate through the human-in-the-loop gate
        rec = grid.escalate(slot=s, load_kw=coordinated[s], at_price_cap=True,
                            price_cap=sc.price_cap, households=households)
        esc_msg = new_message(sender="feeder_3", recipient="regulator",
                              msg_type=MsgType.ESCALATION, trust_domain=TrustDomain.GRID,
                              correlation_id=correlation_id, priority=Priority.EMERGENCY,
                              payload={"slot": s, "overload_kw": overload})
        bus.publish(esc_msg)
        print(f"    -> ESCALATION to human. rationale: {rec['rationale']}")
        print(f"    -> HITL gate ({'human' } approval) = "
              f"{'APPROVED' if rec['approved'] else 'DENIED'}")
        if not rec["approved"]:
            print("    -> not approved: grid holds at safe fallback, no curtailment performed")
            continue
        # fairness-ordered curtailment until feasible. When the overload exceeds
        # available flexibility, this becomes firm load-shedding (a rolling
        # brownout) -- precisely the irreversible action the HITL gate guards.
        order = fairness.order_by_fairness([h.name for h in households])
        need = overload
        by_name = {h.name: h for h in households}
        # cap each home's shed at a fair share so no single home goes fully dark
        fair_share = overload / len(households) * 1.5
        for name in order:
            if need <= 0.5:
                break
            h = by_name[name]
            avail = h.load_at(s)
            if avail <= 0:
                continue
            shed = min(avail, need, fair_share)
            kind = "flex" if s in h.scheduled_slots and shed <= h.flex_kw else "firm/brownout"
            cmsg = new_message(sender="feeder_3", recipient=name,
                               msg_type=MsgType.CURTAILMENT_REQUEST,
                               trust_domain=TrustDomain.GRID,
                               correlation_id=correlation_id, priority=Priority.HIGH,
                               payload={"slot": s, "kwh": shed, "kind": kind})
            bus.publish(cmsg)
            fairness.record(name, shed)
            need -= shed
            curtailed_total += shed
            print(f"      curtail {name}: -{shed:.0f} kW ({kind}, fairness-ordered)")

    # --- metrics -----------------------------------------------------------
    metrics = print_metrics(sc, baseline, coordinated, households, storage, grid,
                            regulator, market, bus, fairness, curtailed_total,
                            correlation_id, audit)
    audit.close()

    # Run context + metrics, returned for the evaluation harness (eval/).
    metrics.update({
        "scenario": sc.name,
        "stagger": stagger,
        "use_llm": use_llm,
        "human_available": not no_human,
        "inject": inject or "",
    })
    return metrics


def print_profile(sc, profile):
    cap = sc.feeder_capacity_kw
    print("  slot  " + "  ".join(f"{lbl:>5}" for lbl in sc.slot_labels))
    print("  load  " + "  ".join(f"{v:5.0f}" for v in profile))
    bars = []
    for v in profile:
        n = int(round(20 * v / max(cap * 1.3, 1)))
        mark = "#" * min(n, 26)
        over = "!" if v > cap else ""
        bars.append((mark, over))
    for s, (mark, over) in enumerate(bars):
        flag = "  <-- OVER CAPACITY" if over else ""
        print(f"   {sc.slot_labels[s]:>4} |{mark}{flag}")


def price_oscillation(market):
    amp = 0.0
    by_slot = {}
    for r in market.history:
        by_slot.setdefault(r.slot, []).append(r.price)
    for series in by_slot.values():
        for a, b in zip(series, series[1:]):
            amp = max(amp, abs(b - a))
    return amp


def print_metrics(sc, baseline, coordinated, households, storage, grid, regulator,
                  market, bus, fairness, curtailed_total, correlation_id, audit):
    print(hr("METRICS  (agent / interaction / system / human)"))
    peak_base, peak_coord = max(baseline), max(coordinated)
    reduction = (peak_base - peak_coord) / peak_base if peak_base else 0

    print("AGENT")
    comfort_ok = sum(1 for h in households if len(h.scheduled_slots) == h.flex_slots_needed
                     and all(s <= h.deadline_slot for s in h.scheduled_slots))
    print(f"  households meeting comfort/deadline : {comfort_ok}/{len(households)}")
    print(f"  storage final SoC / cycles used     : {storage.soc:.0%} / "
          f"{len(storage.dispatch_log)} discharge events")

    print("INTERACTION")
    print(f"  messages delivered                  : {bus.delivered}")
    print(f"  dead-letter (rejected) messages     : {len(bus.dead_letter)}")
    print(f"  max price oscillation (round-to-round): {price_oscillation(market):.3f} $/kWh")
    print(f"  escalations raised                  : {len(grid.escalations)}")

    print("SYSTEM")
    print(f"  baseline peak                       : {peak_base:.0f} kW")
    print(f"  coordinated peak                    : {peak_coord:.0f} kW")
    print(f"  peak reduction                      : {reduction:+.0%}")
    print(f"  slots over capacity (final)         : "
          f"{sum(1 for v in coordinated if v > sc.feeder_capacity_kw)}")
    print(f"  total curtailed                     : {curtailed_total:.0f} kW")
    gini = fairness.gini()
    breach = regulator.review_fairness(gini)
    print(f"  fairness (curtailment Gini)         : {gini:.2f}"
          f"{'  [!] BREACH > %.2f' % regulator.fairness_gini_threshold if breach else '  (within threshold)'}")

    print("HUMAN")
    human_calls = [d for d in grid.gate.decisions if d["via"] == "human"]
    approved = [d for d in human_calls if d["approved"]]
    print(f"  irreversible actions sent to human  : {len(human_calls)}")
    print(f"  approved by human                   : {len(approved)}")
    print(f"  regulator overrides recorded        : {len(regulator.overrides)}")

    print(hr("AUDIT TRACE  (this episode, by correlation_id)"))
    recs = audit.for_correlation(correlation_id)
    print(f"  correlation_id = {correlation_id}")
    print(f"  {len(recs)} message events logged to logs/audit_{sc.name}.jsonl")
    shown = [r for r in recs if r["message"]["msg_type"] in
             ("ESCALATION", "CURTAILMENT_REQUEST", "OVERRIDE")]
    for r in shown[:8]:
        m = r["message"]
        print(f"    [{r['event']}] {m['sender']} -> {m['recipient']} : "
              f"{m['msg_type']} {m['payload']}")
    print(hr())

    # Same numbers the block above printed, returned as data so an evaluation
    # harness can collect them across runs without parsing stdout.
    return {
        # agent
        "comfort_ok": comfort_ok,
        "total_homes": len(households),
        "storage_soc": storage.soc,
        "storage_cycles": len(storage.dispatch_log),
        # interaction
        "messages_delivered": bus.delivered,
        "dead_letter": len(bus.dead_letter),
        "price_oscillation": price_oscillation(market),
        "escalations": len(grid.escalations),
        # system
        "baseline_peak": peak_base,
        "coordinated_peak": peak_coord,
        "peak_reduction": reduction,
        "slots_over_capacity": sum(1 for v in coordinated if v > sc.feeder_capacity_kw),
        "total_curtailed": curtailed_total,
        "gini": gini,
        "fairness_breach": bool(breach),
        # human
        "human_calls": len(human_calls),
        "human_approved": len(approved),
        "regulator_overrides": len(regulator.overrides),
        # trace
        "correlation_id": correlation_id,
        "audit_events": len(recs),
    }


def main():
    ap = argparse.ArgumentParser(description="Smart-grid multi-agent system simulation")
    ap.add_argument("--scenario", default="scenarios/heatwave_peak.yaml")
    ap.add_argument("--inject", choices=["rebound"], default=None,
                    help="inject a named failure mode")
    ap.add_argument("--use-llm", action="store_true",
                    help="use the LLM for escalation rationale (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--no-human", action="store_true",
                    help="simulate no operator available (HITL gate denies irreversible actions)")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--stagger", dest="stagger", action="store_true", default=None)
    group.add_argument("--no-stagger", dest="stagger", action="store_false", default=None)
    args = ap.parse_args()
    run(args.scenario, args.inject, args.use_llm, args.no_human, args.stagger)


if __name__ == "__main__":
    main()
