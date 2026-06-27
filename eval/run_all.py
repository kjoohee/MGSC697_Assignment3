"""Evaluation harness -- run the whole scenario matrix and collect the metrics
into one reproducible results table.

This turns the evaluation *plan* (docs/evaluation.md) into executed *evidence*:
every scenario, plus the injected rebound failure and the no-human safety path,
run end to end with their agent / interaction / system / human metrics gathered
into eval/results/summary.md (+ .csv).

Run from anywhere:
    python eval/run_all.py
"""
from __future__ import annotations

import contextlib
import csv
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
os.chdir(REPO)  # so scenarios/ and logs/ resolve regardless of caller's cwd

from src.sim.run import run  # noqa: E402

RESULTS_DIR = os.path.join(REPO, "eval", "results")

# label, scenario, inject, use_llm, no_human, stagger_override
MATRIX = [
    ("normal_day", "scenarios/normal_day.yaml", None, False, False, None),
    ("heatwave_peak", "scenarios/heatwave_peak.yaml", None, False, False, None),
    ("supply_shortfall", "scenarios/supply_shortfall.yaml", None, False, False, None),
    ("failure_rebound", "scenarios/failure_rebound.yaml", None, False, False, None),
    ("heatwave +inject rebound", "scenarios/heatwave_peak.yaml", "rebound", False, False, None),
    ("supply_shortfall --no-human", "scenarios/supply_shortfall.yaml", None, False, True, None),
]

# output column -> header label
FIELDS = [
    ("run", "run"),
    ("baseline_peak", "base peak"),
    ("coordinated_peak", "coord peak"),
    ("peak_reduction", "peak red."),
    ("slots_over_capacity", "slots>cap"),
    ("price_oscillation", "oscill"),
    ("escalations", "escal."),
    ("total_curtailed", "curtailed"),
    ("gini", "gini"),
    ("fairness_breach", "fair breach"),
    ("human_calls", "HITL calls"),
    ("human_approved", "HITL appr."),
    ("comfort_ok", "comfort"),
]


def fmt(key, value, row):
    if key == "peak_reduction":
        return "%+.0f%%" % (value * 100)
    if key in ("price_oscillation", "gini"):
        return "%.3f" % value
    if key in ("baseline_peak", "coordinated_peak", "total_curtailed"):
        return "%.0f" % value
    if key == "comfort_ok":
        return "%d/%d" % (value, row["total_homes"])
    return str(value)


def collect():
    rows = []
    for label, scen, inject, use_llm, no_human, stagger in MATRIX:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            m = run(scen, inject, use_llm, no_human, stagger)
        m["run"] = label
        rows.append(m)
    return rows


def write_markdown(rows):
    headers = [h for _, h in FIELDS]
    lines = [
        "# Evaluation results",
        "",
        "Reproduce with `python eval/run_all.py`. One row per run; metrics are the",
        "agent / interaction / system / human tiers from `docs/evaluation.md`.",
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for r in rows:
        cells = [fmt(k, r[k], r) for k, _ in FIELDS]
        lines.append("| " + " | ".join(cells) + " |")
    path = os.path.join(RESULTS_DIR, "summary.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def write_csv(rows):
    keys = [k for k, _ in FIELDS] + ["total_homes", "correlation_id"]
    path = os.path.join(RESULTS_DIR, "summary.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(keys)
        for r in rows:
            w.writerow([r[k] for k in keys])
    return path


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    rows = collect()
    md = write_markdown(rows)
    csv_path = write_csv(rows)

    # echo the table so the run is legible from the terminal too
    headers = [h for _, h in FIELDS]
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        print("| " + " | ".join(fmt(k, r[k], r) for k, _ in FIELDS) + " |")
    print("\nwrote %s" % os.path.relpath(md, REPO))
    print("wrote %s" % os.path.relpath(csv_path, REPO))


if __name__ == "__main__":
    main()
