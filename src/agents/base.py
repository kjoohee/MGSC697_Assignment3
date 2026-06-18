"""Base agent: identity, trust domain, explicit permissions, bus wiring."""
from __future__ import annotations

from ..bus import MessageBus
from ..messages import Message, TrustDomain


class Agent:
    #: subclasses declare which MsgTypes they accept; everything else is logged + ignored
    accepts: tuple = ()

    def __init__(self, name: str, trust_domain: TrustDomain, bus: MessageBus,
                 permissions: set[str] | None = None) -> None:
        self.name = name
        self.trust_domain = trust_domain
        self.bus = bus
        self.permissions = permissions or set()
        self.inbox: list[Message] = []
        bus.register(name, self._receive)

    # --- permissions -------------------------------------------------------
    def can(self, permission: str) -> bool:
        return permission in self.permissions

    def require(self, permission: str) -> None:
        if not self.can(permission):
            raise PermissionError(f"{self.name} lacks permission '{permission}'")

    # --- messaging ---------------------------------------------------------
    def _receive(self, msg: Message) -> None:
        self.inbox.append(msg)
        self.handle(msg)

    def handle(self, msg: Message) -> None:  # override
        pass

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name} [{self.trust_domain.value}]>"
