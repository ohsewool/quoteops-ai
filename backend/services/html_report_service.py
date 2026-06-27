from html import escape
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import HtmlReport, PriceApprovalRequest
from backend.schemas import HtmlReportCreate, HtmlReportResponse
from backend.services.approval_service import get_approval_request
from backend.services.dashboard_service import get_dashboard_metrics
from backend.services.pricing_simulation_service import get_pricing_simulation
from backend.services.scenario_comparison_service import get_scenario_comparison


ALLOWED_REPORT_TYPES = {
    "quote_preview",
    "price_validation",
    "approval_request",
    "pricing_simulation",
    "scenario_comparison",
    "dashboard_summary",
}
SOURCE_REQUIRED_TYPES = {
    "quote_preview",
    "price_validation",
    "approval_request",
    "pricing_simulation",
    "scenario_comparison",
}
REPORT_NOTES = [
    "This HTML report was generated from deterministic system data.",
    "No AI-generated price, approval, or validation decision was used.",
    "This report does not approve or activate prices.",
]
DECISION_BOUNDARY = (
    "Decision boundary: this report is read-only and does not approve, reject, "
    "or activate any price."
)


def create_html_report(
    db: Session, payload: HtmlReportCreate, created_by_username: str
) -> HtmlReportResponse:
    _validate_report_request(payload)
    source_type = payload.report_type
    html_content, summary_text = _render_report(db, payload)
    report = HtmlReport(
        report_type=payload.report_type,
        title=payload.title,
        source_type=source_type,
        source_id=str(payload.source_id) if payload.source_id is not None else None,
        html_content=html_content,
        summary_text=summary_text,
        created_by_username=created_by_username,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _to_response(report)


def list_html_reports(db: Session) -> list[HtmlReportResponse]:
    reports = db.query(HtmlReport).order_by(HtmlReport.id.desc()).all()
    return [_to_response(report) for report in reports]


def get_html_report(db: Session, report_id: int) -> HtmlReportResponse:
    return _to_response(_get_report_model(db, report_id))


def get_html_report_content(db: Session, report_id: int) -> str:
    return _get_report_model(db, report_id).html_content


def _validate_report_request(payload: HtmlReportCreate) -> None:
    if payload.report_type not in ALLOWED_REPORT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported report_type")
    if payload.report_type in SOURCE_REQUIRED_TYPES and payload.source_id is None:
        raise HTTPException(status_code=400, detail="source_id is required for this report_type")


def _render_report(db: Session, payload: HtmlReportCreate) -> tuple[str, str]:
    report_type = payload.report_type
    if report_type == "dashboard_summary":
        return _render_dashboard_report(db, payload.title)
    if report_type == "approval_request":
        return _render_approval_report(db, payload.title, _source_id(payload))
    if report_type == "price_validation":
        return _render_validation_report(db, payload.title, _source_id(payload))
    if report_type == "quote_preview":
        return _render_quote_preview_report(db, payload.title, _source_id(payload))
    if report_type == "pricing_simulation":
        return _render_pricing_simulation_report(db, payload.title, _source_id(payload))
    if report_type == "scenario_comparison":
        return _render_scenario_comparison_report(db, payload.title, _source_id(payload))
    raise HTTPException(status_code=400, detail="Unsupported report_type")


def _render_dashboard_report(db: Session, title: str) -> tuple[str, str]:
    dashboard = get_dashboard_metrics(db)
    sections = [
        _kv_table("Summary", dashboard.summary.model_dump()),
        _kv_table("Quote metrics", dashboard.quote_metrics.model_dump()),
        _kv_table("Approval metrics", dashboard.approval_metrics.model_dump()),
        _kv_table("Validation metrics", dashboard.validation_metrics.model_dump()),
        _kv_table("Pricing metrics", dashboard.pricing_metrics.model_dump()),
        _kv_table("Workflow metrics", dashboard.workflow_metrics.model_dump()),
        _kv_table(
            "Audit metrics",
            {
                "total_audit_logs": dashboard.audit_metrics.total_audit_logs,
                "recent_audit_log_count": dashboard.audit_metrics.recent_audit_log_count,
            },
        ),
        _list_section("Dashboard notes", dashboard.dashboard_notes),
    ]
    html = _document(title, sections)
    return html, "Dashboard summary report generated from deterministic KPI metrics."


def _render_approval_report(db: Session, title: str, source_id: int) -> tuple[str, str]:
    approval = get_approval_request(db, source_id)
    sections = [
        _kv_table(
            "Approval request",
            {
                "approval_request_id": approval.id,
                "product": approval.product_name,
                "quantity": approval.quantity,
                "proposed_unit_price": approval.proposed_unit_price,
                "validation_status": approval.validation_status,
                "risk_level": approval.risk_level,
                "approval_status": approval.status,
                "reviewer_name": approval.reviewer_name,
                "review_note": approval.review_note,
                "submitted_note": approval.submitted_note,
                "created_at": approval.created_at,
                "reviewed_at": approval.reviewed_at,
            },
        )
    ]
    html = _document(title, sections)
    return html, "Approval request report generated from deterministic stored data."


def _render_validation_report(db: Session, title: str, source_id: int) -> tuple[str, str]:
    approval = get_approval_request(db, source_id)
    sections = [
        _kv_table(
            "Validation snapshot",
            {
                "product": approval.product_name,
                "quantity": approval.quantity,
                "candidate_unit_price": approval.proposed_unit_price,
                "candidate_total_price": approval.proposed_total_price,
                "unit_cost": approval.unit_cost,
                "estimated_margin_rate": approval.estimated_margin_rate,
                "validation_status": approval.validation_status,
                "risk_level": approval.risk_level,
            },
        )
    ]
    html = _document(title, sections)
    return html, "Price validation report generated from approval request snapshot data."


def _render_quote_preview_report(db: Session, title: str, source_id: int) -> tuple[str, str]:
    approval = get_approval_request(db, source_id)
    sections = [
        _kv_table(
            "Quote preview snapshot",
            {
                "product": approval.product_name,
                "quantity": approval.quantity,
                "unit_cost": approval.unit_cost,
                "total_cost": approval.total_cost,
                "suggested_unit_price": approval.proposed_unit_price,
                "suggested_total_price": approval.proposed_total_price,
                "estimated_gross_profit": approval.estimated_gross_profit,
                "estimated_margin_rate": approval.estimated_margin_rate,
            },
        ),
        _list_section(
            "Calculation notes",
            [
                "Quote preview report uses stored approval request snapshot values.",
                "No AI-generated price was used.",
            ],
        ),
    ]
    html = _document(title, sections)
    return html, "Quote preview report generated from stored pricing snapshot data."


def _render_pricing_simulation_report(db: Session, title: str, source_id: int) -> tuple[str, str]:
    simulation = get_pricing_simulation(db, source_id)
    rows = [
        {
            "quantity": scenario.quantity,
            "margin_rate": scenario.margin_rate,
            "unit_price": scenario.unit_price,
            "total_price": scenario.total_price,
            "gross_profit": scenario.estimated_gross_profit,
            "validation_status": scenario.validation_status,
            "risk_level": scenario.risk_level,
        }
        for scenario in simulation.scenarios
    ]
    sections = [
        _kv_table(
            "Simulation",
            {
                "simulation_name": simulation.name,
                "product": simulation.product_name,
                "scenario_count": simulation.scenario_count,
            },
        ),
        _rows_table("Scenario table", rows),
    ]
    html = _document(title, sections)
    return html, "Pricing simulation report generated from deterministic stored data."


def _render_scenario_comparison_report(db: Session, title: str, source_id: int) -> tuple[str, str]:
    comparison = get_scenario_comparison(db, source_id)
    rows = [
        {
            "label": scenario.label,
            "quantity": scenario.quantity,
            "margin_rate": scenario.margin_rate,
            "unit_price": scenario.unit_price,
            "total_price": scenario.total_price,
            "gross_profit": scenario.estimated_gross_profit,
            "validation_status": scenario.validation_status,
            "risk_level": scenario.risk_level,
        }
        for scenario in comparison.scenarios
    ]
    sections = [
        _kv_table(
            "Comparison summary",
            {
                "comparison_name": comparison.name,
                "product": comparison.product_name,
                "scenario_count": comparison.scenario_count,
                "highest_margin_scenario": comparison.summary.highest_margin_label,
                "highest_profit_scenario": comparison.summary.highest_profit_label,
                "lowest_risk_scenario": comparison.summary.lowest_risk_label,
            },
        ),
        _rows_table("Scenario comparison table", rows),
    ]
    html = _document(title, sections)
    return html, "Scenario comparison report generated from deterministic stored data."


def _document(title: str, sections: list[str]) -> str:
    safe_title = escape(title)
    section_html = "\n".join(sections)
    return (
        "<!doctype html>\n"
        "<html>\n"
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f"  <title>{safe_title}</title>\n"
        "  <style>body{font-family:Arial,sans-serif;line-height:1.5;margin:32px;}"
        "table{border-collapse:collapse;width:100%;margin:12px 0;}"
        "th,td{border:1px solid #d0d7de;padding:8px;text-align:left;}"
        "th{background:#f6f8fa;} .boundary{margin-top:24px;font-weight:bold;}</style>\n"
        "</head>\n"
        "<body>\n"
        f"  <h1>{safe_title}</h1>\n"
        f"{section_html}\n"
        f"  <p class=\"boundary\">{escape(DECISION_BOUNDARY)}</p>\n"
        "</body>\n"
        "</html>\n"
    )


def _kv_table(title: str, values: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><th>{escape(str(key))}</th><td>{escape(_display(value))}</td></tr>"
        for key, value in values.items()
    )
    return f"  <h2>{escape(title)}</h2>\n  <table><tbody>{rows}</tbody></table>"


def _rows_table(title: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return f"  <h2>{escape(title)}</h2>\n  <p>No rows available.</p>"
    headers = list(rows[0].keys())
    head = "".join(f"<th>{escape(str(header))}</th>" for header in headers)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{escape(_display(row.get(header)))}</td>" for header in headers)
        + "</tr>"
        for row in rows
    )
    return f"  <h2>{escape(title)}</h2>\n  <table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _list_section(title: str, items: list[str]) -> str:
    entries = "".join(f"<li>{escape(item)}</li>" for item in items)
    return f"  <h2>{escape(title)}</h2>\n  <ul>{entries}</ul>"


def _display(value: Any) -> str:
    if value is None:
        return "-"
    return str(value)


def _source_id(payload: HtmlReportCreate) -> int:
    if payload.source_id is None:
        raise HTTPException(status_code=400, detail="source_id is required for this report_type")
    return payload.source_id


def _get_report_model(db: Session, report_id: int) -> HtmlReport:
    report = db.get(HtmlReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="HTML report not found")
    return report


def _to_response(report: HtmlReport) -> HtmlReportResponse:
    return HtmlReportResponse(
        id=report.id,
        report_type=report.report_type,
        title=report.title,
        source_type=report.source_type,
        source_id=report.source_id,
        summary_text=report.summary_text,
        created_by_username=report.created_by_username,
        created_at=report.created_at,
        updated_at=report.updated_at,
        report_notes=REPORT_NOTES,
    )
