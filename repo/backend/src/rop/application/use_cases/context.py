from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TraceContext:
    trace_id: str | None
    request_id: str | None
