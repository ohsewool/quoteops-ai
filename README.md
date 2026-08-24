# QuoteOps AI

**견적·가격 운영(CPQ) SaaS — 결재가 숫자에 묶이는 곳**

> **가격 승인은 어디에나 있는데, "누가 어떤 견적의 어떤 가격을 승인했는가"는 어디에도 남지 않습니다.**

**고객 요청부터 견적·가격 점검·승인·리포트까지를 하나의 데이터 계보로 잇습니다. AI는 근거를 설명할 뿐, 숫자와 상태는 결정론적 백엔드와 사람만 바꿉니다.**

```
고객 요청 → 견적 작성 → 결정론적 가격 점검 → 승인 요청 → 승인/반려 → 리포트
```

이 저장소는 그 흐름을 **두 번 지은 기록**입니다. 넓게 만든 V1(API 99개, 테스트 410개)을
스스로 감사해 "승인이 견적에 묶이지 않는다"는 결함을 찾았고, V1을 증거로 동결한 뒤
좁고 깊은 V2를 다시 지었습니다 — 경위는 [CASE_STUDY.md](docs/CASE_STUDY.md) 한 장에,
전체 결정은 [V2-00 제품 계약](docs/v2/V2-00-PRODUCT-CONTRACT.md)에 있습니다.

## 현재 상태 — 정직하게

| | |
|---|---|
| V2 구현 | **V2-01 보안 게이트 ~ V2-10B 독립 릴리스 리뷰까지 완주** ([리뷰 문서](docs/v2/V2-10-RELEASE-READINESS-REVIEW.md)) |
| 테스트 | 백엔드 **69개** (CI가 실제 PostgreSQL 16으로 전부 실행) · 프런트엔드 **31개** |
| 배포 | **Render에 백엔드·프런트를 실제 배포하고 배포본 스모크 QA까지 운영한 경험**(V1, [당시 스크립트·문서](https://github.com/ohsewool/quoteops-ai/commit/fa54f3ce3cf4921f41839a5f0a35d4f21fe633cb)는 git 이력에) · V2용 프로덕션 설정(`render.yaml`: 마이그레이션 pre-deploy, readiness 게이트, docs/demo 차단) 완비 · **현재 인스턴스는 휴면** — 로컬 실행이 기본 경로입니다 |
| 상태 | 완성 후 동결. 기능 추가 계획 없음 — [비목표](docs/v2/V2-00-PRODUCT-CONTRACT.md)가 계약에 명시돼 있습니다 |

## 무엇이 다른가

- **AI는 숫자를 못 바꿉니다.** 가격 계산·검증·승인·상태 전이는 결정론적 서비스와
  권한 있는 사람만 수행하고, 핵심 흐름은 LLM 없이 완주됩니다. copilot은 저장된
  근거의 설명과 제안까지만 합니다.
- **금액은 Decimal 문자열만.** Float 유래 값은 반올림하지 않고 격리합니다. V1
  가격표는 V2 재계산과 0.01 KRW 안에서 일치할 때만 증거로 보존됩니다.
- **시드 계정이 없습니다.** 첫 관리자도 명시적 CLI(`backend.cli.create_first_user`)로만
  만들어집니다 — V1의 무조건 시드·공개 쓰기 API·선택적 인증 승인은 V2가 상속하지
  않은 결함 목록에 있습니다.

## 로컬 실행

Python 3.12+ · Node 24+ · pnpm. 통합 테스트까지 돌리려면 **V2 전용 PostgreSQL**이
필요합니다([안내](docs/development/native-postgresql.md)) — 없으면 통합 28개는
명시적 사유와 함께 skip됩니다(41개는 그대로 돕니다).

**Linux / macOS**

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.lock
.venv/bin/python -m pytest -q backend/tests        # 69 tests (DB 없으면 41 passed + 28 skipped)
cd frontend && pnpm install --frozen-lockfile && pnpm test && pnpm build
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
.\.venv\Scripts\python -m pytest -q backend/tests
.\scripts\validate-v2-environment.ps1 -Environment local   # URL·시크릿을 출력하지 않는 환경 점검
```

DB 준비 후 첫 관리자 생성:

```bash
.venv/bin/python -m backend.cli.create_first_user --username admin --display-name "V2 Admin"
```

## 더 읽기

- [CASE_STUDY.md](docs/CASE_STUDY.md) — V1을 반성하고 V2를 다시 지은 경위, 한 장
- [V2-00 제품 계약](docs/v2/V2-00-PRODUCT-CONTRACT.md) — 제품·보안·수치·경계의 전체 결정 (1,974줄)
- [V2-10B 릴리스 준비 리뷰](docs/v2/V2-10-RELEASE-READINESS-REVIEW.md) — 독립 검토와 릴리스 판정
- `docs/v2/V2-01 ~ V2-10` — 단계별 구현 보고서와 갭 로그
