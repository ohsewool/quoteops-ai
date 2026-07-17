"""Pure V1 export transformation for the V2-10 migration review gate.

The transformer accepts an explicitly supplied, versioned JSON export. It does
not open a V1 connection and it does not write to a V2 database. Its output is
a deterministic import manifest plus an explicit quarantine list for a human
reviewer to approve before any separate staging import is attempted.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from backend.domain.money import decimal_string, quantize_money, quantize_rate


V1_EXPORT_FORMAT = "quoteops-v1-readonly-export"
V1_EXPORT_VERSION = "v1"
V2_IMPORT_MANIFEST_FORMAT = "quoteops-v2-import-manifest"
V2_MIGRATION_VERSION = "v2-10-v1-transform-v1"
V2_QUARANTINE_REPORT_FORMAT = "quoteops-v2-migration-quarantine-report"
RECOMPUTATION_TOLERANCE_KRW = Decimal("0.01")

_SUPPORTED_TOP_LEVEL_SECTIONS = ("products", "cost_profiles", "price_table_items")
_ALLOWED_TOP_LEVEL_KEYS = {
    "format",
    "format_version",
    "exported_at",
    "export_id",
    *_SUPPORTED_TOP_LEVEL_SECTIONS,
}
_SENSITIVE_KEY_MARKERS = ("password", "secret", "token", "api_key", "database_url", "connection_string")
_SKU_NORMALIZER = re.compile(r"[^a-z0-9]+")
_PRODUCT_CODE_BY_SKU = {
    "a3_flyer": "a3_flyer",
    "a3flyer": "a3_flyer",
    "brand_sticker": "brand_sticker",
    "product_brand_sticker": "brand_sticker",
}


class V1ExportValidationError(ValueError):
    """Raised when a supplied export is not safe or compatible to transform."""


def _contains_sensitive_key(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = str(key).lower()
            if any(marker in normalized_key for marker in _SENSITIVE_KEY_MARKERS):
                return True
            if _contains_sensitive_key(child):
                return True
    elif isinstance(value, list):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def _canonical_json_bytes(document: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(document, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise V1ExportValidationError("The supplied export is not valid JSON-compatible data") from error


def _positive_id(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _required_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return _required_text(value)


def _canonical_sku(value: str) -> str:
    return _SKU_NORMALIZER.sub("_", value.lower()).strip("_")


def _parse_decimal_text(value: object, *, rate: bool = False) -> Decimal | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = Decimal(raw)
    except InvalidOperation:
        return None
    if not parsed.is_finite() or parsed < 0:
        return None
    try:
        normalized = quantize_rate(parsed) if rate else quantize_money(parsed)
    except (InvalidOperation, TypeError, ValueError):
        return None
    if parsed != normalized:
        return None
    if rate and parsed >= Decimal("1"):
        return None
    return normalized


def _append_quarantine(
    quarantine: list[dict[str, Any]],
    *,
    entity_type: str,
    source_id: int | None,
    reason_code: str,
) -> None:
    quarantine.append(
        {
            "entity_type": entity_type,
            "source_id": source_id,
            "reason_code": reason_code,
        }
    )


def _validate_export_document(document: Mapping[str, Any]) -> None:
    if document.get("format") != V1_EXPORT_FORMAT or document.get("format_version") != V1_EXPORT_VERSION:
        raise V1ExportValidationError("The export format or version is not supported")
    exported_at = _required_text(document.get("exported_at"))
    if exported_at is None:
        raise V1ExportValidationError("The export timestamp is required")
    try:
        parsed_exported_at = datetime.fromisoformat(exported_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise V1ExportValidationError("The export timestamp is invalid") from error
    if parsed_exported_at.tzinfo is None or parsed_exported_at.utcoffset() is None:
        raise V1ExportValidationError("The export timestamp must include a timezone")
    if _contains_sensitive_key(document):
        raise V1ExportValidationError("The export contains prohibited sensitive fields")
    for section in _SUPPORTED_TOP_LEVEL_SECTIONS:
        records = document.get(section, [])
        if not isinstance(records, list):
            raise V1ExportValidationError(f"The {section} section must be a list")
        if len(records) > 10_000:
            raise V1ExportValidationError(f"The {section} section exceeds the supported record limit")


def _transform_products(records: list[Any], quarantine: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[int, str]]:
    candidates: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping):
            _append_quarantine(quarantine, entity_type="products", source_id=None, reason_code="invalid_record_shape")
            continue
        source_id = _positive_id(record.get("id"))
        if source_id is None:
            _append_quarantine(quarantine, entity_type="products", source_id=None, reason_code="invalid_source_id")
            continue
        sku = _required_text(record.get("sku"))
        code = _PRODUCT_CODE_BY_SKU.get(_canonical_sku(sku)) if sku else None
        if code is None:
            _append_quarantine(quarantine, entity_type="products", source_id=source_id, reason_code="unsupported_product_sku")
            continue
        name = _required_text(record.get("name"))
        active = record.get("active")
        description = _optional_text(record.get("description"))
        if name is None or not isinstance(active, bool) or (record.get("description") is not None and description is None):
            _append_quarantine(quarantine, entity_type="products", source_id=source_id, reason_code="invalid_product_fields")
            continue
        candidates.append(
            {
                "source_id": source_id,
                "code": code,
                "name": name,
                "description": description,
                "active": active,
            }
        )

    source_id_counts = Counter(candidate["source_id"] for candidate in candidates)
    code_counts = Counter(candidate["code"] for candidate in candidates)
    accepted: list[dict[str, Any]] = []
    source_product_codes: dict[int, str] = {}
    for candidate in candidates:
        if source_id_counts[candidate["source_id"]] > 1:
            _append_quarantine(
                quarantine,
                entity_type="products",
                source_id=candidate["source_id"],
                reason_code="duplicate_source_id",
            )
            continue
        if code_counts[candidate["code"]] > 1:
            _append_quarantine(
                quarantine,
                entity_type="products",
                source_id=candidate["source_id"],
                reason_code="duplicate_v2_product_code",
            )
            continue
        accepted.append(candidate)
        source_product_codes[candidate["source_id"]] = candidate["code"]
    return accepted, source_product_codes


def _transform_cost_profiles(
    records: list[Any],
    source_product_codes: Mapping[int, str],
    quarantine: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping):
            _append_quarantine(quarantine, entity_type="cost_profiles", source_id=None, reason_code="invalid_record_shape")
            continue
        source_id = _positive_id(record.get("id"))
        if source_id is None:
            _append_quarantine(quarantine, entity_type="cost_profiles", source_id=None, reason_code="invalid_source_id")
            continue
        product_id = _positive_id(record.get("product_id"))
        product_code = source_product_codes.get(product_id) if product_id is not None else None
        if product_code is None:
            _append_quarantine(quarantine, entity_type="cost_profiles", source_id=source_id, reason_code="source_product_not_migrated")
            continue
        material_cost = _parse_decimal_text(record.get("material_cost"))
        labor_cost = _parse_decimal_text(record.get("labor_cost"))
        overhead_cost = _parse_decimal_text(record.get("overhead_cost"))
        target_margin_rate = _parse_decimal_text(record.get("target_margin_rate"), rate=True)
        active = record.get("active")
        if (
            material_cost is None
            or labor_cost is None
            or overhead_cost is None
            or target_margin_rate is None
            or not isinstance(active, bool)
        ):
            _append_quarantine(
                quarantine,
                entity_type="cost_profiles",
                source_id=source_id,
                reason_code="invalid_monetary_or_rate_decimal_text",
            )
            continue
        candidates.append(
            {
                "source_id": source_id,
                "product_code": product_code,
                "material_cost": material_cost,
                "labor_cost": labor_cost,
                "overhead_cost": overhead_cost,
                "target_margin_rate": target_margin_rate,
                "active": active,
            }
        )

    source_id_counts = Counter(candidate["source_id"] for candidate in candidates)
    active_by_product = Counter(candidate["product_code"] for candidate in candidates if candidate["active"])
    accepted: list[dict[str, Any]] = []
    active_cost_profiles: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if source_id_counts[candidate["source_id"]] > 1:
            _append_quarantine(
                quarantine,
                entity_type="cost_profiles",
                source_id=candidate["source_id"],
                reason_code="duplicate_source_id",
            )
            continue
        if candidate["active"] and active_by_product[candidate["product_code"]] > 1:
            _append_quarantine(
                quarantine,
                entity_type="cost_profiles",
                source_id=candidate["source_id"],
                reason_code="multiple_active_cost_profiles",
            )
            continue
        accepted.append(
            {
                "source_id": candidate["source_id"],
                "product_code": candidate["product_code"],
                "material_cost": decimal_string(candidate["material_cost"]),
                "labor_cost": decimal_string(candidate["labor_cost"]),
                "overhead_cost": decimal_string(candidate["overhead_cost"]),
                "target_margin_rate": decimal_string(candidate["target_margin_rate"], rate=True),
                "active": candidate["active"],
            }
        )
        if candidate["active"]:
            active_cost_profiles[candidate["product_code"]] = candidate
    return accepted, active_cost_profiles


def _validate_price_table_items(
    records: list[Any],
    source_product_codes: Mapping[int, str],
    active_cost_profiles: Mapping[str, Mapping[str, Any]],
    quarantine: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping):
            _append_quarantine(quarantine, entity_type="price_table_items", source_id=None, reason_code="invalid_record_shape")
            continue
        source_id = _positive_id(record.get("id"))
        if source_id is None:
            _append_quarantine(quarantine, entity_type="price_table_items", source_id=None, reason_code="invalid_source_id")
            continue
        product_id = _positive_id(record.get("product_id"))
        product_code = source_product_codes.get(product_id) if product_id is not None else None
        if product_code is None:
            _append_quarantine(
                quarantine,
                entity_type="price_table_items",
                source_id=source_id,
                reason_code="source_product_not_migrated",
            )
            continue
        active_cost_profile = active_cost_profiles.get(product_code)
        if active_cost_profile is None:
            _append_quarantine(
                quarantine,
                entity_type="price_table_items",
                source_id=source_id,
                reason_code="active_cost_profile_not_migratable",
            )
            continue
        observed_price = _parse_decimal_text(record.get("price"))
        margin_rate = _parse_decimal_text(record.get("margin_rate"), rate=True)
        if observed_price is None or margin_rate is None:
            _append_quarantine(
                quarantine,
                entity_type="price_table_items",
                source_id=source_id,
                reason_code="invalid_monetary_or_rate_decimal_text",
            )
            continue
        unit_cost = (
            active_cost_profile["material_cost"]
            + active_cost_profile["labor_cost"]
            + active_cost_profile["overhead_cost"]
        )
        recomputed_price = quantize_money(unit_cost / (Decimal("1") - margin_rate))
        difference = abs(observed_price - recomputed_price)
        if difference > RECOMPUTATION_TOLERANCE_KRW:
            _append_quarantine(
                quarantine,
                entity_type="price_table_items",
                source_id=source_id,
                reason_code="price_recomputation_mismatch",
            )
            continue
        evidence.append(
            {
                "source_id": source_id,
                "product_code": product_code,
                "observed_price": decimal_string(observed_price),
                "recomputed_price": decimal_string(recomputed_price),
                "difference_krw": decimal_string(difference),
            }
        )
    return evidence


def _quarantine_unsupported_sections(document: Mapping[str, Any], quarantine: list[dict[str, Any]]) -> None:
    for section, value in document.items():
        if section in _ALLOWED_TOP_LEVEL_KEYS:
            continue
        if isinstance(value, list):
            for record in value:
                source_id = _positive_id(record.get("id")) if isinstance(record, Mapping) else None
                _append_quarantine(
                    quarantine,
                    entity_type=str(section),
                    source_id=source_id,
                    reason_code="unsupported_export_section",
                )
        else:
            _append_quarantine(
                quarantine,
                entity_type=str(section),
                source_id=None,
                reason_code="unsupported_export_section",
            )


def transform_readonly_v1_export(document: Mapping[str, Any]) -> dict[str, Any]:
    """Build a deterministic, database-free V2 import manifest from a V1 export."""

    _validate_export_document(document)
    source_sha256 = hashlib.sha256(_canonical_json_bytes(document)).hexdigest()
    quarantine: list[dict[str, Any]] = []
    _quarantine_unsupported_sections(document, quarantine)
    products, source_product_codes = _transform_products(document.get("products", []), quarantine)
    cost_profiles, active_cost_profiles = _transform_cost_profiles(
        document.get("cost_profiles", []), source_product_codes, quarantine
    )
    price_evidence = _validate_price_table_items(
        document.get("price_table_items", []), source_product_codes, active_cost_profiles, quarantine
    )
    source_record_count = sum(
        len(value) if isinstance(value, list) else 1
        for key, value in document.items()
        if key not in {"format", "format_version", "exported_at", "export_id"}
    )
    accepted_record_count = len(products) + len(cost_profiles)
    return {
        "manifest_format": V2_IMPORT_MANIFEST_FORMAT,
        "migration_version": V2_MIGRATION_VERSION,
        "source": {
            "format": V1_EXPORT_FORMAT,
            "format_version": V1_EXPORT_VERSION,
            "exported_at": document["exported_at"],
            "sha256": source_sha256,
        },
        "accepted": {
            "products": products,
            "cost_profiles": cost_profiles,
        },
        "validated_legacy_price_evidence": price_evidence,
        "quarantine": quarantine,
        "summary": {
            "source_record_count": source_record_count,
            "accepted_record_count": accepted_record_count,
            "validated_legacy_price_evidence_count": len(price_evidence),
            "quarantined_record_count": len(quarantine),
            "manual_review_required": bool(quarantine),
            "database_writes_performed": False,
        },
    }


def build_quarantine_report(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return a shareable, secret-free quarantine report from one transform result."""

    summary = manifest.get("summary", {})
    source = manifest.get("source", {})
    quarantine = manifest.get("quarantine", [])
    return {
        "report_format": V2_QUARANTINE_REPORT_FORMAT,
        "migration_version": V2_MIGRATION_VERSION,
        "source_sha256": source.get("sha256"),
        "quarantined_record_count": summary.get("quarantined_record_count", 0),
        "manual_review_required": summary.get("manual_review_required", True),
        "items": quarantine,
    }
