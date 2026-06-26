from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from typing import Any

from backend.services.dashboard_insights import get_dashboard_insights
from backend.services.dashboard_kpis import get_dashboard_kpis
from backend.services.scenario_comparison import compare_pricing_scenarios


class ReportError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


REPORT_NOTICE = (
    "이 보고서의 가격, 마진, 검증 결과, 비교 수치는 저장된 데이터와 결정론적 "
    "백엔드 계산에서 생성되었습니다. AI는 가격 숫자나 승인 여부를 결정하지 않습니다."
)


def _row_to_dict(row: Any | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _loads(value: str | None, default: Any) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return escape(str(value))


def _money(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):,.0f} KRW"
    except (TypeError, ValueError):
        return _fmt(value)


def _percent(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return _fmt(value)


def _json_text(value: Any) -> str:
    return escape(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _metric(label: str, value: Any) -> str:
    return f"""
      <div class="metric">
        <div class="metric-label">{escape(label)}</div>
        <div class="metric-value">{_fmt(value)}</div>
      </div>
    """


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return '<div class="empty">표시할 데이터가 없습니다.</div>'
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"""
      <div class="table-wrap">
        <table>
          <thead><tr>{head}</tr></thead>
          <tbody>{body}</tbody>
        </table>
      </div>
    """


def _document(title: str, subtitle: str, sections: list[str]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    body = "\n".join(sections)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <style>
    :root {{
      color: #111827;
      background: #f7f7f8;
      font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Inter", "Segoe UI", sans-serif;
    }}
    body {{ margin: 0; padding: 32px; }}
    main {{ max-width: 1080px; margin: 0 auto; background: #fff; border: 1px solid #e5e7eb; border-radius: 24px; padding: 36px; }}
    header {{ border-bottom: 1px solid #e5e7eb; padding-bottom: 22px; margin-bottom: 28px; }}
    h1 {{ margin: 0; font-size: 32px; letter-spacing: -0.01em; }}
    h2 {{ margin: 0 0 14px; font-size: 20px; }}
    section {{ margin-top: 28px; }}
    p {{ line-height: 1.65; color: #475569; }}
    .eyebrow {{ color: #64748b; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; }}
    .subtitle {{ color: #475569; margin-top: 10px; }}
    .notice {{ border: 1px solid #bfdbfe; background: #eff6ff; color: #1e3a8a; border-radius: 18px; padding: 16px; }}
    .grid {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
    .metric {{ border: 1px solid #e5e7eb; background: #f8fafc; border-radius: 16px; padding: 14px; }}
    .metric-label {{ color: #64748b; font-size: 12px; }}
    .metric-value {{ margin-top: 6px; font-size: 20px; font-weight: 700; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid #e5e7eb; border-radius: 16px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ text-align: left; background: #f8fafc; color: #64748b; padding: 11px; border-bottom: 1px solid #e5e7eb; }}
    td {{ vertical-align: top; padding: 11px; border-bottom: 1px solid #f1f5f9; }}
    pre {{ white-space: pre-wrap; background: #0f172a; color: #e2e8f0; border-radius: 16px; padding: 16px; overflow-x: auto; }}
    .empty {{ border: 1px dashed #cbd5e1; color: #64748b; border-radius: 16px; padding: 16px; }}
    footer {{ margin-top: 36px; border-top: 1px solid #e5e7eb; padding-top: 18px; color: #64748b; font-size: 12px; line-height: 1.6; }}
    @media print {{
      body {{ background: #fff; padding: 0; }}
      main {{ border: 0; border-radius: 0; padding: 20px; }}
      section {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div class="eyebrow">QuoteOps AI Report</div>
      <h1>{escape(title)}</h1>
      <p class="subtitle">{escape(subtitle)}</p>
      <p class="subtitle">생성 시각: {escape(generated_at)}</p>
    </header>
    <div class="notice">{escape(REPORT_NOTICE)}</div>
    {body}
    <footer>
      {escape(REPORT_NOTICE)} 보고서는 브라우저 인쇄 기능으로 PDF 저장할 수 있습니다.
      환경 변수, 토큰, 데이터베이스 URL, OpenAI API 키 같은 비밀 값은 포함하지 않습니다.
    </footer>
  </main>
</body>
</html>"""


def _candidate_table(connection: Any, candidate_id: int) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT ct.id, ct.product_id, ct.name, ct.strategy_name, ct.status,
               ct.created_at, ct.updated_at, p.name AS product_name
        FROM candidate_tables ct
        JOIN products p ON p.id = ct.product_id
        WHERE ct.id = ?
        """,
        (candidate_id,),
    ).fetchone()
    candidate = _row_to_dict(row)
    if candidate is None:
        raise ReportError(404, "Candidate table not found.")
    return candidate


def _candidate_items(connection: Any, candidate_id: int) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT id, quantity, option_summary, candidate_price, unit_price,
                   cost_floor_price, estimated_margin_rate, market_lowest_price,
                   market_average_price, market_median_price, market_highest_price,
                   market_reference_count, decision_reason_codes, warnings,
                   created_at, updated_at
            FROM candidate_table_items
            WHERE candidate_table_id = ?
            ORDER BY quantity, id
            """,
            (candidate_id,),
        ).fetchall()
    ]


def _latest_validation(connection: Any, candidate_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT id, overall_status, risk_level, summary_json, result_json, created_at, updated_at
        FROM validation_results
        WHERE candidate_table_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (candidate_id,),
    ).fetchone()
    validation = _row_to_dict(row)
    if validation:
        validation["summary"] = _loads(validation.pop("summary_json"), {})
        validation["results"] = _loads(validation.pop("result_json"), [])
    return validation


def _approvals(connection: Any, candidate_id: int) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT id, action, status, reviewer_name, reviewer_note,
                   created_price_table_id, created_at, updated_at
            FROM approvals
            WHERE candidate_table_id = ?
            ORDER BY id DESC
            """,
            (candidate_id,),
        ).fetchall()
    ]


def _approval_audit_events(connection: Any, candidate_id: int) -> list[dict[str, Any]]:
    token = f'"candidate_table_id": {candidate_id}'
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT id, action, entity_type, entity_id, entity_label,
                   actor_name, actor_role, metadata_json, created_at
            FROM audit_logs
            WHERE (entity_type = 'candidate_table' AND entity_id = ?)
               OR metadata_json LIKE ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (candidate_id, f"%{token}%"),
        ).fetchall()
    ]


def generate_candidate_report(connection: Any, candidate_id: int) -> str:
    candidate = _candidate_table(connection, candidate_id)
    items = _candidate_items(connection, candidate_id)
    validation = _latest_validation(connection, candidate_id)
    approvals = _approvals(connection, candidate_id)
    sections = [
        f"""
        <section>
          <h2>후보 가격표 요약</h2>
          <div class="grid">
            {_metric("후보 ID", candidate["id"])}
            {_metric("상품", candidate["product_name"])}
            {_metric("상태", candidate["status"])}
            {_metric("전략", candidate["strategy_name"])}
            {_metric("행 수", len(items))}
            {_metric("최신 검증", validation["overall_status"] if validation else "검증 결과 없음")}
          </div>
        </section>
        """,
        f"""
        <section>
          <h2>후보 가격 행</h2>
          {_table(
              ["수량", "옵션", "후보 가격", "단가", "원가 하한", "예상 마진", "시장 평균", "사유 코드", "경고"],
              [
                  [
                      _fmt(item["quantity"]),
                      _fmt(item["option_summary"]),
                      _money(item["candidate_price"]),
                      _money(item["unit_price"]),
                      _money(item["cost_floor_price"]),
                      _percent(item["estimated_margin_rate"]),
                      _money(item["market_average_price"]),
                      _fmt(", ".join(_loads(item["decision_reason_codes"], []))),
                      _fmt(", ".join(_loads(item["warnings"], []))),
                  ]
                  for item in items
              ],
          )}
        </section>
        """,
        f"""
        <section>
          <h2>승인 상태</h2>
          {_table(
              ["작업", "상태", "관리자", "생성 가격표", "시각"],
              [
                  [
                      _fmt(row["action"]),
                      _fmt(row["status"]),
                      _fmt(row["reviewer_name"]),
                      _fmt(row["created_price_table_id"]),
                      _fmt(row["created_at"]),
                  ]
                  for row in approvals
              ],
          )}
        </section>
        """,
    ]
    return _document(
        "후보 가격표 보고서",
        f'{candidate["name"]} · 후보 가격표는 관리자 승인 전까지 실제 가격표로 적용되지 않습니다.',
        sections,
    )


def generate_validation_report(connection: Any, candidate_id: int) -> str:
    candidate = _candidate_table(connection, candidate_id)
    validation = _latest_validation(connection, candidate_id)
    if validation is None:
        sections = [
            """
            <section>
              <h2>검증 결과 없음</h2>
              <div class="empty">이 후보 가격표에는 저장된 검증 결과가 없습니다. 승인 전에 검증을 실행해야 합니다.</div>
            </section>
            """
        ]
    else:
        summary = validation["summary"] or {}
        results = validation["results"] or []
        sections = [
            f"""
            <section>
              <h2>검증 요약</h2>
              <div class="grid">
                {_metric("후보 ID", candidate_id)}
                {_metric("전체 상태", validation["overall_status"])}
                {_metric("위험 수준", validation["risk_level"])}
                {_metric("검증 ID", validation["id"])}
                {_metric("생성 시각", validation["created_at"])}
                {_metric("결과 행", len(results))}
              </div>
            </section>
            """,
            f"""
            <section>
              <h2>요약 JSON</h2>
              <pre>{_json_text(summary)}</pre>
            </section>
            """,
            f"""
            <section>
              <h2>항목별 검증 결과</h2>
              {_table(
                  ["수량", "상태", "위험", "검사 코드", "메시지"],
                  [
                      [
                          _fmt(item.get("quantity")),
                          _fmt(item.get("status")),
                          _fmt(item.get("risk_level")),
                          _fmt(", ".join(check.get("code", "") for check in item.get("checks", []))),
                          _fmt(" / ".join(check.get("message", "") for check in item.get("checks", []))),
                      ]
                      for item in results
                  ],
              )}
            </section>
            """,
        ]
    return _document(
        "검증 보고서",
        f'{candidate["name"]} · 검증 결과는 관리자 승인 전 참고용이며 결정론적 규칙으로만 생성됩니다.',
        sections,
    )


def generate_scenario_comparison_report(
    connection: Any,
    *,
    base_type: str,
    base_id: int,
    compare_type: str,
    compare_id: int,
) -> str:
    result = compare_pricing_scenarios(
        connection,
        base_type=base_type,
        base_id=base_id,
        compare_type=compare_type,
        compare_id=compare_id,
    )
    summary = result["summary"]
    sections = [
        f"""
        <section>
          <h2>시나리오 비교 요약</h2>
          <div class="grid">
            {_metric("비교 행", summary["total_compared_items"])}
            {_metric("일치 행", summary["matching_item_count"])}
            {_metric("누락 행", summary["missing_item_count"])}
            {_metric("평균 가격 차이", _money(summary["average_price_difference"]))}
            {_metric("평균 가격 차이율", _percent(summary["average_price_difference_rate"]))}
            {_metric("경고 수", summary["warning_count"])}
          </div>
        </section>
        """,
        f"""
        <section>
          <h2>비교 대상</h2>
          <div class="grid">
            {_metric("기준", f'{result["base"]["name"]} ({result["base"]["scenario_type"]} #{result["base"]["scenario_id"]})')}
            {_metric("비교", f'{result["compare"]["name"]} ({result["compare"]["scenario_type"]} #{result["compare"]["scenario_id"]})')}
            {_metric("기준 검증", (result["base"].get("validation") or {}).get("overall_status"))}
            {_metric("비교 검증", (result["compare"].get("validation") or {}).get("overall_status"))}
          </div>
        </section>
        """,
        f"""
        <section>
          <h2>항목별 차이</h2>
          {_table(
              ["수량", "옵션", "기준 가격", "비교 가격", "가격 차이", "가격 차이율", "마진 차이", "상태", "경고"],
              [
                  [
                      _fmt(item["quantity"]),
                      _fmt(item["option_summary"]),
                      _money(item["base_price"]),
                      _money(item["compare_price"]),
                      _money(item["price_difference"]),
                      _percent(item["price_difference_rate"]),
                      _percent(item["margin_difference"]),
                      _fmt(item["match_status"]),
                      _fmt(", ".join(item.get("warnings") or [])),
                  ]
                  for item in result["item_differences"]
              ],
          )}
        </section>
        """,
        f"""
        <section>
          <h2>주의 사항</h2>
          <pre>{_json_text({"warnings": result.get("warnings", []), "notes": result.get("notes", [])})}</pre>
        </section>
        """,
    ]
    return _document(
        "가격 시나리오 비교 보고서",
        "이 보고서는 저장된 가격표와 후보 가격표의 차이를 읽기 전용으로 비교합니다.",
        sections,
    )


def generate_approval_report(connection: Any, candidate_id: int) -> str:
    candidate = _candidate_table(connection, candidate_id)
    approvals = _approvals(connection, candidate_id)
    events = _approval_audit_events(connection, candidate_id)
    sections = [
        f"""
        <section>
          <h2>승인/반려 상태</h2>
          <div class="grid">
            {_metric("후보 ID", candidate["id"])}
            {_metric("상품", candidate["product_name"])}
            {_metric("후보 상태", candidate["status"])}
            {_metric("전략", candidate["strategy_name"])}
            {_metric("승인/반려 기록", len(approvals))}
            {_metric("감사 이벤트", len(events))}
          </div>
        </section>
        """,
        f"""
        <section>
          <h2>승인/반려 기록</h2>
          {_table(
              ["ID", "작업", "상태", "관리자", "메모", "생성 가격표", "시각"],
              [
                  [
                      _fmt(row["id"]),
                      _fmt(row["action"]),
                      _fmt(row["status"]),
                      _fmt(row["reviewer_name"]),
                      _fmt(row["reviewer_note"]),
                      _fmt(row["created_price_table_id"]),
                      _fmt(row["created_at"]),
                  ]
                  for row in approvals
              ],
          )}
        </section>
        """,
        f"""
        <section>
          <h2>관련 감사 이벤트</h2>
          {_table(
              ["ID", "작업", "대상", "관리자", "권한", "시각"],
              [
                  [
                      _fmt(row["id"]),
                      _fmt(row["action"]),
                      _fmt(f'{row["entity_type"]} #{row["entity_id"]}' if row["entity_id"] else row["entity_type"]),
                      _fmt(row["actor_name"]),
                      _fmt(row["actor_role"]),
                      _fmt(row["created_at"]),
                  ]
                  for row in events
              ],
          )}
        </section>
        """,
    ]
    return _document(
        "승인 증빙 보고서",
        "AI는 승인 결정을 내리지 않으며, 후보 가격표 활성화는 명시적인 관리자 승인으로만 수행됩니다.",
        sections,
    )


def generate_operations_snapshot_report(connection: Any) -> str:
    kpis = get_dashboard_kpis(connection)
    insights = get_dashboard_insights(connection)
    latest_events = insights.get("audit_activity", {}).get("latest_events", [])
    sections = [
        f"""
        <section>
          <h2>운영 KPI</h2>
          <div class="grid">
            {_metric("전체 상품", kpis["pricing"]["total_products"])}
            {_metric("활성 상품", kpis["pricing"]["active_products"])}
            {_metric("경쟁사 가격", kpis["pricing"]["total_competitor_prices"])}
            {_metric("원가 프로필", kpis["pricing"]["total_cost_profiles"])}
            {_metric("활성 가격표", kpis["pricing"]["active_price_tables"])}
            {_metric("후보 가격표", kpis["candidates"]["total_candidate_tables"])}
            {_metric("검증 경고", kpis["validation"]["warning_count"])}
            {_metric("검증 실패", kpis["validation"]["fail_count"])}
            {_metric("감사 로그", kpis["operations"]["total_audit_logs"])}
            {_metric("작업 실패", kpis["operations"]["failed_workflow_jobs"])}
          </div>
        </section>
        """,
        f"""
        <section>
          <h2>운영 주의 항목</h2>
          {_table(
              ["심각도", "제목", "영역", "건수", "메시지"],
              [
                  [
                      _fmt(item.get("severity")),
                      _fmt(item.get("title")),
                      _fmt(item.get("related_area")),
                      _fmt(item.get("count")),
                      _fmt(item.get("message")),
                  ]
                  for item in insights.get("attention_items", [])
              ],
          )}
        </section>
        """,
        f"""
        <section>
          <h2>최근 감사 이벤트</h2>
          {_table(
              ["ID", "작업", "대상", "관리자", "권한", "시각"],
              [
                  [
                      _fmt(row.get("id")),
                      _fmt(row.get("action")),
                      _fmt(row.get("entity_type")),
                      _fmt(row.get("actor_name")),
                      _fmt(row.get("actor_role")),
                      _fmt(row.get("created_at")),
                  ]
                  for row in latest_events
              ],
          )}
        </section>
        """,
    ]
    return _document(
        "운영 스냅샷 보고서",
        "저장된 운영 데이터에서 계산한 KPI와 최근 활동 요약입니다.",
        sections,
    )
