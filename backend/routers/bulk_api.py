from fastapi import APIRouter, Body, Depends, HTTPException, Response

from backend.db import get_connection
from backend.routers.auth_api import require_manager_or_owner_admin
from backend.schemas import CsvImportResponse
from backend.services.csv_transfer import (
    export_candidate_table_items,
    export_competitor_prices,
    export_cost_profiles,
    export_price_table_items,
    import_competitor_prices,
    import_cost_profiles,
)
from backend.services.audit_logger import log_audit_event

router = APIRouter(prefix="/api", tags=["csv-import-export"])


def _csv_response(csv_text: str, filename: str) -> Response:
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import/competitor-prices", response_model=CsvImportResponse)
def import_competitor_price_csv(
    csv_text: str = Body(..., media_type="text/csv"),
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    with get_connection() as connection:
        log_audit_event(
            connection,
            action="csv_import_started",
            entity_type="csv_import",
            entity_label="competitor_prices",
            metadata={"import_type": "competitor_prices"},
        )
        result = import_competitor_prices(connection, csv_text)
        log_audit_event(
            connection,
            action="csv_import_completed" if result["status"] == "imported" else "csv_import_failed",
            entity_type="csv_import",
            entity_label="competitor_prices",
            after=result,
            metadata={"import_type": "competitor_prices"},
        )
        return result


@router.get("/export/competitor-prices")
def export_competitor_price_csv(admin: dict = Depends(require_manager_or_owner_admin)) -> Response:
    with get_connection() as connection:
        csv_text = export_competitor_prices(connection)
        log_audit_event(
            connection,
            action="csv_export_completed",
            entity_type="csv_export",
            entity_label="competitor_prices",
            metadata={"export_type": "competitor_prices"},
        )
        return _csv_response(csv_text, "competitor-prices.csv")


@router.post("/import/cost-profiles", response_model=CsvImportResponse)
def import_cost_profile_csv(
    csv_text: str = Body(..., media_type="text/csv"),
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    with get_connection() as connection:
        log_audit_event(
            connection,
            action="csv_import_started",
            entity_type="csv_import",
            entity_label="cost_profiles",
            metadata={"import_type": "cost_profiles"},
        )
        result = import_cost_profiles(connection, csv_text)
        log_audit_event(
            connection,
            action="csv_import_completed" if result["status"] == "imported" else "csv_import_failed",
            entity_type="csv_import",
            entity_label="cost_profiles",
            after=result,
            metadata={"import_type": "cost_profiles"},
        )
        return result


@router.get("/export/cost-profiles")
def export_cost_profile_csv(admin: dict = Depends(require_manager_or_owner_admin)) -> Response:
    with get_connection() as connection:
        csv_text = export_cost_profiles(connection)
        log_audit_event(
            connection,
            action="csv_export_completed",
            entity_type="csv_export",
            entity_label="cost_profiles",
            metadata={"export_type": "cost_profiles"},
        )
        return _csv_response(csv_text, "cost-profiles.csv")


@router.get("/export/price-tables/{price_table_id}/items")
def export_price_table_item_csv(
    price_table_id: int,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> Response:
    with get_connection() as connection:
        csv_text = export_price_table_items(connection, price_table_id)
        if csv_text is not None:
            log_audit_event(
                connection,
                action="csv_export_completed",
                entity_type="csv_export",
                entity_id=price_table_id,
                entity_label=f"price_table_{price_table_id}_items",
                metadata={"export_type": "price_table_items"},
            )
    if csv_text is None:
        raise HTTPException(status_code=404, detail="Price table not found")
    return _csv_response(csv_text, f"price-table-{price_table_id}-items.csv")


@router.get("/export/candidate-tables/{candidate_table_id}/items")
def export_candidate_table_item_csv(
    candidate_table_id: int,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> Response:
    with get_connection() as connection:
        csv_text = export_candidate_table_items(connection, candidate_table_id)
        if csv_text is not None:
            log_audit_event(
                connection,
                action="csv_export_completed",
                entity_type="csv_export",
                entity_id=candidate_table_id,
                entity_label=f"candidate_table_{candidate_table_id}_items",
                metadata={"export_type": "candidate_table_items"},
            )
    if csv_text is None:
        raise HTTPException(status_code=404, detail="Candidate table not found")
    return _csv_response(csv_text, f"candidate-table-{candidate_table_id}-items.csv")
