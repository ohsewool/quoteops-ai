import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _nav_source(source: str) -> str:
    start = source.index("const NAV_SECTIONS = [")
    end = source.index("]\n\nconst OVERVIEW_WORKFLOW_CARDS", start)
    return source[start:end]


def test_authenticated_navigation_is_workflow_oriented():
    source = _read(APP_SOURCE)
    nav = _nav_source(source)

    expected_order = [
        "대시보드",
        "고객 요청",
        "견적",
        "가격 평가",
        "승인함",
        "리포트",
        "운영",
        "데모",
    ]
    positions = [nav.index(f'label: "{label}"') for label in expected_order]

    assert positions == sorted(positions)
    assert 'label: "시뮬레이션"' not in nav


def test_dashboard_shell_copy_matches_cpq_workflow():
    source = _read(APP_SOURCE)

    for text in [
        "오늘 처리할 견적과 승인",
        "지연 없이 처리해야 할 요청과 병목을 먼저 확인하세요.",
        "오늘의 작업",
        "신규 요청",
        "가격 평가 필요",
        "승인 대기",
        "최근 리포트",
        "빠른 실행",
        "고객 요청 → 견적 생성 → 가격 평가 → 승인 → 리포트",
        "최종 가격은 승인 후 확정됩니다",
    ]:
        assert text in source

    assert '{showSection("overview") && currentUser && dashboardSummary && (' not in source
    assert '{showSection("overview") && currentUser && dashboardInsights && (' not in source


def test_customer_request_and_quote_workspaces_have_intake_and_quote_structure():
    source = _read(APP_SOURCE)

    for text in [
        "견적을 만들기 전의 요청을 수집하고 정리합니다.",
        "요청 등록",
        "견적으로 전환",
        "견적 만들기",
        "등록된 고객 요청이 없습니다.",
        "고객 요청을 견적 작업으로 전환하고 제출 가능한 상태까지 정리합니다.",
        "기본 정보 → 항목/수량 → 가격 반영 → 검토 → 승인 요청",
        "라인 아이템",
        "가격 평가로 이동",
    ]:
        assert text in source


def test_pricing_check_workspace_contains_decision_shell_and_advanced_tools():
    source = _read(APP_SOURCE)

    for text in [
        "후보 가격과 규칙 검증 결과를 비교해 승인 필요 여부를 판단합니다.",
        "기준가",
        "원가",
        "적용 후보가",
        "예상 마진",
        "리스크 수준",
        "승인 필요 여부",
        "가격안 비교",
        "원가 결과",
        "트리거된 규칙",
        "승인 트리거",
        "다음 작업",
        "전략 템플릿",
        "가격표 이력과 비교",
        "시뮬레이션",
        "기술 정보",
    ]:
        assert text in source

    assert '{showSection("pricing-tools") && currentUser && (' in source
    assert 'summary>시뮬레이션</summary>' in source


def test_approval_reports_operations_and_demo_shells_are_separated():
    source = _read(APP_SOURCE)

    for text in [
        "승인자가 빠르게 판단할 수 있도록 필요한 근거만 모읍니다.",
        "승인 대기 목록",
        "선택한 견적 상세",
        "왜 승인이 필요한지",
        "변경 전후 비교",
        "현재 처리할 승인 항목이 없습니다.",
        "견적 문서와 운영 요약을 공유 가능한 형식으로 관리합니다.",
        "문서 생성",
        "내보내기",
        "미리보기",
        "내보내기 이력",
        "아직 생성된 문서가 없습니다.",
        "시스템 상태와 데이터 관리, 개발자 기능을 관리합니다.",
        "시스템 상태",
        "데이터 관리",
        "감사 로그",
        "API/개발자",
        "OpenAPI",
        "샘플 데이터를 사용해 실제 업무 흐름을 순서대로 체험합니다.",
        "데모 시작",
        "샘플 데이터 준비",
        "고객 요청 생성",
        "견적 생성",
        "가격 평가",
        "승인 처리",
        "리포트 생성",
        "데모 안내",
    ]:
        assert text in source


def test_role_chip_and_normal_workflow_do_not_render_old_visible_artifacts():
    source = _read(APP_SOURCE)
    nav = _nav_source(source)

    for text in ["관리자 모드", "매니저 모드", "조회자 모드"]:
        assert text in source

    for forbidden in [
        "currentUser.display_name",
        "Demo Viewer",
        "Demo Manager",
        "Demo Admin",
    ]:
        assert forbidden not in source

    assert "auth_login_success" in source
    assert "workflow_job_viewed" not in source
    assert "demo_guide_viewed" not in source
    assert "system_health" not in source
    assert "quote_requests" not in nav


def test_frontend_api_contract_artifact_and_pdf_safety():
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

    generated = subprocess.run(
        ["git", "ls-files", "frontend/dist", "frontend/node_modules"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    pdfs = subprocess.run(
        ["git", "ls-files", "*.pdf"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert generated.stdout.strip() == ""
    assert pdfs.stdout.strip() == ""
