"""Transform a supplied V1 read-only JSON export without opening either database."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.v1_export_transform import (
    V1ExportValidationError,
    build_quarantine_report,
    transform_readonly_v1_export,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a V2 migration manifest from a V1 read-only export")
    parser.add_argument("--input", required=True, type=Path, help="Versioned V1 read-only JSON export")
    parser.add_argument("--manifest", required=True, type=Path, help="Output V2 import manifest path")
    parser.add_argument("--quarantine-report", required=True, type=Path, help="Output quarantine report path")
    parser.add_argument("--require-clean", action="store_true", help="Return nonzero when manual review is required")
    arguments = parser.parse_args()

    input_path = arguments.input.resolve()
    manifest_path = arguments.manifest.resolve()
    report_path = arguments.quarantine_report.resolve()
    if input_path in {manifest_path, report_path} or manifest_path == report_path:
        print("v1_export_transform=BLOCKED output_paths_invalid")
        return 1
    try:
        document = json.loads(input_path.read_text(encoding="utf-8-sig"))
        if not isinstance(document, dict):
            raise V1ExportValidationError("The supplied export root must be an object")
        manifest = transform_readonly_v1_export(document)
        _write_json(manifest_path, manifest)
        _write_json(report_path, build_quarantine_report(manifest))
    except (OSError, json.JSONDecodeError, V1ExportValidationError):
        print("v1_export_transform=BLOCKED invalid_input")
        return 1

    summary = manifest["summary"]
    print("v1_export_transform=COMPLETE")
    print(f"accepted_record_count={summary['accepted_record_count']}")
    print(f"validated_legacy_price_evidence_count={summary['validated_legacy_price_evidence_count']}")
    print(f"quarantined_record_count={summary['quarantined_record_count']}")
    print(f"manual_review_required={summary['manual_review_required']}")
    print("database_writes_performed=False")
    if arguments.require_clean and summary["manual_review_required"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
