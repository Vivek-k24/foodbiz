from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderLineModifier:
    code: str
    label: str
    value: str

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("modifier code must be non-empty")
        if not self.label.strip():
            raise ValueError("modifier label must be non-empty")
