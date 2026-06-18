# Communication Contract

## Envelope (`src/messages.py`)

| Field | Purpose |
|---|---|
| `schema_version` | reject unsupported versions |
| `msg_id` | unique id |
| `correlation_id` | groups one coordination round; the key the audit log traces on |
| `timestamp` | ISO-8601 UTC |
| `sender`, `recipient` | identity; `recipient="*"` means broadcast |
| `msg_type` | enum (below) |
| `trust_domain` | which A2A domain the sender is in |
| `priority` | low / normal / high / emergency |
| `payload` | message-type-specific content |
| `confidence` | required for FORECAST messages, in [0,1] |
| `signature` | HMAC over identity+intent; verified on receipt |

## Message types
`TELEMETRY, FORECAST, PRICE_SIGNAL, BID, CLEARING, DISPATCH, CONSTRAINT,
CURTAILMENT_REQUEST, ESCALATION, OVERRIDE, ACK, NACK`

## Routing
- `PRICE_SIGNAL` -> **broadcast** (pub/sub; published to the blackboard, read by all).
- `BID`, `CONSTRAINT`, `DISPATCH`, `CLEARING`, `CURTAILMENT_REQUEST`, `ESCALATION`,
  `OVERRIDE` -> **direct**.

## Escalation path
`Grid -> Regulator -> Human`, triggered when a slot is physically overloaded
**and** price is already at the regulatory cap (economics exhausted).

## Failure handling (safety, not convenience)
Every message is validated before delivery (`src/bus.py`). On failure the bus:
1. records the failure in the audit log,
2. returns a `NACK` to the sender (if known),
3. parks the message in a **dead-letter queue**.
Unknown recipients are rejected, not silently dropped. Tampered cross-domain
messages fail signature verification. See `tests/test_messages.py`.

## Validation rules (enforced)
- known `schema_version`; non-empty `sender`/`recipient`; valid `msg_type`
- `correlation_id` required (traceability)
- `FORECAST` must carry `confidence` in [0,1]
- signature must verify
