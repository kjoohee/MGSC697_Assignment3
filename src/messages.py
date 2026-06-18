"""Communication contract for the smart-grid multi-agent system.

This module defines the message *envelope* every agent uses to talk to every
other agent. The envelope is deliberately strict: messages that fail validation
are rejected (NACK) and sent to a dead-letter queue rather than silently
processed. That is a safety property, not a convenience.

Nothing here is grid-specific. The payload carries the domain content; the
envelope carries identity, trust, ordering, and audit metadata.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

SCHEMA_VERSION = "1.0"

# A toy shared secret used to demonstrate message signing across A2A trust
# boundaries. In a real system each domain would hold its own key material and
# this would be asymmetric. Here it only needs to show *where* integrity matters.
_MOCK_SECRET = b"smartgrid-mas-demo-key"


class MsgType(str, Enum):
    TELEMETRY = "TELEMETRY"                    # grid/storage -> blackboard
    FORECAST = "FORECAST"                      # demand/solar forecast (carries confidence)
    PRICE_SIGNAL = "PRICE_SIGNAL"             # market -> broadcast
    BID = "BID"                               # household/aggregator/storage -> market
    CLEARING = "CLEARING"                     # market -> participants
    DISPATCH = "DISPATCH"                     # market -> storage
    CONSTRAINT = "CONSTRAINT"                 # grid -> market (physical limits)
    CURTAILMENT_REQUEST = "CURTAILMENT_REQUEST"  # grid -> households (last resort)
    ESCALATION = "ESCALATION"                 # grid -> regulator -> human
    OVERRIDE = "OVERRIDE"                     # human/regulator -> grid/market
    ACK = "ACK"
    NACK = "NACK"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EMERGENCY = "emergency"


# Trust domains correspond to A2A boundaries in the architecture. Messages that
# cross domains are the ones whose signatures actually matter.
class TrustDomain(str, Enum):
    CONSUMER = "consumer"          # households, aggregator
    MARKET = "market"             # market operator
    GRID = "grid"                 # DSO: grid + storage
    GOVERNANCE = "governance"     # regulator + human


@dataclass
class Message:
    sender: str
    recipient: str                 # agent name, or "*" for broadcast
    msg_type: MsgType
    trust_domain: TrustDomain
    payload: dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    confidence: Optional[float] = None         # for FORECAST-type messages
    correlation_id: str = ""                   # groups one coordination round
    schema_version: str = SCHEMA_VERSION
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signature: str = ""

    def signing_payload(self) -> bytes:
        # Signature covers the fields that establish identity + intent.
        basis = f"{self.msg_id}|{self.sender}|{self.recipient}|{self.msg_type}|{self.correlation_id}"
        return basis.encode()

    def sign(self) -> "Message":
        self.signature = hmac.new(_MOCK_SECRET, self.signing_payload(), hashlib.sha256).hexdigest()
        return self

    def verify(self) -> bool:
        expected = hmac.new(_MOCK_SECRET, self.signing_payload(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, self.signature)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["msg_type"] = self.msg_type.value
        d["priority"] = self.priority.value
        d["trust_domain"] = self.trust_domain.value
        return d


class ValidationError(Exception):
    pass


def validate(msg: Message) -> None:
    """Raise ValidationError if the message is malformed.

    Validation failures must never be silently dropped or guessed at; the bus
    converts a failure here into a NACK + dead-letter entry.
    """
    if msg.schema_version != SCHEMA_VERSION:
        raise ValidationError(f"unsupported schema_version {msg.schema_version!r}")
    if not msg.sender or not msg.recipient:
        raise ValidationError("sender and recipient are required")
    if not isinstance(msg.msg_type, MsgType):
        raise ValidationError("msg_type must be a MsgType")
    if not msg.correlation_id:
        raise ValidationError("correlation_id is required (audit/trace)")
    if msg.msg_type == MsgType.FORECAST and msg.confidence is None:
        raise ValidationError("FORECAST messages must carry a confidence")
    if msg.confidence is not None and not (0.0 <= msg.confidence <= 1.0):
        raise ValidationError("confidence must be in [0, 1]")
    if not msg.verify():
        raise ValidationError("signature verification failed")


def new_message(**kwargs: Any) -> Message:
    """Convenience factory that always returns a signed, valid message."""
    msg = Message(**kwargs)
    msg.sign()
    validate(msg)
    return msg
