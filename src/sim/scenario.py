"""Minimal scenario loader.

Uses PyYAML if available; otherwise falls back to a tiny hand-rolled parser for
the simple subset of YAML our scenarios use, so the project runs with zero
third-party dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Household:
    name: str
    base_load: list[float]
    flex_kw: float
    flex_slots_needed: int
    deadline_slot: int


@dataclass
class Scenario:
    name: str
    description: str
    slots: int
    slot_labels: list[str]
    feeder_capacity_kw: float
    target_kw: float
    price_cap: float
    initial_price: float
    storage: dict[str, Any]
    households: list[Household] = field(default_factory=list)
    flags: dict[str, Any] = field(default_factory=dict)


def _load_yaml(path: str) -> dict:
    try:
        import yaml  # type: ignore
        with open(path) as f:
            return yaml.safe_load(f)
    except ModuleNotFoundError:
        return _tiny_yaml(path)


def _tiny_yaml(path: str) -> dict:
    """Parse the limited YAML subset used by our scenario files."""
    import ast

    root: dict = {}
    stack = [(-1, root)]
    with open(path) as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        raw = lines[i].rstrip("\n")
        if not raw.strip() or raw.strip().startswith("#"):
            i += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if line.startswith("- "):
            item = line[2:].strip()
            if not isinstance(parent, list):
                continue
            if ":" in item:
                obj: dict = {}
                k, v = item.split(":", 1)
                obj[k.strip()] = _coerce(v.strip())
                parent.append(obj)
                stack.append((indent, obj))
                # subsequent indented "key: val" belong to this obj
            else:
                parent.append(_coerce(item))
            i += 1
            continue

        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "":
            # could be a list or a mapping; peek next line
            nxt = _peek_next(lines, i + 1)
            container: Any = [] if nxt and nxt.lstrip().startswith("- ") else {}
            if isinstance(parent, dict):
                parent[key] = container
            stack.append((indent, container))
        else:
            if isinstance(parent, dict):
                parent[key] = _coerce(val)
        i += 1
    return root


def _peek_next(lines, idx):
    while idx < len(lines):
        if lines[idx].strip() and not lines[idx].strip().startswith("#"):
            return lines[idx]
        idx += 1
    return None


def _coerce(v: str):
    import ast
    if v.startswith("[") or v.startswith("{"):
        try:
            return ast.literal_eval(v)
        except Exception:
            return v
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v.strip('"\'')


def load_scenario(path: str) -> Scenario:
    d = _load_yaml(path)
    households = [
        Household(
            name=h["name"],
            base_load=list(h["base_load"]),
            flex_kw=float(h["flex_kw"]),
            flex_slots_needed=int(h["flex_slots_needed"]),
            deadline_slot=int(h["deadline_slot"]),
        )
        for h in d.get("households", [])
    ]
    return Scenario(
        name=d["name"],
        description=d.get("description", ""),
        slots=int(d["slots"]),
        slot_labels=list(d.get("slot_labels", [str(i) for i in range(int(d["slots"]))])),
        feeder_capacity_kw=float(d["feeder_capacity_kw"]),
        target_kw=float(d["target_kw"]),
        price_cap=float(d["price_cap"]),
        initial_price=float(d.get("initial_price", 0.15)),
        storage=d.get("storage", {}),
        households=households,
        flags=d.get("flags", {}),
    )
