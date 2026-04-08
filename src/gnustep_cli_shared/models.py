from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    id: str
    title: str
    status: str
    severity: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


@dataclass
class Action:
    kind: str
    message: str
    priority: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "priority": self.priority,
            "message": self.message,
        }

