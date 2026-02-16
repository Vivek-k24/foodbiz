from __future__ import annotations

from typing import Protocol


class EventPublisher(Protocol):
    def publish(self, channel: str, message: str) -> None: ...
