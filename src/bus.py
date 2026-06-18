"""Message bus + audit log.

Routing modes:
  - direct:    recipient is a specific agent name
  - broadcast: recipient == "*" (e.g. PRICE_SIGNAL); delivered to all subscribers

Every message is validated before delivery. A malformed message is NOT delivered:
it is logged, NACK'd back to the sender, and parked in the dead-letter queue. This
is the "what happens to bad messages" safety story made concrete.

Every accepted message is appended to an immutable audit log keyed by
correlation_id, so any downstream action (a curtailment, an escalation) can be
traced back through the exact conversation that produced it.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable

from .messages import Message, MsgType, Priority, TrustDomain, ValidationError, validate, new_message

Handler = Callable[[Message], None]


class AuditLog:
    def __init__(self, path: str | None = None) -> None:
        self.path = path
        self.records: list[dict] = []
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # append-only: open in append mode, never truncate
            self._fh = open(path, "a", encoding="utf-8")
        else:
            self._fh = None

    def append(self, event: str, msg: Message | None = None, **extra) -> None:
        rec = {
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **extra,
        }
        if msg is not None:
            rec["message"] = msg.to_dict()
        self.records.append(rec)
        if self._fh:
            self._fh.write(json.dumps(rec) + "\n")
            self._fh.flush()

    def for_correlation(self, correlation_id: str) -> list[dict]:
        out = []
        for r in self.records:
            m = r.get("message")
            if m and m.get("correlation_id") == correlation_id:
                out.append(r)
        return out

    def close(self) -> None:
        if self._fh:
            self._fh.close()


class MessageBus:
    def __init__(self, audit: AuditLog | None = None) -> None:
        self._direct: dict[str, Handler] = {}
        self._subscribers: dict[MsgType, list[str]] = defaultdict(list)
        self.dead_letter: list[tuple[Message, str]] = []
        self.audit = audit or AuditLog()
        self.delivered = 0

    def register(self, name: str, handler: Handler) -> None:
        self._direct[name] = handler

    def subscribe(self, name: str, msg_type: MsgType) -> None:
        self._subscribers[msg_type].append(name)

    def _nack(self, original: Message, reason: str) -> None:
        self.dead_letter.append((original, reason))
        self.audit.append("NACK", original, reason=reason)
        # Best-effort NACK back to a known sender.
        if original.sender in self._direct:
            nack = new_message(
                sender="bus",
                recipient=original.sender,
                msg_type=MsgType.NACK,
                trust_domain=original.trust_domain,
                correlation_id=original.correlation_id or "bus-nack",
                payload={"reason": reason, "rejected_msg_id": original.msg_id},
                priority=Priority.HIGH,
            )
            self._direct[original.sender](nack)

    def publish(self, msg: Message) -> None:
        try:
            validate(msg)
        except ValidationError as e:
            self._nack(msg, str(e))
            return

        self.audit.append("DELIVER", msg)
        self.delivered += 1

        if msg.recipient == "*":
            for name in self._subscribers.get(msg.msg_type, []):
                if name in self._direct:
                    self._direct[name](msg)
        else:
            handler = self._direct.get(msg.recipient)
            if handler is None:
                self._nack(msg, f"unknown recipient {msg.recipient!r}")
                return
            handler(msg)
