from __future__ import annotations

import json
import sqlite3
from typing import Any

from backend.config import get_settings
from backend.db import utc_now
from backend.services.agent_logger import log_agent_step


class ExplanationError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class ExplanationNotFoundError(ExplanationError):
    status_code = 404


def _fetch_candidate_facts(
    connection: sqlite3.Connection,
    candidate_table_id: int,
) -> dict[str, Any]:
    table = connection.execute(
        """
        SELECT
            ct.id, ct.pricing_session_id, ct.product_id, ct.name,
            ct.strategy_name, ct.status, p.name AS product_name
        FROM candidate_tables ct
        JOIN products p ON p.id = ct.product_id
        WHERE ct.id = ?
        """,
        (candidate_table_id,),
    ).fetchone()
    if table is None:
        raise ExplanationNotFoundError("Candidate table not found.")

    items = connection.execute(
        """
        SELECT
            quantity, option_summary, candidate_price, unit_price,
            cost_floor_price, estimated_margin_rate, market_lowest_price,
            market_average_price, market_median_price, market_highest_price,
            market_reference_count, decision_reason_codes, warnings
        FROM candidate_table_items
        WHERE candidate_table_id = ?
        ORDER BY quantity ASC, id ASC
        """,
        (candidate_table_id,),
    ).fetchall()
    if not items:
        raise ExplanationNotFoundError("Candidate table has no items to explain.")

    validation = connection.execute(
        """
        SELECT id, overall_status, risk_level, summary_json, result_json, created_at
        FROM validation_results
        WHERE candidate_table_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (candidate_table_id,),
    ).fetchone()

    return {
        "candidate_table_id": table["id"],
        "pricing_session_id": table["pricing_session_id"],
        "candidate_table_name": table["name"],
        "product_name": table["product_name"],
        "strategy_name": table["strategy_name"],
        "candidate_status": table["status"],
        "items": [
            {
                "quantity": item["quantity"],
                "option_summary": item["option_summary"],
                "candidate_price": item["candidate_price"],
                "unit_price": item["unit_price"],
                "cost_floor_price": item["cost_floor_price"],
                "estimated_margin_rate": item["estimated_margin_rate"],
                "market_lowest_price": item["market_lowest_price"],
                "market_average_price": item["market_average_price"],
                "market_median_price": item["market_median_price"],
                "market_highest_price": item["market_highest_price"],
                "market_reference_count": item["market_reference_count"],
                "decision_reason_codes": json.loads(item["decision_reason_codes"] or "[]"),
                "warnings": json.loads(item["warnings"] or "[]"),
            }
            for item in items
        ],
        "latest_validation": (
            {
                "validation_result_id": validation["id"],
                "overall_status": validation["overall_status"],
                "risk_level": validation["risk_level"],
                "summary": json.loads(validation["summary_json"]),
                "results": json.loads(validation["result_json"]),
                "created_at": validation["created_at"],
            }
            if validation is not None
            else None
        ),
    }


def _fallback_explanation(facts: dict[str, Any]) -> str:
    validation = facts.get("latest_validation")
    validation_sentence = (
        f"최근 검증 결과는 {validation['overall_status']} 상태이며 위험 수준은 {validation['risk_level']}입니다."
        if validation
        else "아직 저장된 검증 결과가 없으므로, 승인 전 검증을 먼저 실행해야 합니다."
    )
    return (
        "AI API 키가 설정되지 않아 기본 설명을 표시합니다. "
        f"{facts['product_name']} 후보 가격표는 {facts['strategy_name']} 전략으로 생성되었습니다. "
        "표시된 가격, 원가 하한, 시장 참고값, 마진율은 모두 백엔드 결정 로직이 계산한 값입니다. "
        f"{validation_sentence} "
        "이 설명은 숫자를 새로 만들지 않으며, 후보 가격표는 아직 승인되거나 활성화되지 않았습니다. "
        "관리자는 원가 하한, 시장 평균과의 차이, 검증 경고를 확인한 뒤 이후 승인 단계에서 판단해야 합니다."
    )


def _openai_explanation(facts: dict[str, Any], api_key: str, model: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    system_prompt = (
        "You explain deterministic pricing operation results in Korean. "
        "Do not generate, infer, or modify numeric prices, margins, market data, "
        "validation results, risk levels, or approval decisions. "
        "Only refer to numbers and facts present in the provided JSON. "
        "Do not say the candidate is approved. Say human approval is still required."
    )
    user_prompt = (
        "다음 JSON에 포함된 결정론적 계산 결과만 사용해 관리자용 설명을 한국어로 작성하세요. "
        "새로운 숫자나 시장 정보를 만들지 마세요.\n\n"
        + json.dumps(facts, ensure_ascii=False)
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


def explain_candidate_table(
    connection: sqlite3.Connection,
    *,
    candidate_table_id: int,
) -> dict[str, Any]:
    facts = _fetch_candidate_facts(connection, candidate_table_id)
    warnings: list[str] = []
    source = "fallback"
    settings = get_settings()
    api_key = settings.openai_api_key
    model = settings.openai_model

    if not api_key or api_key == "***":
        warnings.append("OPENAI_API_KEY is not configured")
        explanation = _fallback_explanation(facts)
    else:
        try:
            explanation = _openai_explanation(facts, api_key, model)
            source = "openai"
        except Exception as exc:  # pragma: no cover - depends on external API/network.
            warnings.append(f"OpenAI explanation failed: {exc}")
            explanation = _fallback_explanation(facts)

    created_at = utc_now()
    log_agent_step(
        connection,
        pricing_session_id=facts["pricing_session_id"],
        candidate_table_id=candidate_table_id,
        validation_result_id=(
            facts["latest_validation"]["validation_result_id"]
            if facts.get("latest_validation")
            else None
        ),
        step_type="ai_explanation_generated",
        title="AI explanation generated",
        message=(
            "Generated an OpenAI explanation from deterministic facts."
            if source == "openai"
            else "Generated a fallback explanation because OpenAI is not configured."
        ),
        status="completed" if source == "openai" else "warning",
        metadata={"source": source, "warnings": warnings},
    )

    return {
        "candidate_table_id": candidate_table_id,
        "explanation": explanation,
        "source": source,
        "warnings": warnings,
        "created_at": created_at,
    }
