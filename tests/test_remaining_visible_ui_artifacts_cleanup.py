import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"
STYLES_SOURCE = ROOT / "frontend" / "src" / "styles.css"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_pricing_demo_and_explanation_korean_labels_are_present():
    source = _read(APP_SOURCE)

    for text in [
        "데모 데이터 상태 확인",
        "샘플 데이터 준비",
        "견적 미리보기 생성",
        "가격안 생성",
        "제안 가격 평가",
        "승인 요청 제출",
        "시나리오 비교",
        "리포트 생성",
        "검토가 필요합니다.",
        "최종 가격은 승인 후 확정됩니다.",
        "AI가 가격을 생성하지 않았습니다.",
        "AI가 승인 결정을 하지 않았습니다.",
        "가격표가 자동 적용되지 않았습니다.",
        "데모 도구는 포트폴리오 시연용입니다.",
        "낮은 마진율",
        "기준 마진율",
        "프리미엄 마진율",
        "원가와 마진 기준으로 계산한 가격안입니다.",
        "제안 단가가 계산된 원가보다 높습니다.",
        "예상 마진이 최소 기준보다 낮습니다.",
        "경쟁사 평균보다 20% 이상 낮습니다.",
        "변경 없음",
        "변경됨",
        "기술 정보",
    ]:
        assert text in source


def test_home_screen_no_longer_renders_internal_dashboard_panels_on_overview():
    source = _read(APP_SOURCE)

    assert '{showSection("admin-system") && currentUser && dashboardSummary && (' in source
    assert '{showSection("admin-system") && currentUser && dashboardInsights && (' in source
    assert '{showSection("overview") && currentUser && dashboardSummary && (' not in source
    assert '{showSection("overview") && currentUser && dashboardInsights && (' not in source
    assert "최근 작업: {displayAction(latestActions[0].action)}" not in source
    assert "오늘의 작업" in source
    assert "다음 단계: 가격 평가" in source


def test_visible_render_paths_do_not_use_raw_english_or_internal_values():
    source = _read(APP_SOURCE)

    for forbidden in [
        "Margin: {candidate.margin_rate}",
        "Unit: {formatMoney(candidate.unit_price)}",
        "Total: {formatMoney(candidate.total_price)}",
        "margin: {results.validation.estimated_margin_rate}",
        "scenarios: {activeSimulation.scenario_count}",
        "unit cost: {formatMoney(activeSimulation.unit_cost)}",
        "<td>{step.title}</td>",
        "{results.explanation.explanation_summary}",
        "<Badge>출처: {results.explanation.explanation_source}</Badge>",
        "<td>{change.change_type}</td>",
    ]:
        assert forbidden not in source

    assert "<td>{displayNote(step.title)}</td>" in source
    assert "{displayNote(results.explanation.explanation_summary)}" in source
    assert "displaySource(results.explanation.explanation_source)" in source
    assert "<td>{displayStatus(change.change_type)}</td>" in source


def test_demo_flow_layout_prevents_vertical_korean_step_cards():
    styles = _read(STYLES_SOURCE)

    assert "grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));" in styles
    assert "grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));" in styles
    assert "word-break: keep-all;" in styles
    assert "overflow-wrap: normal;" in styles
    assert "grid-template-columns: repeat(5, minmax(0, 1fr));" not in styles


def test_frontend_api_contract_and_secret_safety_are_unchanged():
    api_source = _read(API_CLIENT_SOURCE)
    frontend_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "frontend" / "src").rglob("*")
        if path.is_file()
    )

    assert "import.meta.env.VITE_API_BASE_URL" in api_source
    assert "http://127.0.0.1:8000" in api_source
    assert "DATABASE_URL" not in frontend_sources
    assert "QUOTEOPS_AUTH_SECRET" not in frontend_sources


def test_generated_frontend_artifacts_are_not_tracked():
    result = subprocess.run(
        ["git", "ls-files", "frontend/dist", "frontend/node_modules"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == ""
