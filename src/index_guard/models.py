from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AuditScope = Literal["staged", "tracked"]


@dataclass(frozen=True, slots=True)
class IgnoreDecision:
    path: str
    ignored: bool
    source: str | None
    line: int | None
    pattern: str | None


@dataclass(frozen=True, slots=True)
class AuditReport:
    scope: AuditScope
    checked_paths: int
    findings: tuple[IgnoreDecision, ...]
