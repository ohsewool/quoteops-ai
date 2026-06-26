import csv
from datetime import datetime
from io import StringIO

from sqlalchemy.orm import Session

from backend.models import Competitor, CompetitorPrice, CostProfile, Product
from backend.schemas import CsvImportError, CsvImportSummary


CSV_NOTES = [
    "CSV import completed deterministically.",
    "No AI was used to modify imported data.",
]


def import_products_csv(db: Session, content: bytes) -> CsvImportSummary:
    rows, errors = _read_csv(content)
    created_rows = 0
    updated_rows = 0
    row_errors: list[CsvImportError] = errors

    for row_number, row in rows:
        missing = _missing_required(row, ["name", "sku", "category"])
        if missing:
            row_errors.append(_error(row_number, f"Missing required column: {missing}"))
            continue

        product = db.query(Product).filter(Product.sku == row["sku"].strip()).first()
        values = {
            "name": row["name"].strip(),
            "sku": row["sku"].strip(),
            "category": row["category"].strip(),
            "description": _optional_text(row.get("description")),
            "active": _parse_bool(row.get("active"), True),
        }
        if product is None:
            db.add(Product(**values))
            created_rows += 1
        else:
            for key, value in values.items():
                setattr(product, key, value)
            updated_rows += 1

    db.commit()
    return _summary("products", len(rows), created_rows, updated_rows, row_errors)


def import_cost_profiles_csv(db: Session, content: bytes) -> CsvImportSummary:
    rows, errors = _read_csv(content)
    created_rows = 0
    updated_rows = 0
    row_errors: list[CsvImportError] = errors

    for row_number, row in rows:
        missing = _missing_required(
            row,
            [
                "product_sku",
                "material_cost",
                "labor_cost",
                "overhead_cost",
                "target_margin_rate",
            ],
        )
        if missing:
            row_errors.append(_error(row_number, f"Missing required column: {missing}"))
            continue

        product = db.query(Product).filter(Product.sku == row["product_sku"].strip()).first()
        if product is None:
            row_errors.append(_error(row_number, "Product not found for product_sku"))
            continue

        values = _cost_profile_values(row_number, row, row_errors)
        if values is None:
            continue

        cost_profile = (
            db.query(CostProfile)
            .filter(CostProfile.product_id == product.id, CostProfile.active.is_(True))
            .order_by(CostProfile.id.desc())
            .first()
        )
        values["product_id"] = product.id
        if cost_profile is None:
            db.add(CostProfile(**values))
            created_rows += 1
        else:
            for key, value in values.items():
                setattr(cost_profile, key, value)
            updated_rows += 1

    db.commit()
    return _summary("cost_profiles", len(rows), created_rows, updated_rows, row_errors)


def import_competitor_prices_csv(db: Session, content: bytes) -> CsvImportSummary:
    rows, errors = _read_csv(content)
    created_rows = 0
    row_errors: list[CsvImportError] = errors

    for row_number, row in rows:
        missing = _missing_required(row, ["competitor_name", "product_sku", "reference_price"])
        if missing:
            row_errors.append(_error(row_number, f"Missing required column: {missing}"))
            continue

        product = db.query(Product).filter(Product.sku == row["product_sku"].strip()).first()
        if product is None:
            row_errors.append(_error(row_number, "Product not found for product_sku"))
            continue

        reference_price = _parse_float(row_number, "reference_price", row, row_errors)
        if reference_price is None:
            continue
        if reference_price <= 0:
            row_errors.append(_error(row_number, "reference_price must be greater than 0"))
            continue

        competitor_name = row["competitor_name"].strip()
        competitor = db.query(Competitor).filter(Competitor.name == competitor_name).first()
        if competitor is None:
            competitor = Competitor(
                name=competitor_name,
                channel=_optional_text(row.get("channel")) or "unknown",
                notes="Created from manual CSV import.",
            )
            db.add(competitor)
            db.flush()
        elif _optional_text(row.get("channel")):
            competitor.channel = row["channel"].strip()

        observed_at = _parse_datetime(row_number, row.get("observed_at"), row_errors)
        if row.get("observed_at") and observed_at is None:
            continue

        db.add(
            CompetitorPrice(
                competitor_id=competitor.id,
                product_id=product.id,
                reference_price=reference_price,
                source_note=_optional_text(row.get("source_note")),
                observed_at=observed_at or datetime.utcnow(),
            )
        )
        created_rows += 1

    db.commit()
    return _summary("competitor_prices", len(rows), created_rows, 0, row_errors)


def export_products_csv(db: Session) -> str:
    rows = db.query(Product).order_by(Product.id).all()
    return _write_csv(
        ["id", "name", "sku", "category", "description", "active", "created_at", "updated_at"],
        [
            [
                row.id,
                row.name,
                row.sku,
                row.category,
                row.description or "",
                row.active,
                _format_datetime(row.created_at),
                _format_datetime(row.updated_at),
            ]
            for row in rows
        ],
    )


def export_cost_profiles_csv(db: Session) -> str:
    rows = db.query(CostProfile).join(Product).order_by(CostProfile.id).all()
    return _write_csv(
        [
            "id",
            "product_id",
            "product_sku",
            "material_cost",
            "labor_cost",
            "overhead_cost",
            "target_margin_rate",
            "active",
            "created_at",
            "updated_at",
        ],
        [
            [
                row.id,
                row.product_id,
                row.product.sku,
                row.material_cost,
                row.labor_cost,
                row.overhead_cost,
                row.target_margin_rate,
                row.active,
                _format_datetime(row.created_at),
                _format_datetime(row.updated_at),
            ]
            for row in rows
        ],
    )


def export_competitor_prices_csv(db: Session) -> str:
    rows = (
        db.query(CompetitorPrice)
        .join(Competitor)
        .join(Product)
        .order_by(CompetitorPrice.id)
        .all()
    )
    return _write_csv(
        [
            "id",
            "competitor_name",
            "product_sku",
            "reference_price",
            "source_note",
            "observed_at",
            "created_at",
        ],
        [
            [
                row.id,
                row.competitor.name,
                row.product.sku,
                row.reference_price,
                row.source_note or "",
                _format_datetime(row.observed_at),
                _format_datetime(row.created_at),
            ]
            for row in rows
        ],
    )


def _read_csv(content: bytes) -> tuple[list[tuple[int, dict[str, str]]], list[CsvImportError]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        return [], [_error(1, "CSV header row is required")]
    rows = [(index, _normalize_row(row)) for index, row in enumerate(reader, start=2)]
    return rows, []


def _normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {(key or "").strip(): (value or "").strip() for key, value in row.items()}


def _missing_required(row: dict[str, str], required_columns: list[str]) -> str | None:
    for column in required_columns:
        if column not in row or row[column] == "":
            return column
    return None


def _cost_profile_values(
    row_number: int, row: dict[str, str], errors: list[CsvImportError]
) -> dict | None:
    material_cost = _parse_float(row_number, "material_cost", row, errors)
    labor_cost = _parse_float(row_number, "labor_cost", row, errors)
    overhead_cost = _parse_float(row_number, "overhead_cost", row, errors)
    target_margin_rate = _parse_float(row_number, "target_margin_rate", row, errors)
    values = [material_cost, labor_cost, overhead_cost, target_margin_rate]
    if any(value is None for value in values):
        return None
    if any(value < 0 for value in [material_cost, labor_cost, overhead_cost]):
        errors.append(_error(row_number, "cost values must be greater than or equal to 0"))
        return None
    if target_margin_rate < 0 or target_margin_rate >= 1:
        errors.append(_error(row_number, "target_margin_rate must be >= 0 and < 1"))
        return None
    return {
        "material_cost": material_cost,
        "labor_cost": labor_cost,
        "overhead_cost": overhead_cost,
        "target_margin_rate": target_margin_rate,
        "active": _parse_bool(row.get("active"), True),
    }


def _parse_float(
    row_number: int, field_name: str, row: dict[str, str], errors: list[CsvImportError]
) -> float | None:
    try:
        return float(row[field_name])
    except (TypeError, ValueError):
        errors.append(_error(row_number, f"{field_name} must be a number"))
        return None


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "active"}


def _parse_datetime(
    row_number: int, value: str | None, errors: list[CsvImportError]
) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        errors.append(_error(row_number, "observed_at must be ISO datetime format"))
        return None


def _optional_text(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    return value.strip()


def _write_csv(headers: list[str], rows: list[list]) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()


def _summary(
    entity_type: str,
    received_rows: int,
    created_rows: int,
    updated_rows: int,
    errors: list[CsvImportError],
) -> CsvImportSummary:
    return CsvImportSummary(
        entity_type=entity_type,
        received_rows=received_rows,
        created_rows=created_rows,
        updated_rows=updated_rows,
        failed_rows=len(errors),
        errors=errors,
        notes=CSV_NOTES,
    )


def _error(row_number: int, message: str) -> CsvImportError:
    return CsvImportError(row_number=row_number, message=message)


def _format_datetime(value: datetime | None) -> str:
    return value.isoformat() if value else ""
