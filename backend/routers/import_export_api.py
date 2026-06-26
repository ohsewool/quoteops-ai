from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.auth import require_role
from backend.db import get_db
from backend.models import User
from backend.schemas import CsvImportSummary
from backend.services.audit_service import create_audit_log
from backend.services.csv_service import (
    export_competitor_prices_csv,
    export_cost_profiles_csv,
    export_products_csv,
    import_competitor_prices_csv,
    import_cost_profiles_csv,
    import_products_csv,
)


router = APIRouter(tags=["csv import export"])


@router.post("/api/import/products", response_model=CsvImportSummary)
async def import_products(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> CsvImportSummary:
    summary = import_products_csv(db, await file.read())
    _audit_import(db, "csv_products_imported", summary, current_user)
    return summary


@router.post("/api/import/cost-profiles", response_model=CsvImportSummary)
async def import_cost_profiles(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> CsvImportSummary:
    summary = import_cost_profiles_csv(db, await file.read())
    _audit_import(db, "csv_cost_profiles_imported", summary, current_user)
    return summary


@router.post("/api/import/competitor-prices", response_model=CsvImportSummary)
async def import_competitor_prices(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> CsvImportSummary:
    summary = import_competitor_prices_csv(db, await file.read())
    _audit_import(db, "csv_competitor_prices_imported", summary, current_user)
    return summary


@router.get("/api/export/products.csv")
def export_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> Response:
    csv_text = export_products_csv(db)
    _audit_export(db, "csv_products_exported", "products", current_user)
    return _csv_response(csv_text, "products.csv")


@router.get("/api/export/cost-profiles.csv")
def export_cost_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> Response:
    csv_text = export_cost_profiles_csv(db)
    _audit_export(db, "csv_cost_profiles_exported", "cost_profiles", current_user)
    return _csv_response(csv_text, "cost-profiles.csv")


@router.get("/api/export/competitor-prices.csv")
def export_competitor_prices(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> Response:
    csv_text = export_competitor_prices_csv(db)
    _audit_export(db, "csv_competitor_prices_exported", "competitor_prices", current_user)
    return _csv_response(csv_text, "competitor-prices.csv")


def _audit_import(
    db: Session, action: str, summary: CsvImportSummary, current_user: User
) -> None:
    create_audit_log(
        db,
        action=action,
        entity_type=summary.entity_type,
        summary=f"CSV import completed for {summary.entity_type}.",
        metadata={
            "entity_type": summary.entity_type,
            "received_rows": summary.received_rows,
            "created_rows": summary.created_rows,
            "updated_rows": summary.updated_rows,
            "failed_rows": summary.failed_rows,
        },
        actor=current_user,
    )


def _audit_export(db: Session, action: str, entity_type: str, current_user: User) -> None:
    create_audit_log(
        db,
        action=action,
        entity_type=entity_type,
        summary=f"CSV export generated for {entity_type}.",
        metadata={"entity_type": entity_type},
        actor=current_user,
    )


def _csv_response(csv_text: str, filename: str) -> Response:
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
