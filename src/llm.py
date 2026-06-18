"""Optional LLM reasoning hook.

The core system is deterministic and rule-based so it runs anywhere, every time,
identically (good for grading and for reproducible safety demos). But the brief
is about *AI agents*, so we expose ONE clearly-bounded place where an agent can
defer a judgement call to an LLM:

    - The Grid agent uses it to write a human-readable escalation rationale.

Design choices that matter:
  - LLM is OFF by default. Enable with --use-llm AND an ANTHROPIC_API_KEY.
  - If the call fails or the key is absent, we fall back to a deterministic
    template. The system never depends on the LLM for a *safety* decision; the
    LLM only summarizes a decision the rules already made.

This keeps the system testable and keeps non-determinism out of the control path.
"""
from __future__ import annotations

import json
import os
import urllib.request


def _deterministic_rationale(context: dict) -> str:
    return (
        f"Feeder '{context.get('feeder')}' projected at "
        f"{context.get('load_kw'):.0f} kW against a {context.get('capacity_kw'):.0f} kW limit "
        f"({context.get('utilization', 0):.0%} utilization). Market price reached the "
        f"regulatory cap of {context.get('price_cap')} without clearing the overload. "
        f"Economic signals are exhausted; human authorization is required for "
        f"physical curtailment affecting {context.get('households_at_risk', 0)} households. "
        f"Recommend approving fairness-ordered curtailment."
    )


def escalation_rationale(context: dict, use_llm: bool = False) -> str:
    """Produce an escalation rationale. Falls back to a template unless LLM is on."""
    if not use_llm or not os.environ.get("ANTHROPIC_API_KEY"):
        return _deterministic_rationale(context)
    try:
        body = {
            "model": "claude-sonnet-4-6",
            "max_tokens": 300,
            "system": (
                "You are a grid-operations assistant. Given a JSON situation, write a "
                "concise (<=4 sentence) escalation rationale for a human operator. "
                "State the physical risk, that market price hit its cap, and the requested action. "
                "Do not invent numbers beyond those provided."
            ),
            "messages": [{"role": "user", "content": json.dumps(context)}],
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode(),
            headers={
                "content-type": "application/json",
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        return text.strip() or _deterministic_rationale(context)
    except Exception as e:  # never let the LLM break the control path
        return _deterministic_rationale(context) + f"  [llm-fallback: {type(e).__name__}]"
