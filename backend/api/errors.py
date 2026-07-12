from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ApiError(Exception):
    status_code: int
    code: str
    detail: str
    field_errors: list[dict[str, str]] = field(default_factory=list)
