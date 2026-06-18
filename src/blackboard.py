"""Blackboard: the shared-state half of the hybrid coordination mechanism.

Agents read the blackboard opportunistically (current price, latest telemetry,
forecasts) without point-to-point messaging for every fact. Writes are
namespaced so it is always clear which domain owns a piece of state.

This is intentionally simple (a dict). What matters for the assignment is the
*role* it plays: a single, observable, auditable view of shared truth that sits
underneath the market and the safety supervisor.
"""
from __future__ import annotations

import copy
from typing import Any


class Blackboard:
    def __init__(self) -> None:
        self._state: dict[str, Any] = {}
        self._history: list[dict[str, Any]] = []

    def write(self, namespace: str, key: str, value: Any) -> None:
        self._state.setdefault(namespace, {})[key] = value

    def read(self, namespace: str, key: str, default: Any = None) -> Any:
        return self._state.get(namespace, {}).get(key, default)

    def read_namespace(self, namespace: str) -> dict[str, Any]:
        return copy.deepcopy(self._state.get(namespace, {}))

    def snapshot(self, label: str = "") -> dict[str, Any]:
        snap = {"label": label, "state": copy.deepcopy(self._state)}
        self._history.append(snap)
        return snap

    def history(self) -> list[dict[str, Any]]:
        return self._history
