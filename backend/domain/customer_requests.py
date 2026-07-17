from __future__ import annotations

from enum import StrEnum


class CustomerRequestStatus(StrEnum):
    NEW = "new"
    REVIEWING = "reviewing"
    QUOTED = "quoted"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ProductCode(StrEnum):
    A3_FLYER = "a3_flyer"
    BRAND_STICKER = "brand_sticker"


REQUEST_TRANSITIONS: dict[CustomerRequestStatus, tuple[CustomerRequestStatus, ...]] = {
    CustomerRequestStatus.NEW: (CustomerRequestStatus.REVIEWING, CustomerRequestStatus.CANCELLED),
    CustomerRequestStatus.REVIEWING: (CustomerRequestStatus.QUOTED, CustomerRequestStatus.CANCELLED),
    CustomerRequestStatus.QUOTED: (CustomerRequestStatus.CLOSED, CustomerRequestStatus.CANCELLED),
    CustomerRequestStatus.CLOSED: (),
    CustomerRequestStatus.CANCELLED: (),
}


def allowed_transitions(status: CustomerRequestStatus) -> tuple[CustomerRequestStatus, ...]:
    return REQUEST_TRANSITIONS[status]


def is_terminal(status: CustomerRequestStatus) -> bool:
    return status in {CustomerRequestStatus.CLOSED, CustomerRequestStatus.CANCELLED}
