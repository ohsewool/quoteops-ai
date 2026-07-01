from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "uiux-redesign-plan.md"


def test_uiux_redesign_plan_exists():
    assert PLAN.exists()
    assert PLAN.stat().st_size > 3000


def test_uiux_redesign_plan_contains_required_sections_and_keywords():
    text = PLAN.read_text(encoding="utf-8")

    required = [
        "현재 UI 문제 진단",
        "정보구조",
        "반응형",
        "한국어 UI 카피",
        "점진적 공개",
        "홈",
        "견적",
        "가격",
        "승인",
        "분석",
        "운영",
        "데모",
        "PR-37",
        "PR-38",
        "PR-39",
        "PR-40",
        "PR-41",
        "PR-42",
    ]

    for keyword in required:
        assert keyword in text


def test_uiux_redesign_plan_includes_responsive_breakpoints():
    text = PLAN.read_text(encoding="utf-8")

    for keyword in [
        "1200px 이상",
        "1024px-1199px",
        "768px-1023px",
        "768px 미만",
        "navigation behavior",
        "card grid behavior",
        "form layout",
        "result panel layout",
        "table behavior",
        "button behavior",
        "status card behavior",
        "login panel behavior",
    ]:
        assert keyword in text


def test_uiux_redesign_plan_does_not_contain_obvious_secrets():
    text = PLAN.read_text(encoding="utf-8")

    forbidden = [
        "DATABASE_URL=",
        "QUOTEOPS_" + "AUTH_SECRET=",
        "postgres://",
        "postgresql://",
    ]
    for value in forbidden:
        assert value not in text
