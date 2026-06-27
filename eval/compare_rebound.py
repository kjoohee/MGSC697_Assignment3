"""Failure-vs-mitigation comparison for the rebound (synchronized) peak.

The headline emergent failure (docs/emergence.md) is the rebound peak: tell every
household the single cheapest slot and they all pile in, creating a NEW peak. The
mitigation is `stagger_targets`, which spreads them across cheap slots.

This script runs the same heatwave scenario twice -- staggering OFF (the failure)
vs ON (the fix) -- and prints them side by side so "watch it fail, watch the fix
work" is one legible artifact.

Run from anywhere:
    python eval/compare_rebound.py
"""
from __future__ import annotations

import contextlib
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
os.chdir(REPO)

from src.sim.run import run  # noqa: E402

SCENARIO = "scenarios/heatwave_peak.yaml"
ROWS = [
    ("coordinated_peak", "coordinated peak (kW)", "%.0f"),
    ("peak_reduction", "peak reduction", "%+.0f%%"),
    ("price_oscillation", "price oscillation ($/kWh)", "%.3f"),
    ("slots_over_capacity", "slots over capacity", "%d"),
]


def run_quiet(stagger):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return run(SCENARIO, None, False, False, stagger)


def cell(key, fmt, m):
    v = m[key] * 100 if key == "peak_reduction" else m[key]
    return fmt % v


def main():
    off = run_quiet(False)  # rebound mitigation OFF -> the failure
    on = run_quiet(True)    # rebound mitigation ON  -> the fix

    print("Rebound peak: failure (stagger OFF) vs mitigation (stagger ON)")
    print("scenario: %s\n" % SCENARIO)
    w = max(len(label) for _, label, _ in ROWS)
    print("%-*s | %12s | %12s" % (w, "metric", "stagger OFF", "stagger ON"))
    print("%s-+-%s-+-%s" % ("-" * w, "-" * 12, "-" * 12))
    for key, label, fmt in ROWS:
        print("%-*s | %12s | %12s" % (w, label, cell(key, fmt, off), cell(key, fmt, on)))

    better = on["coordinated_peak"] <= off["coordinated_peak"]
    delta = off["coordinated_peak"] - on["coordinated_peak"]
    print()
    if better:
        print("Verdict: staggering lowers the coordinated peak by %.0f kW "
              "(and does not raise oscillation) -- the mitigation works." % delta)
    else:
        print("Verdict: staggering did NOT lower the peak in this scenario "
              "(review parameters).")


if __name__ == "__main__":
    main()
