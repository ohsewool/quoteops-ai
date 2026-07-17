from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys

import pytest

from backend.services.v1_export_transform import (
    V1ExportValidationError,
    build_quarantine_report,
    transform_readonly_v1_export,
)


def _export_document() -> dict[str, object]:
    return {
        "format": "quoteops-v1-readonly-export",
        "format_version": "v1",
        "exported_at": "2026-07-17T12:00:00+00:00",
        "export_id": "review-fixture-001",
        "products": [
            {
                "id": 1,
                "name": "A3 Flyer",
                "sku": "a3_flyer",
                "description": "Synthetic migration fixture",
                "active": True,
            },
            {
                "id": 2,
                "name": "Product / Brand Sticker",
                "sku": "brand_sticker",
                "description": None,
                "active": True,
            },
        ],
        "cost_profiles": [
            {
                "id": 11,
                "product_id": 1,
                "material_cost": "100.00",
                "labor_cost": "50.00",
                "overhead_cost": "50.00",
                "target_margin_rate": "0.250000",
                "active": True,
            },
            {
                "id": 12,
                "product_id": 2,
                "material_cost": "80.00",
                "labor_cost": "40.00",
                "overhead_cost": "30.00",
                "target_margin_rate": "0.350000",
                "active": True,
            },
        ],
        "price_table_items": [
            {
                "id": 21,
                "price_table_id": 91,
                "product_id": 1,
                "price": "266.67",
                "margin_rate": "0.250000",
            }
        ],
    }


def test_transform_accepts_supported_decimal_text_and_preserves_input() -> None:
    document = _export_document()
    original = deepcopy(document)

    manifest = transform_readonly_v1_export(document)

    assert document == original
    assert manifest["summary"] == {
        "source_record_count": 5,
        "accepted_record_count": 4,
        "validated_legacy_price_evidence_count": 1,
        "quarantined_record_count": 0,
        "manual_review_required": False,
        "database_writes_performed": False,
    }
    assert manifest["accepted"]["products"] == [
        {
            "source_id": 1,
            "code": "a3_flyer",
            "name": "A3 Flyer",
            "description": "Synthetic migration fixture",
            "active": True,
        },
        {
            "source_id": 2,
            "code": "brand_sticker",
            "name": "Product / Brand Sticker",
            "description": None,
            "active": True,
        },
    ]
    assert manifest["accepted"]["cost_profiles"][0] == {
        "source_id": 11,
        "product_code": "a3_flyer",
        "material_cost": "100.00",
        "labor_cost": "50.00",
        "overhead_cost": "50.00",
        "target_margin_rate": "0.250000",
        "active": True,
    }
    assert manifest["validated_legacy_price_evidence"] == [
        {
            "source_id": 21,
            "product_code": "a3_flyer",
            "observed_price": "266.67",
            "recomputed_price": "266.67",
            "difference_krw": "0.00",
        }
    ]
    assert len(manifest["source"]["sha256"]) == 64


def test_transform_quarantines_non_exact_values_drift_and_unsupported_sections() -> None:
    document = _export_document()
    document["products"].append(
        {"id": 3, "name": "Unsupported", "sku": "mug", "description": None, "active": True}
    )
    document["cost_profiles"][1]["material_cost"] = 80.0
    document["price_table_items"][0]["price"] = "300.00"
    document["customer_quote_requests"] = [{"id": 501, "customer_name": "Synthetic only"}]

    manifest = transform_readonly_v1_export(document)

    reasons = {(item["entity_type"], item["source_id"], item["reason_code"]) for item in manifest["quarantine"]}
    assert ("products", 3, "unsupported_product_sku") in reasons
    assert ("cost_profiles", 12, "invalid_monetary_or_rate_decimal_text") in reasons
    assert ("price_table_items", 21, "price_recomputation_mismatch") in reasons
    assert ("customer_quote_requests", 501, "unsupported_export_section") in reasons
    assert manifest["summary"]["manual_review_required"] is True
    assert manifest["summary"]["database_writes_performed"] is False
    report = build_quarantine_report(manifest)
    assert report["quarantined_record_count"] == 4
    assert "Synthetic only" not in str(report)


def test_transform_quarantines_multiple_active_profiles_for_one_product() -> None:
    document = _export_document()
    document["cost_profiles"].append(
        {
            "id": 13,
            "product_id": 1,
            "material_cost": "100.00",
            "labor_cost": "50.00",
            "overhead_cost": "50.00",
            "target_margin_rate": "0.250000",
            "active": True,
        }
    )

    manifest = transform_readonly_v1_export(document)

    reasons = {(item["source_id"], item["reason_code"]) for item in manifest["quarantine"]}
    assert (11, "multiple_active_cost_profiles") in reasons
    assert (13, "multiple_active_cost_profiles") in reasons
    assert (21, "active_cost_profile_not_migratable") in reasons
    assert {profile["source_id"] for profile in manifest["accepted"]["cost_profiles"]} == {12}


def test_transform_rejects_sensitive_export_fields_before_writing_any_manifest() -> None:
    document = _export_document()
    document["products"][0]["password_hash"] = "must-not-be-exported"

    with pytest.raises(V1ExportValidationError, match="prohibited sensitive fields"):
        transform_readonly_v1_export(document)


def test_recomputation_tolerance_is_exactly_one_krw_cent() -> None:
    document = _export_document()
    document["price_table_items"][0]["price"] = "266.68"

    manifest = transform_readonly_v1_export(document)

    assert manifest["quarantine"] == []
    difference = manifest["validated_legacy_price_evidence"][0]["difference_krw"]
    assert Decimal(difference) == Decimal("0.01")


def test_cli_accepts_utf8_bom_readonly_exports_and_writes_no_database() -> None:
    from tempfile import TemporaryDirectory

    project_root = Path(__file__).resolve().parents[2]
    with TemporaryDirectory() as directory:
        temporary_root = Path(directory)
        input_path = temporary_root / "readonly-export.json"
        manifest_path = temporary_root / "manifest.json"
        report_path = temporary_root / "quarantine.json"
        input_path.write_text(json.dumps(_export_document()), encoding="utf-8-sig")

        completed = subprocess.run(
            [
                sys.executable,
                "scripts/transform_v1_readonly_export.py",
                "--input",
                str(input_path),
                "--manifest",
                str(manifest_path),
                "--quarantine-report",
                str(report_path),
                "--require-clean",
            ],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
    assert completed.returncode == 0
    assert "v1_export_transform=COMPLETE" in completed.stdout
    assert "database_writes_performed=False" in completed.stdout
    assert manifest["summary"]["database_writes_performed"] is False
    assert report["quarantined_record_count"] == 0
