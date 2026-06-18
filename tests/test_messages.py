"""Tests for the communication contract and bus safety behavior.

Run with:  python -m pytest -q     (or)     python -m unittest -q
"""
import unittest

from src.messages import (
    Message, MsgType, Priority, TrustDomain, ValidationError, validate, new_message,
)
from src.bus import MessageBus, AuditLog


class TestMessageContract(unittest.TestCase):
    def test_valid_message_passes(self):
        m = new_message(
            sender="market_agent", recipient="*", msg_type=MsgType.PRICE_SIGNAL,
            trust_domain=TrustDomain.MARKET, correlation_id="round-1",
            payload={"slot": 0, "price": 0.2},
        )
        validate(m)  # should not raise

    def test_missing_correlation_id_rejected(self):
        m = Message(sender="a", recipient="b", msg_type=MsgType.BID,
                    trust_domain=TrustDomain.CONSUMER).sign()
        with self.assertRaises(ValidationError):
            validate(m)

    def test_forecast_requires_confidence(self):
        m = Message(sender="a", recipient="b", msg_type=MsgType.FORECAST,
                    trust_domain=TrustDomain.GRID, correlation_id="r1").sign()
        with self.assertRaises(ValidationError):
            validate(m)

    def test_tampered_signature_fails(self):
        m = new_message(sender="a", recipient="b", msg_type=MsgType.BID,
                        trust_domain=TrustDomain.CONSUMER, correlation_id="r1")
        m.payload["price"] = 999          # tamper after signing
        m.sender = "attacker"             # change identity -> signature no longer matches
        with self.assertRaises(ValidationError):
            validate(m)

    def test_confidence_out_of_range_rejected(self):
        m = Message(sender="a", recipient="b", msg_type=MsgType.FORECAST,
                    trust_domain=TrustDomain.GRID, correlation_id="r1",
                    confidence=1.5).sign()
        with self.assertRaises(ValidationError):
            validate(m)


class TestBusSafety(unittest.TestCase):
    def test_unknown_recipient_goes_to_dead_letter(self):
        bus = MessageBus(AuditLog())
        m = new_message(sender="a", recipient="ghost", msg_type=MsgType.BID,
                        trust_domain=TrustDomain.CONSUMER, correlation_id="r1")
        # register the sender so it can receive the NACK
        received = []
        bus.register("a", lambda msg: received.append(msg))
        bus.publish(m)
        self.assertEqual(len(bus.dead_letter), 1)
        self.assertTrue(any(r.msg_type == MsgType.NACK for r in received))

    def test_broadcast_reaches_subscribers(self):
        bus = MessageBus(AuditLog())
        got = []
        bus.register("sub1", lambda msg: got.append(("sub1", msg)))
        bus.register("sub2", lambda msg: got.append(("sub2", msg)))
        bus.subscribe("sub1", MsgType.PRICE_SIGNAL)
        bus.subscribe("sub2", MsgType.PRICE_SIGNAL)
        m = new_message(sender="market", recipient="*", msg_type=MsgType.PRICE_SIGNAL,
                        trust_domain=TrustDomain.MARKET, correlation_id="r1",
                        payload={"price": 0.2})
        bus.publish(m)
        self.assertEqual(len(got), 2)

    def test_audit_log_traces_by_correlation(self):
        bus = MessageBus(AuditLog())
        bus.register("b", lambda msg: None)
        m = new_message(sender="a", recipient="b", msg_type=MsgType.BID,
                        trust_domain=TrustDomain.CONSUMER, correlation_id="trace-me")
        bus.publish(m)
        self.assertEqual(len(bus.audit.for_correlation("trace-me")), 1)


if __name__ == "__main__":
    unittest.main()
