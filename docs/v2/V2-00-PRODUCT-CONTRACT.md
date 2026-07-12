# QuoteOps AI V2-00 Product Contract

> Status: V2-00.1 final contract  
> Stable functional baseline: `origin/main` at `08362d5d086d5deb7f37fe3be46c5cbf1b08575c`  
> Historical release marker: `v0.1.0` at `8387c5a1445615055c94fc50278b3ffb66f0f412`  
> PR-48 reference baseline: `pr-48-cpq-workflow-app-shell-restructure` at `7bda36360c5cb7196ee8bc0c8ad06f4f24f3e277`  
> Inspection date: 2026-07-12  
> Scope: product, API, domain, architecture, test, and migration contract only  
> Implementation status: not started

## 1. Executive Summary

QuoteOps AI V2는 고객 요청, 견적, 결정론적 가격 점검, 사람의 승인 또는 반려, 리포트 생성을 연결하는 경량형 가격 운영 SaaS이자 pricing operations copilot이다. 숫자 가격, 원가, 마진, 검증 결과와 workflow decision은 결정론적 백엔드 로직과 사람의 통제로만 만들어진다. AI는 저장된 근거를 설명하고 다음 행동을 제안할 수 있지만 숫자나 상태를 변경할 수 없다.

현재 저장소는 기능 수와 API 범위는 넓다. 실제 OpenAPI에는 애플리케이션이 정의한 99개 HTTP 작업이 74개 경로에 존재하고, SQLAlchemy ORM 모델은 19개이며, 프런트엔드 API 함수는 55개다. 새 임시 SQLite 데이터베이스에서 현재 테스트 410개가 모두 통과했다. 견적 미리보기, 후보 가격, 검증, 승인, 시뮬레이션, 비교, 리포트, 감사 로그 등 다수의 동작은 실제 코드와 테스트로 확인된다.

그러나 V1은 핵심 업무 흐름을 영속적인 데이터 계보로 연결하지 못한다. `CustomerQuoteRequest`는 존재하지만 `Quote`, `QuoteLine`, 영속 `PriceCandidate`, 영속 `PriceValidationResult`는 없다. 고객 요청에서 실행하는 견적 미리보기와 후보 가격 생성은 계산 응답만 반환한다. 승인 요청은 견적이나 후보와 연결되지 않으며, 승인되어도 가격표를 변경하지 않는다. 이 안전 경계 자체는 옳지만, “어떤 고객 요청의 어떤 견적 revision에 대한 어떤 가격을 누가 승인했는가”는 추적할 수 없다.

V2의 승인된 repository strategy는 기존 저장소 내부의 점진적 feature-flag migration이 아니다. 현재 QuoteOps AI 저장소와 배포는 V1 evidence로 동결하고, 별도의 clean repository `quoteops-ai-v2`에서 V2를 구축한다.

1. stable `main`에서 검증된 backend behavior, API, model, calculation, test expectation을 선택적으로 이관한다.
2. V1 backend 전체를 복사하지 않고 Tier A core asset만 재검증해 옮긴다.
3. 영속 `Quote`, `QuoteLine`, quote revision, candidate/check snapshot을 clean domain으로 구현한다.
4. 3,168줄 `App.jsx`, `activeSection` navigation, JSX source placement에 의존하는 UI test는 V2 foundation으로 사용하지 않는다.
5. 99개 V1 API를 같은 수준으로 재구축하지 않는다. Tier A core workflow를 먼저 완성하고 Tier B는 V1에 frozen 상태로 둔다.
6. grounded AI copilot은 deterministic core 다음인 V2-08에서 구현하며 final V2 scope 안에 포함한다.
7. V1 배포는 V2-10 staging, security, migration, rollback verification이 끝날 때까지 교체하지 않는다.

### Immediate V1 Security Decision

> **V1 SECURITY STATUS: DEMO / PORTFOLIO ONLY**

- 현재 V1 배포에는 real customer, cost, competitor, approval 또는 confidential business data를 입력해서는 안 된다.
- V1을 production-secure 또는 production-ready라고 설명해서는 안 된다.
- V2-01 security gate가 통과하기 전 V1을 실제 business operation에 사용해서는 안 된다.
- 실무적으로 가능한 범위에서 V1은 private, access-restricted 또는 명확한 demo-only 표시 상태로 유지한다.
- V2는 V1의 public-write API, optional-auth approval mutation, reviewer identity 약한 결합, production demo seed behavior를 상속하지 않는다.
- 이 결정의 근거는 public product/cost/competitor/price-table writes, optional-auth approval create/approve/reject, unconditional startup seed, ineffective demo-tools guard, `create_all()` schema management, UI-only permission hiding이다.

### Verified baseline

| 항목 | 확인값 | 근거 |
|---|---:|---|
| 애플리케이션 정의 HTTP 작업 | 99 | 런타임 `app.openapi()` |
| 고유 OpenAPI 경로 | 74 | 런타임 `app.openapi()` |
| OpenAPI 컴포넌트 스키마 | 101 | 런타임 `app.openapi()` |
| SQLAlchemy ORM 모델 | 19 | `backend/models.py`, SQLAlchemy mapper 검사 |
| 프런트엔드 API 함수 | 55 | `frontend/src/api/client.js` |
| 프런트엔드 핵심 파일 | `App.jsx` 3,168줄 | `frontend/src/App.jsx` |
| pytest 테스트 함수 | 410 | 54개 `tests/test_*.py` AST 검사 및 실행 |
| FastAPI TestClient 사용 테스트 파일 | 34 | 테스트 소스 검사 |
| 현재 테스트 결과 | 410 passed, 1131 warnings | 임시 SQLite DB로 `pytest -q` 실행 |
| 기능 결정표 | 32개 | 이 문서 4절 |
| 실제 구현이 확인된 기능 영역 | 30개 | 32개 중 영속 견적과 자동 활성화는 미구현 |

## Approved Decision Summary

| 항목 | 최종 결정 |
|---|---|
| Stable functional baseline | `origin/main` commit `08362d5d086d5deb7f37fe3be46c5cbf1b08575c`를 V1 stable functional source of truth로 사용한다. `v0.1.0@8387c5a`는 그 조상인 historical release marker다. |
| PR-48 reference baseline | `pr-48-cpq-workflow-app-shell-restructure@7bda36360c5cb7196ee8bc0c8ad06f4f24f3e277`은 authenticated IA, UI restructuring attempt, frontend problem, CPQ research reference로만 사용한다. V2 frontend code foundation으로 사용하지 않는다. |
| Repository strategy | V1 저장소와 배포를 evidence로 동결하고 새 clean repository `quoteops-ai-v2`에서 V2를 구축한다. |
| Product identity | lightweight pricing operations SaaS and grounded pricing operations copilot이다. |
| Core workflow | Customer Request -> Quote Creation -> Pricing Check -> Approval Request -> Approve or Reject -> Report Generation이다. |
| AI responsibility | V2-08에서 grounded explanation, evidence summary, draft, revision suggestion을 구현한다. AI는 numeric value 또는 workflow state를 변경하지 않는다. |
| Deterministic safety boundary | 모든 숫자 계산, validation result, approval/rejection, workflow transition은 deterministic service와 authorized human만 수행한다. core workflow는 external LLM 없이 완주한다. |
| Tier A core API scope | primary workflow, supporting catalog/cost/reference data, auth/role, audit, core dashboard, health/readiness, safe demo, report, grounded AI support만 V2 completion contract로 구축한다. |
| Tier B frozen API scope | strategy template, simulation, scenario comparison, workflow job, legacy insight, price-table history/comparison, CSV/advanced operations 등 44개 V1 operation은 초기 V2 completion을 막지 않는다. |
| Current V1 deployment status | demo/portfolio only이며 production-secure 또는 production-ready가 아니다. real/confidential business data 사용을 금지한다. |
| Mandatory V2-01 security gate | public write 0, optional approval mutation 0, production demo seed 0, backend role enforcement, protected docs/status, migration framework, Decimal/Numeric KRW policy를 먼저 통과한다. |
| V2-01 entry conditions | stable baseline, clean repository, Tier A/B, roles, security, numeric, AI boundary, core journey, measurable tests가 이 문서에서 확정됐다. |
| Explicit non-goals | full CRM, ecommerce, payment/billing, CLM/e-signature, enterprise CPQ, scraping, automatic pricing decision/approval/activation, chatbot-first UX, all 99 APIs의 동등 재구축은 하지 않는다. |

**Rebuilding all 99 existing API operations to equal V2 product quality is not part of the initial V2 scope.**

## 2. Product Definition

### One-sentence definition

QuoteOps AI V2 is a lightweight pricing operations SaaS and pricing operations copilot that connects customer requests, quotes, deterministic pricing checks, human approval or rejection, and report generation.

### Product paragraph

V2는 CRM이 없는 작은 사업자의 request intake, quote workspace, pricing decision, approval inbox, report artifact를 하나의 persistent lineage로 연결한다. 가격 계산은 원가와 마진 규칙을 사용하는 deterministic backend service가 수행하고, validation은 명시적 규칙과 저장된 source snapshot으로 결정된다. AI copilot은 Quote Workspace, Pricing Check Workspace, Approval Inbox, Report Center 안에서 grounded assistance를 제공하며 별도 chatbot을 제품 중심에 두지 않는다. 승인 전에는 고객용 최종 가격, 활성 가격표, 외부 전송이 변경되지 않는다.

### In scope

- 공개 랜딩과 데모/로그인 진입
- 관리자, 매니저, 조회자 역할
- 업무 대시보드
- 고객 요청 intake와 상태 관리
- 영속 견적과 견적 라인
- 결정론적 견적 미리보기와 후보 가격
- 원가, 마진, 경쟁사 참고를 이용한 가격 점검
- 승인 요청, 승인, 반려
- 승인 결과와 연결된 HTML 리포트
- grounded AI pricing copilot과 deterministic fallback
- 감사 이력
- V2-09에서 정당화된 selected CSV operations, audit search, health, readiness, protected system status/OpenAPI
- 두 MVP 제품: A3 Flyer, Product / Brand Sticker
- 안전한 안내형 데모

### Explicitly out of scope

- 전체 CRM, 영업 파이프라인, 연락처 관리 제품
- 전자상거래, 장바구니, 결제, 청구
- 계약 수명주기 관리와 전자서명
- 복잡한 제품 configurator 또는 엔터프라이즈 CPQ 복제
- 다중 조직/테넌트 협업 기능의 V2 초기 구현
- 자동 경쟁사 스크래핑과 실시간 모니터링
- AI가 숫자 가격, 검증 결과, 승인 결과를 생성하는 동작
- 승인 없는 가격표 자동 활성화 또는 고객 전송
- 챗봇 중심 UI
- 모바일 앱, TypeScript 전환, 새로운 배포 플랫폼 도입

### AI responsibility contract

AI가 할 수 있는 일:

- 후보 가격 간 차이와 각 후보의 장점·trade-off 설명
- 원가, 마진, competitor reference context 요약
- triggered validation rule과 pricing risk 설명
- approval request reason 초안
- approver evidence 요약
- rejection 이후 revision point 제안
- grounded report summary 초안
- deterministic output을 이해 가능한 business language로 변환
- 실행하지 않는 next workflow action 제안

AI가 할 수 없는 일:

- 숫자 가격을 발명하거나 임의 변경
- cost/margin calculation 대체
- deterministic validation result override 또는 failed -> passed 변경
- quote approve/reject 또는 approval/workflow state 변경
- price table 활성화 또는 final customer price 자동 전송
- source에 없는 사실 발명
- failed deterministic process를 AI 결과로 대체
- 저장된 numeric snapshot을 조용히 변경

모든 AI output은 적용 가능한 범위에서 다음 grounding metadata를 참조한다.

- quote ID와 quote revision
- selected candidate
- pricing-check snapshot과 triggered rules
- source data timestamp
- source artifacts used
- deterministic fallback status
- AI generation timestamp

external LLM 장애, timeout 또는 미설정은 core workflow를 차단하지 않는다. deterministic fallback은 “AI generated”가 아니라 rule-based explanation으로 명시한다.

### Core product invariant

```text
customer request
-> persisted quote and lines
-> deterministic candidate prices
-> deterministic price check snapshot
-> human approval request
-> approve or reject
-> reviewable report
```

어느 단계에서도 AI 호출은 숫자, 상태 전이, 승인 또는 활성화를 결정하지 않는다. grounded AI copilot은 deterministic core 완료 후 V2-08에서 구현하며 final V2 scope에서 제외하지 않는다.

## 3. Verified Current-State Inventory

### 3.0 Baseline and repository strategy

#### A. Stable functional baseline

| 항목 | 검증 결과 |
|---|---|
| Branch/ref | `origin/main` |
| Commit | `08362d5d086d5deb7f37fe3be46c5cbf1b08575c` |
| Commit subject | `Clean remaining visible UI artifacts (#47)` |
| Remote verification | `git fetch origin --tags --prune` 후 `origin/main`이 위 commit을 가리킴 |
| CI evidence | GitHub Actions `backend-checks` completed with `success` for commit `08362d5` |
| Release relationship | `v0.1.0@8387c5a1445615055c94fc50278b3ffb66f0f412`는 `origin/main`의 ancestor |
| PR-48 relationship | PR-48 branch는 stable main보다 1 commit ahead, main은 PR-48 commit을 포함하지 않음 |

`origin/main@08362d5`는 최신 remote main이고 CI success가 확인됐으므로 stable functional baseline으로 확정한다. V2 contract에서 다음 항목의 source of truth는 이 baseline이다.

- verified backend behavior와 API behavior
- database models와 request/response schema
- deterministic pricing calculation과 business rule
- stable tests와 golden numeric expectation
- deployment/security configuration
- V1 stable functional behavior

`v0.1.0` tag는 reproducible historical release marker로 보존하지만 PR-35 이후 main 변경을 포함하지 않으므로 최신 stable functional baseline으로 선택하지 않는다.

#### B. PR-48 reference baseline

| 항목 | 확정 계약 |
|---|---|
| Branch | `pr-48-cpq-workflow-app-shell-restructure` |
| Commit | `7bda36360c5cb7196ee8bc0c8ad06f4f24f3e277` |
| Stable main과 차이 | frontend, UI source-contract tests, `docs/portfolio-ui-qa.md`만 변경; backend/config/deploy 차이 없음 |
| 사용할 수 있는 것 | authenticated IA reference, CPQ workflow labels, UI restructuring attempt, known frontend problem evidence, attached CPQ research interpretation |
| 사용해서는 안 되는 것 | V2 frontend code foundation, `App.jsx` component structure, `activeSection` routing, source-placement UI tests, V2 stable functional source of truth |

PR-48은 V2를 직접 이어서 구현할 branch가 아니다. 특히 PR-48의 `App.jsx`를 분리하거나 계속 patch하는 방식은 승인된 V2 strategy가 아니다.

#### Approved repository strategy comparison

| 선택지 | 장점 | 위험 | 결정 |
|---|---|---|---|
| Clean `quoteops-ai-v2` repository | V1 history/deployment 보존, clean domain/API/security baseline, legacy frontend/test coupling 제거, Tier A만 선택 이관 | 초기 scaffold와 contract adapter 비용, V1/V2 비교·migration evidence를 별도 유지해야 함 | **Approved default** |
| V1 repository 내부 feature-flag migration | 기존 CI/history/asset에 즉시 접근, 한 저장소에서 diff 가능 | 3,168-line App와 99 API 범위에 다시 결합, public-write/demo/auth debt 상속, old/new 장기 공존, rollback 복잡 | **Rejected as default** |

V1 repository와 배포는 read-only evidence와 comparison target으로 동결한다. V2-01에서 새 repository를 생성하고, 각 V1 asset은 evidence와 tests를 통과한 경우에만 선택 이관한다. V1 backend 전체와 legacy frontend 구조를 복사하지 않는다.

### 3.1 Frontend

현재 프런트엔드는 React 18 + Vite + JavaScript + Axios로 구성된다. `frontend/src/`의 제품 코드는 `App.jsx`, `styles.css`, `main.jsx`, `api/client.js` 네 영역에 집중돼 있다.

확인된 로그인 전 흐름:

- 공개 랜딩
- 서비스 시작 CTA
- 데모 체험 CTA
- 사용자명/비밀번호 로그인 폼
- 공개 `/api/auth/demo-users` 결과를 이용한 데모 역할 빠른 로그인

확인된 로그인 후 상위 내비게이션 순서:

1. 대시보드
2. 고객 요청
3. 견적
4. 가격 평가
5. 승인함
6. 리포트
7. 운영
8. 데모

현재 화면 전환은 URL 라우터가 아니라 `activeSection` React 상태와 조건부 렌더링으로 처리된다. 로그인 토큰은 `localStorage`의 `quoteops_token`에 저장된다. 로그인 후 다수 API를 한 번에 호출하고 일부 실패는 `.catch(() => {})`로 무시한다. 모든 상위 메뉴는 동일 앱 셸에 존재하며, 역할별 버튼 숨김은 있으나 백엔드 권한과 항상 일치하지 않는다.

현재 프런트엔드가 호출하는 API 함수는 55개다. 상품 생성/수정, 원가 프로필 CRUD, 경쟁사 CRUD, 가격표 CRUD 자체는 프런트엔드 클라이언트에 연결되지 않았고, CSV 운영 기능을 통해 일부 데이터를 관리한다.

### 3.2 Backend and API

현재 백엔드는 FastAPI, Pydantic, SQLAlchemy를 사용한다. `backend/main.py`가 23개 라우터 모듈을 등록하고 `backend/services/`의 결정론적 서비스가 계산과 도메인 동작을 담당한다. 기본 로컬 DB는 SQLite이며 `DATABASE_URL`로 PostgreSQL을 사용할 수 있다.

앱 lifespan은 시작할 때 `Base.metadata.create_all()`과 `seed_demo_data()`를 항상 실행한다. 마이그레이션 프레임워크는 없다. `QUOTEOPS_DEMO_TOOLS_ENABLED` 설정은 system status에 표시되지만 현재 demo 라우터 접근을 차단하지 않으며, startup demo seed도 제어하지 않는다.

현재 권한 분포:

| 권한 분류 | 작업 수 | 의미 |
|---|---:|---|
| 공개 | 34 | 인증 없이 호출 가능 |
| 선택 인증 | 7 | 토큰이 있으면 actor를 기록하지만 없어도 호출 가능 |
| 인증 사용자 | 1 | `/api/auth/me` |
| 조회자 이상 | 35 | viewer, manager, admin |
| 매니저 이상 | 20 | manager, admin |
| 관리자 | 2 | admin |

공개 쓰기에는 상품, 경쟁사, 경쟁사 가격, 원가 프로필, 가격표, 가격표 항목 CRUD와 고객 요청 생성이 포함된다. 승인 요청 생성·승인·반려는 선택 인증이므로 인증 없이도 실행 가능하다. 이것은 프런트엔드 버튼 권한과 다르고 V2 구현 전 해결해야 할 보안 계약 문제다.

### 3.3 Deterministic pricing behavior

현재 확인된 계산식:

```text
unit_cost = material_cost + labor_cost + overhead_cost
unit_price = unit_cost / (1 - margin_rate)
total_cost = unit_cost * quantity
total_price = unit_price * quantity
gross_profit = total_price - total_cost
estimated_margin_rate = gross_profit / total_price
```

후보 가격 기본 마진은 `0.25`, `0.35`, `0.45`이고 전략 이름은 `low_margin`, `target_margin`, `premium_margin`이다. 사용자 지정 마진은 `custom_margin_N`으로 표시된다. 계산은 소수 둘째 자리로 반올림된다.

현재 가격 검증 규칙:

- 후보 단가가 단위원가 이상인지 검사: 실패 시 `error`
- 예상 마진이 최소 마진 이상인지 검사: 손실이면 `error`, 이익이지만 최소 미달이면 `warning`
- 경쟁사 평균의 80% 미만인지 검사: `warning`
- 경쟁사 평균의 150% 초과인지 검사: `warning`
- 오류 실패가 있으면 `failed/high`
- 경고 실패만 있으면 `warning/medium`
- 모두 통과하면 `passed/low`

현재 구현되지 않은 것으로 확인된 가격 도메인 기능:

- 수량 구간별 가격표 모델
- 경쟁사 가격의 수량 필드
- 경쟁사 유형별 실제 가중치 계산
- price inversion 검사
- unit price progression 검사
- discount cliff 검사
- 전략 템플릿의 `risk_preference`를 계산에 반영하는 로직
- 영속 후보 가격 및 영속 검증 결과
- 승인된 후보를 가격표 버전에 연결하는 로직

### 3.4 Approval and reporting

승인 요청은 생성 시 가격 검증을 다시 실행하고 그 결과를 `PriceApprovalRequest`에 스냅샷으로 저장한다. 상태는 `pending`에서 `approved` 또는 `rejected`로만 서비스 전이된다. 스키마에는 `cancelled`도 있으나 cancel API는 없다. 승인·반려 후 같은 요청을 다시 처리하면 400을 반환한다.

승인 요청에는 `quote_id`, `candidate_id`, 요청자 사용자 ID가 없다. `reviewer_name`은 요청 본문의 문자열이며 인증 사용자와 강제로 일치하지 않는다. 승인 또는 반려는 가격표를 자동 변경하지 않는다.

HTML 리포트는 `quote_preview`, `price_validation`, `approval_request`, `pricing_simulation`, `scenario_comparison`, `dashboard_summary` 유형을 지원한다. `quote_preview`와 `price_validation` 리포트도 실제 Quote가 아니라 승인 요청 스냅샷을 source로 사용한다. 리포트 상태 필드는 없고 생성 성공 시 완성된 HTML을 바로 저장한다.

### 3.5 Data and persistence

확인된 ORM 모델 19개:

- `User`
- `Product`
- `Competitor`
- `CompetitorPrice`
- `CostProfile`
- `PriceTable`
- `PriceTableItem`
- `PriceApprovalRequest`
- `AuditLog`
- `PricingSimulation`
- `PricingSimulationScenario`
- `PricingStrategyTemplate`
- `CustomerQuoteRequest`
- `PriceTableSnapshot`
- `PriceTableSnapshotItem`
- `WorkflowJob`
- `ScenarioComparison`
- `ScenarioComparisonItem`
- `HtmlReport`

데이터 구조의 주요 위험:

- 금액과 마진이 `Float`로 저장된다.
- 여러 active cost profile을 막는 제약이 없고 서비스는 가장 큰 ID를 선택한다.
- `CostProfileCreate.target_margin_rate`는 스키마에서 `1.0`을 허용하지만 계산 서비스는 `< 1`을 요구하므로 0으로 나누기가 가능하다.
- 가격표 항목에 수량 또는 수량 구간이 없다.
- 같은 가격표·상품 조합의 중복 항목을 막는 unique constraint가 없다.
- `AuditLog.actor_user_id`는 외래 키가 아니다.
- 여러 `created_by_username` 필드는 User 외래 키가 아닌 문자열이다.
- 시간은 대부분 timezone-naive `datetime.utcnow()`를 사용한다.
- `create_all`만 있고 스키마 버전과 롤백 가능한 migration이 없다.
- organization/tenant 경계가 없다.

### 3.6 Demo, operations, deployment

startup seed는 A3 Flyer와 Product / Brand Sticker, 세 데모 사용자, 전략 템플릿, 경쟁사, 원가, draft/active 가격표를 생성한다. 데모 도구 서비스는 추가로 Banner, Sticker, Tumbler, Hoodie, Package Box를 만든다. 이는 AGENTS.md의 두 제품 MVP 범위와 충돌한다.

Render 설정은 백엔드 Web Service 하나를 선언한다. 프런트엔드는 문서상 Render Static Site로 수동 설정한다. 배포 자체는 자동화되지 않는다. system status는 원본 DB URL과 비밀값을 반환하지 않으며, production CORS에서 wildcard를 제거한다.

현재 환경변수 계약:

| 변수 | 실제 소비 위치 | 현재 의미 | V2 판단 |
|---|---|---|---|
| `DATABASE_URL` | `backend/config.py`, `backend/db.py` | SQLite 또는 PostgreSQL 연결 | name/concept 참고; V2는 separate DB, PostgreSQL validation, Alembic 적용 |
| `QUOTEOPS_ENV` | `backend/config.py` | local/production 환경 라벨과 CORS 처리 | environment-policy concept만 새 V2 config에서 구현 |
| `QUOTEOPS_AUTH_SECRET` | `backend/auth.py` | HMAC bearer signature | V1 fallback/transport 미이관; V2-01 auth design에 필요한 secret은 startup validation과 rotation policy 적용 |
| `QUOTEOPS_DEMO_TOOLS_ENABLED` | config/status만 | safe status에는 보이나 route/startup을 차단하지 않음 | V1 변수 미이관; V2는 explicit non-production demo policy와 route/startup guards 신규 구현 |
| `DEMO_TOOLS_ENABLED` | config legacy alias | 위 변수 fallback | V2에 미이관 |
| `QUOTEOPS_CORS_ORIGINS` | `backend/config.py` | comma-separated origins | behavior 참고; V2는 fail-closed production origin validation 신규 구현 |
| `ALLOWED_ORIGINS` | config legacy alias | CORS fallback | V2에 미이관 |
| `OPENAI_API_KEY` | config/status only | configured 여부만 표시 | current V1 external AI 호출 없음; V2-08은 새 provider integration으로 구현 |
| `LLM_ENABLED` | `.env.example` only | 현재 코드에서 소비하지 않음 | 구현된 feature flag로 간주하지 않음 |
| `OPENAI_MODEL` | `.env.example` only | 현재 코드에서 소비하지 않음 | V1 변수 미이관; V2-08 provider/model allowlist config를 별도 정의 |
| `VITE_API_BASE_URL` | `frontend/src/api/client.js` | public backend base URL | concept만 새 V2 frontend config에서 구현; secret 저장 금지 |
| `QUOTEOPS_DEPLOYED_BACKEND_URL` | deployed QA script | 선택적 remote QA target | QA target concept만 V2 smoke tooling에서 재평가 |
| `QUOTEOPS_DEPLOYED_FRONTEND_URL` | deployed QA script | 선택적 remote QA target | QA target concept만 V2 smoke tooling에서 재평가 |
| `PORT`, `PYTHON_VERSION` | Render runtime/config | service bind/runtime version | V1 deployment evidence; V2 deploy config에서 명시적으로 재선택 |

### 3.7 Tests

새 임시 SQLite DB에서 실행한 현재 기준선:

```text
410 passed, 1131 warnings in 74.93s (0:01:14)
```

현재 테스트가 강하게 보장하는 영역:

- FastAPI 라우트의 성공/실패 응답
- 가격 계산 공식과 대표 숫자
- 승인 pending -> approved/rejected 동작
- 감사 로그 생성과 민감정보 제거
- CSV import/export
- 시뮬레이션, 비교, 리포트, demo reset 안전성
- health/readiness/system status/OpenAPI
- Render 설정과 tracked secret/generated file 방지
- 핵심 결정론적 business flow

현재 테스트가 약하게 보장하는 영역:

- 실제 브라우저 렌더링과 클릭 흐름
- 로그인부터 리포트까지 사용자 E2E
- 접근성, 포커스, 모바일 오버플로
- 프런트엔드 요청 race/error recovery
- PostgreSQL 통합과 migration
- 동시 요청과 중복 승인
- 권한이 없는 현재 공개/선택 인증 쓰기 API

54개 테스트 파일 중 34개가 TestClient를 사용하고, 18개가 프런트엔드 JSX/CSS/API client 소스를 직접 검사한다. UI 테스트 다수는 특정 문구와 JSX 소스 배치를 검사하며 실제 브라우저를 실행하는 테스트는 없다. 1,131개 경고의 대부분은 `datetime.utcnow()` deprecation이며 FastAPI TestClient/httpx deprecation 경고도 있다.

## 4. Keep / Rewrite / Exclude Decision Matrix

결정 정의:

- **유지**: stable V1에서 검증된 behavior, contract, sanitizer 또는 golden expectation을 clean V2로 선택 이관한다. V1 코드를 그대로 복사한다는 뜻이 아니다.
- **재작성**: 기능 목적은 유지하지만 V2 repository에서 domain lineage, authorization, persistence 또는 UI를 새로 구현한다.
- **제외**: Tier B로 V1에 frozen 상태로 두며 core V2 completion을 막지 않는다.

| ID | 기능 | Tier | 현재 구현 상태와 근거 | V2 결정 | 이유 / 의존 / 위험 | 단계 | 측정 가능한 완료 조건 |
|---|---|---|---|---|---|---|---|
| F01 | 공개 랜딩 | A | `App.jsx`에 hero, 로그인/데모 CTA 존재 | 재작성 | legacy App와 분리된 clean public shell 필요 | V2-02 | `/`에서 인증 없이 렌더링, 기술 진단 미노출, login/demo CTA 작동 |
| F02 | 로그인/세션 | A | `/api/auth/login`, `/me`, HMAC bearer, localStorage | 재작성 | production seed와 backend authorization부터 재설계 | V2-01/02 | 기본 계정 0, protected route 401/403, logout 후 접근 불가 |
| F03 | 관리자/매니저/조회자 데모 역할 | A | User role과 demo quick login 존재 | 재작성 | demo-only environment와 normal role policy 분리 | V2-01/02/09 | demo flag에서만 credential hint, role/security tests 통과 |
| F04 | 대시보드 | A | KPI/insight API와 업무형 PR-48 copy | 재작성 | PR-48은 IA reference만 사용; actual Quote data 필요 | V2-02/04 | request/quote/approval core data로 업무 시작점 표시 |
| F05 | 상품 마스터 | A | Product CRUD/model, SKU unique | 유지 | 두 MVP 제품 기준 데이터 behavior 선택 이관 | V2-01/05 | viewer summary read, manager/admin write, two-product fixture |
| F06 | 원가 프로필 | A | CostProfile CRUD, active 최신 ID 사용 | 유지 | formula input은 재사용, auth/Decimal/active invariant는 새 구현 | V2-01/05 | active 1개, margin `<1`, raw detail viewer 차단 |
| F07 | 고객 요청 | A | CRUD/status/preview/candidates API와 UI 존재 | 재작성 | public create와 unconstrained transition 제거, Quote lineage 추가 | V2-03 | authenticated create, strict transitions, actor audit |
| F08 | 견적 생성 | A | UI 명칭과 transient preview만 존재; Quote/Line 없음 | 재작성 | persistent core domain이 미구현 | V2-04 | Quote/Line/revision 저장과 request lineage 재현 |
| F09 | 견적 미리보기 | A | `/api/quote-preview`, deterministic service | 유지 | formula와 golden outputs 선택 이관 | V2-04/05 | stable baseline golden compatibility와 Decimal reproducibility |
| F10 | 후보 가격 계산 | A | `/api/candidate-prices`, 3개 기본 마진 | 유지 | deterministic behavior 선택 이관, snapshot은 신규 | V2-05 | selected candidate가 Quote revision snapshot에 저장 |
| F11 | 가격 검증 | A | 원가/마진/경쟁사 평균 4개 check | 재작성 | verified rules는 이관, missing rules와 immutable snapshot 구현 | V2-05 | severity contract, failed block, warning reason, golden tests |
| F12 | 경쟁사 가격 참고 | A | product별 reference price 평균; `channel` 미사용 | 재작성 | quantity/type/price basis가 필요 | V2-05 | source quantity/type/timestamp와 grounded summary |
| F13 | 전략 템플릿 | B | CRUD와 후보/시뮬레이션 적용 API 존재 | 제외 | advanced feature, `risk_preference` 미사용 | V2-09 이후 별도 결정 | core UI/API/DoD에 미포함, V1 frozen |
| F14 | 가격표/버전 | B | PriceTable/Item/Snapshot 존재 | 재작성 | 재도입 시에만 새 contract가 필요함; core Quote approval/report에는 불필요 | V2-09 이후 별도 결정 | initial V2 이관 0, core 자동 activation 0, legacy API frozen |
| F15 | 가격표 비교 | B | live table/snapshot 비교 API와 테스트 존재 | 유지 | proven read-only behavior지만 advanced | V2-09 selected adapter | adapter 선택 전 V1 frozen, core completion 비차단 |
| F16 | 시뮬레이션 | B | persisted simulation/scenarios API | 제외 | advanced pricing feature | V2-09 이후 별도 결정 | top-level V2 nav/API 없음 |
| F17 | 시나리오 비교 | B | persisted comparison, summary API | 제외 | simulation과 중복되는 advanced feature | V2-09 이후 별도 결정 | report dependency 포함 재도입 여부 평가 |
| F18 | 승인 요청 | A | validation snapshot 저장, Quote 연결 없음 | 재작성 | optional auth 제거, quote/candidate/requester lineage 필수 | V2-06 | authenticated requester, revision/check IDs, self-approval guard |
| F19 | 승인 | A | pending -> approved, optional auth | 재작성 | reviewer identity와 concurrency 보강 | V2-06 | actor from session, pending 1회 transition, race test |
| F20 | 반려 | A | pending -> rejected, optional auth | 재작성 | reason과 new revision flow 필요 | V2-06 | reason required, original evidence immutable |
| F21 | 리포트 생성 | A | 6종 HTML report 저장/조회 | 재작성 | approved Quote source와 grounding metadata 필요 | V2-07 | source revision 숫자 일치, preview/regeneration history |
| F22 | 감사 로그 | A | actor/action/entity/metadata sanitize | 유지 | sanitizer와 event expectations 선택 이관 | V2-01~09 | 모든 core transition actor, token/secret 0 |
| F23 | 작업 로그/Workflow Job | B | 3개 job type, HTTP 안에서 동기 실행 | 제외 | background job이 아니며 core에 불필요 | V2-09 이후 별도 결정 | V1 frozen, V2 core UI 미노출 |
| F24 | CSV 가져오기/내보내기 | B | product/cost/competitor price 3종, audit | 유지 | selected parser behavior만 operations phase에서 평가 | V2-09 | core completion 비차단, raw cost export viewer 금지 |
| F25 | 데모 데이터 | A | startup seed + seed/reset/full scenario | 재작성 | production auto seed/flag failure/5-product conflict | V2-01/02/09 | production seed 0, route guard, two-product guided demo |
| F26 | 시스템 상태 | A | `/api/system/status`, secret-safe summary | 유지 | safe fields 선택 이관; production admin-only | V2-01/09 | anonymous production 401/403, secret marker 0 |
| F27 | health/readiness | A | health/live/ready, ready failure 503 | 유지 | deployment safety core | V2-01/10 | three public endpoints and 503 readiness contract |
| F28 | OpenAPI | A | `/openapi.json`, `/docs`, 99 app operations | 유지 | Tier A contract source; production protected/disabled | V2-01 onward | admin/disabled production policy test, schema snapshot |
| F29 | 배포 진단 | A | Render config와 QA/security scripts | 유지 | V1/V2 staging and rollback evidence | V2-10 | core smoke, CORS, auth, no credential exposure |
| F30 | 결정론적 dashboard insights | B | rule-based insight API | 제외 | Quote lineage 완성 전 해석 불완전 | V2-09 이후 별도 결정 | core dashboard만 Tier A, legacy insights frozen |
| F31 | grounded explanation/copilot | A | current deterministic English explanation only | 재작성 | final V2 scope의 contextual copilot, no core dependency | V2-08 | grounding metadata, fallback, no numeric/state mutation |
| F32 | 자동 가격표 활성화 | A safety | 미구현이나 public status update로 우회 가능 | 제외 | 금지해야 하는 core safety invariant | 모든 단계 | approval/report/AI가 activation을 실행하지 않음 |

결정 합계: **유지 12 / 재작성 14 / 제외 6 / 총 32**.

## 5. Personas and Permissions

### 5.1 V2 role contract

| 역할 | 주요 목적 | 볼 수 있는 화면 | 허용 작업 | 금지 작업 | 승인 권한 | 운영/기술 정보 |
|---|---|---|---|---|---|---|
| 관리자 | 기준 데이터, 보안, 데모, 운영 안전 관리 | 모든 화면 | 상품/원가/경쟁사 설정, raw cost profile, CSV import/export, demo seed/reset, audit, 모든 manager 작업 | 승인 없는 activation, secret/raw DB URL 조회 | 타인이 요청한 Quote 승인/반려. normal 환경 self-approval 금지 | production OpenAPI와 detailed status 접근 가능 |
| 매니저 | 요청부터 견적·가격 점검·승인·리포트까지 처리 | 대시보드, 고객 요청, 견적, 가격 점검, 승인함, 리포트, 제한 운영 | request/Quote 작성, candidate/check, approval request, 타인 요청 승인/반려, report | self-approval, security/user 설정, raw cost admin, demo reset, activation | 타인이 요청한 Quote 승인/반려 | 업무 audit 요약과 허용된 operations만 접근 |
| 조회자 | 내부 가격 업무를 읽고 검토 | 대시보드, 요청, 견적, 가격 점검, 승인함, 리포트 | 목록/상세/report 조회, summarized total cost/margin/risk/validation 확인 | 생성/수정/승인/반려/import, raw cost components/profile/CSV/admin config | 없음 | public health 요약만; detailed status/OpenAPI/raw log 금지 |

### 5.2 Current backend reality

- `require_role("viewer")`는 viewer 이상을 의미한다.
- `require_role("manager")`는 manager/admin을 허용한다.
- demo seed/reset은 admin, full scenario는 manager 이상이다.
- audit logs는 manager 이상이다.
- 상품/경쟁사/원가/가격표 CRUD는 현재 공개다.
- 승인 생성/승인/반려는 현재 선택 인증이다.
- 프런트엔드는 역할에 따라 일부 버튼을 숨기지만 API 권한을 대신할 수 없다.
- user management, password reset, invitation, organization, session revocation은 없다.
- 현재 demo user endpoint와 startup seed는 production에서도 코드상 차단되지 않는다.

### 5.3 Permission invariants for V2

1. 권한은 반드시 백엔드에서 강제한다.
2. UI 버튼 숨김은 보조 표현이며 보안 경계가 아니다.
3. 가격, 원가, 경쟁사 데이터의 공개 API는 없다.
4. 승인 actor는 요청 body가 아니라 인증 사용자에서 결정한다.
5. normal 환경에서 requester와 reviewer가 같으면 403이다. explicitly enabled demo 환경만 self-approval을 허용하고 visible demo label과 `demo_self_approval_used` audit event를 남긴다.
6. V2 initial customer request create는 manager/admin만 가능하다. public intake는 out of scope이며 추후 별도 restricted endpoint로만 도입한다.
7. viewer는 total cost, resulting margin, risk summary, validation outcome만 보고 raw component cost/profile/CSV/config를 볼 수 없다.
8. demo 계정과 credential hint는 demo-enabled environment에서만 존재한다.
9. `/api/health`, `/api/health/live`, `/api/health/ready`만 production public system API다. detailed status와 OpenAPI는 admin-only 또는 disabled다.

## 6. Core User Journeys

### 6.1 Primary V2 journey

| 단계 | 사용자 목적 | 현재 자산 | 현재 단절 | V2 결과 |
|---|---|---|---|---|
| 1. 고객 요청 등록 | 고객 요구, 상품, 수량, 납기 기록 | CustomerQuoteRequest API/model | public create, transition 자유 | authenticated intake와 명시적 status transition |
| 2. 요청을 견적으로 전환 | 작업 가능한 견적 생성 | request preview/candidate endpoints | Quote/Line 미존재 | persisted Quote와 QuoteLine, request linkage |
| 3. 후보 가격 생성 | 원가/마진에 따른 선택지 생성 | candidate service | 결과 비영속 | immutable candidate snapshot |
| 4. 가격 점검 | 위험과 규칙 통과 여부 판단 | validation service | 단일 가격, rule 부족, 비영속 | selected candidate에 연결된 check snapshot |
| 5. 승인 요청 | 사람이 판단할 근거 제출 | approval service | quote/candidate/requester 연결 없음 | Quote revision 기반 approval request |
| 6. 승인 또는 반려 | 근거를 확인하고 1회 결정 | approve/reject service | optional auth, reviewer body | authenticated actor, strict transition, history |
| 7. 리포트 생성 | 승인 결과를 공유 가능한 문서로 생성 | HTML report service | Quote source 없음 | approved Quote를 source로 report 생성 |

### 6.2 Happy-path acceptance journey

```gherkin
Given a manager is authenticated
And an active cost profile exists for an MVP product
When the manager creates a customer request
And converts the request into a persisted quote
And adds at least one quote line
And generates deterministic candidates
And selects a candidate whose pricing check is complete
And submits the quote for approval
And an authorized reviewer approves it
And the manager generates a report
Then every artifact references the same customer request and quote revision
And the report reproduces the approved numeric snapshot
And no price table is activated automatically
And audit entries identify the authenticated actors
```

### 6.3 Rejection path

반려는 기존 승인 스냅샷을 수정하지 않는다. 반려된 견적은 같은 revision을 다시 pending으로 바꾸지 않고, 수정 가능한 새 revision 또는 draft 상태로 돌아간다. 새 후보/검증/승인 요청은 새 revision에 연결한다.

### 6.4 Failure paths

- active cost profile 없음: 409 `active_cost_profile_required`
- quantity <= 0: 422 schema validation으로 통일
- margin >= 1: 저장과 계산 모두 422로 차단
- `failed/high`: 승인 요청을 차단하고 admin override를 제공하지 않음
- `warning/medium`: written reason이 있을 때만 승인 요청 허용
- `passed/low`: 정상 진행
- 이미 처리된 approval: 409 Conflict
- report source가 approved가 아님: 409
- token 만료/role 부족: 401/403

## 7. Information Architecture

### 7.1 Pre-login

```text
Public Landing
├─ 서비스 시작 -> 로그인
├─ 데모 체험 -> demo-enabled role entry
└─ 제품 흐름 -> 요청 -> 견적 -> 가격 점검 -> 승인 -> 리포트
```

공개 화면에는 health, readiness, OpenAPI, DB, CSV, audit log, demo reset, raw JSON을 노출하지 않는다.

### 7.2 Post-login

```text
Authenticated Workspace
├─ 대시보드
├─ 고객 요청
│  ├─ 목록
│  └─ 상세 / 견적으로 전환
├─ 견적
│  ├─ 목록
│  └─ 상세 / 라인 / 요약 / 승인 요청
├─ 가격 점검
│  ├─ 후보 비교
│  ├─ 검증 근거
│  └─ grounded copilot 설명 (V2-08, contextual)
├─ 승인함
│  ├─ inbox
│  └─ 상세 / 승인 / 반려
├─ 리포트
│  ├─ 문서
│  ├─ 미리보기
│  └─ 생성 이력
├─ 운영
│  ├─ 기준 데이터
│  ├─ CSV
│  ├─ 감사 로그
│  └─ 시스템 / API / 배포 진단
└─ 데모 (demo-enabled 환경만)
```

### 7.3 Placement rules

- 로그인 후 대시보드는 마케팅 랜딩이 아니다.
- 가격 점검은 핵심 의사결정 workspace다.
- 승인함은 list/detail inbox다.
- 시뮬레이션과 시나리오 비교를 core V2 navigation/UI에 넣지 않는다. V2-09 이후 선택 adapter가 생겨도 Operations에 격리한다.
- DB, OpenAPI, readiness, raw logs, raw JSON은 일반 업무 화면에 없다.
- 기술 및 진단 정보는 운영 화면에 격리한다.
- 데모는 개발자 도구 모음이 아니라 안내형 업무 시연이다.

## 8. Screen Contracts

### 8.1 Public Landing

| 계약 | 내용 |
|---|---|
| 사용자 | 미인증 방문자 |
| 핵심 작업 | 제품을 이해하고 로그인 또는 데모를 시작한다 |
| 입력 | 없음 |
| 출력 | 제품 정의, 6단계 흐름, 안전 경계 |
| 대표 상태 | anonymous |
| CTA | 서비스 시작, 데모 체험 |
| 다음 화면 | 로그인 또는 demo role entry |
| API | static environment policy로 demo CTA를 결정; no credential/data API call |
| 빈/로딩/오류 | 정적 shell은 API 없이 렌더링. demo 상태 실패는 CTA만 비활성화 |
| 숨김 | health, DB, OpenAPI, CSV, audit, credentials |

### 8.2 Login and Demo Entry

| 계약 | 내용 |
|---|---|
| 사용자 | 미인증 내부 사용자 또는 demo 방문자 |
| 핵심 작업 | 유효한 세션을 만든다 |
| 입력 | username, password 또는 demo role |
| 출력 | 현재 사용자와 role |
| 대표 상태 | idle, submitting, invalid, expired |
| CTA | 로그인, 역할로 체험 |
| 다음 화면 | 대시보드 |
| API | `POST /api/auth/login`, `GET /api/auth/me`; demo endpoint는 환경 제한 |
| 오류 | 401은 자격 증명 오류, network는 재시도 안내 |
| 숨김 | token, password hash, auth secret, raw exception |

### 8.3 Dashboard

| 계약 | 내용 |
|---|---|
| 사용자 | 모든 인증 역할 |
| 핵심 작업 | 오늘 처리할 가장 중요한 업무 하나를 연다 |
| 입력 | 역할, 선택적 필터 |
| 출력 | 대기 승인, 진행 견적, 최근 요청, 지연 항목, 최근 활동 |
| 대표 상태 | normal, no-work, partial-data |
| CTA | 새 고객 요청, 새 견적, 승인함 보기, 가격 점검 열기 |
| 다음 화면 | 선택한 업무 상세 |
| API | `GET /api/dashboard/summary`; V2 quote metrics adapter |
| 빈 상태 | 현재 처리할 업무가 없습니다. demo-enabled이면 데모 안내 |
| 로딩 | KPI skeleton과 목록 skeleton을 분리 |
| 오류 | 섹션별 재시도. 전체 blank page 금지 |
| 숨김/이동 | health/OpenAPI/DB/CSV는 운영으로 이동 |

### 8.4 Customer Requests

| 계약 | 내용 |
|---|---|
| 사용자 | manager/admin 작성, viewer 조회 |
| 핵심 작업 | 요청을 검토하고 견적으로 전환한다 |
| 입력 | 고객명, 연락처, 회사, 상품, 수량, 납기, 메모, 담당자 |
| 출력 | 요청 목록, 상세, 상태, 연결된 Quote |
| 대표 상태 | new, reviewing, quoted, closed, cancelled |
| CTA | 요청 등록, 검토 시작, 견적으로 전환 |
| 다음 화면 | Quote detail |
| API | 기존 request CRUD + proposed conversion endpoint |
| 빈 상태 | 등록된 고객 요청이 없습니다 |
| 로딩 | 목록과 상세 독립 로딩 |
| 오류 | 저장 실패 시 입력 유지, transition conflict 표시 |
| 숨김/이동 | 후보 비교, 시스템 상태, 전체 audit는 다른 화면 |

### 8.5 Quote Workspace

| 계약 | 내용 |
|---|---|
| 사용자 | manager/admin 작성, viewer 조회 |
| 핵심 작업 | 라인과 조건을 정리해 가격 점검 가능한 견적을 만든다 |
| 입력 | 고객 요청, quote metadata, line product, quantity, options, notes |
| 출력 | line totals, quote totals, revision, status, next action |
| 대표 상태 | draft, pricing_review, approval_pending, approved, rejected, cancelled |
| CTA | 라인 저장, 가격 점검으로 이동, 승인 요청, 문서 미리보기 |
| 다음 화면 | 가격 점검 또는 승인함 |
| API | proposed Quote APIs + retained quote preview |
| AI context | V2-08에서 current Quote revision/lines/totals를 grounding으로 revision suggestion을 표시; 적용은 manager action이며 숫자/상태 자동 변경 없음 |
| 빈 상태 | 아직 라인 아이템이 없습니다 |
| 로딩 | header/lines/summary 독립 skeleton |
| 오류 | optimistic save 금지. 실패 시 dirty state 유지 |
| 숨김/이동 | raw JSON, health, full audit dump는 운영 |

### 8.6 Pricing Check Workspace

| 계약 | 내용 |
|---|---|
| 사용자 | manager/admin 실행, viewer 조회 |
| 핵심 작업 | 적용 후보를 선택하고 승인 필요 여부를 판단한다 |
| 입력 | Quote revision, cost profile snapshot, margin rules, competitor context |
| 출력 | 기준가, 원가, 후보가, 마진, risk, checks, comparison |
| 대표 상태 | not_checked, ready, needs_review, blocked |
| CTA | 후보 생성, 후보 선택, 검증, 승인 요청, 사유 메모 |
| 다음 화면 | 승인함 또는 Quote 수정 |
| API | retained candidate/validation services through Quote adapter |
| AI context | V2-08에서 candidate 차이, trade-off, triggered rule/risk를 selected snapshot ID와 함께 설명; candidate 생성/수정 금지 |
| 빈 상태 | 점검할 견적이 없습니다 |
| 로딩 | 계산 진행 상태와 이전 snapshot 구분 |
| 오류 | 계산 실패 이유와 수정 가능한 입력 표시 |
| 숨김/이동 | customer intake, document logs, system diagnostics |

### 8.7 Approval Inbox

| 계약 | 내용 |
|---|---|
| 사용자 | manager/admin 결정, viewer 조회 |
| 핵심 작업 | 근거를 확인하고 승인 또는 반려한다 |
| 입력 | approval comment 또는 required rejection reason; override 입력 없음 |
| 출력 | requestor, Quote revision, submission reason, before/after, margin/risk/rule hits, timeline |
| 대표 상태 | pending, approved, rejected, cancelled |
| CTA | 승인, 반려, 원본 견적 열기 |
| 다음 화면 | 리포트 또는 revised Quote |
| API | hardened existing approval APIs |
| AI context | V2-08에서 evidence summary와 approval-reason draft를 제공; reviewer decision/state mutation 권한 없음 |
| 빈 상태 | 현재 처리할 승인 항목이 없습니다 |
| 로딩 | inbox와 detail 독립 skeleton |
| 오류 | 409이면 최신 상태 재조회 |
| 숨김/이동 | 전체 Quote 편집, simulation input, OpenAPI/CSV |

### 8.8 Report Center

| 계약 | 내용 |
|---|---|
| 사용자 | manager/admin 생성, viewer 조회 |
| 핵심 작업 | 승인된 견적의 문서를 생성하고 확인한다 |
| 입력 | approved Quote revision, report title/type |
| 출력 | report list, preview, source, generated timestamp, history |
| 대표 상태 | ready, archived; generation failure creates no ready row |
| CTA | 문서 생성, 미리보기, 재생성 |
| 다음 화면 | report preview 또는 Quote |
| API | existing HTML report adapter with Quote source |
| AI context | V2-08에서 approved source artifacts만 사용한 report-summary draft; saved report numbers/content source는 deterministic snapshot |
| 빈 상태 | 아직 생성된 문서가 없습니다 |
| 로딩 | 목록/preview 분리 |
| 오류 | source/status 오류와 retry 안내 |
| 숨김/이동 | raw HTML/API payload, template debug, readiness |

### 8.9 Operations

| 계약 | 내용 |
|---|---|
| 사용자 | admin, 일부 manager |
| 핵심 작업 | 기준 데이터와 시스템 상태를 안전하게 관리한다 |
| 입력 | CSV, filters, safe config actions |
| 출력 | import summary, audit trail, health/readiness, API link |
| 대표 상태 | healthy, degraded, unauthorized |
| CTA | CSV import/export, 상태 재확인, audit 검색, OpenAPI 열기 |
| API | import/export, audit, health, readiness, status |
| 오류 | 기술 상세는 sanitize 후 표시 |
| 숨김 | secret, raw DB URL, token, password hash |

### 8.10 Guided Demo

| 계약 | 내용 |
|---|---|
| 사용자 | demo-enabled 환경의 방문자/admin |
| 핵심 작업 | 핵심 업무 흐름을 순서대로 체험한다 |
| 입력 | demo role, start/reset |
| 출력 | 현재 단계, 생성된 demo artifact, 다음 deep link |
| 대표 상태 | unavailable, ready, in_progress, complete |
| CTA | 데모 시작, 다음 단계, 진행 초기화 |
| API | gated demo status/seed/scenario/guide/reset |
| 빈 상태 | 데모를 시작하면 샘플 workspace가 준비됩니다 |
| 오류 | production에서는 404 또는 disabled 응답 |
| 숨김 | SQL, raw health output, internal test controls |

## 9. Current API Contract

### 9.1 Reading guide

OpenAPI가 직접 포함하는 애플리케이션 작업은 99개, 고유 경로는 74개다. FastAPI framework가 제공하는 `/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc`는 이 99개에 포함하지 않는다.

권한 약어:

- `P`: public
- `O`: optional bearer; 토큰 없이도 실행 가능
- `U`: authenticated user
- `V`: viewer 이상
- `M`: manager 이상
- `A`: admin

공통 상태 코드:

- Pydantic 입력 오류: 422
- 필수 인증 누락/만료: 401
- 역할 부족: 403
- 서비스 입력/상태 오류: 400
- 리소스 없음: 404
- readiness 실패: 503

`FE`는 현재 `frontend/src/api/client.js`와 `App.jsx`에서 호출되는지를 뜻한다.

#### Current-operation tier map

Tier는 현재 V1 기능의 존재 여부가 아니라 초기 V2에서의 계약 책임을 뜻한다. Tier A는 핵심 흐름과 시스템 안전에 필요한 작업이며 선택 이관 또는 신규 구현, backend 권한 강제, 영속 lineage, 계약 테스트가 필수다. Tier B는 V1에 동결하고 V2 core 완료를 막지 않으며, V2-09 이후 별도 근거가 있을 때만 adapter, 선택 재도입, 정식 폐기 중 하나를 결정한다.

| Current API group | Tier A | Tier B | Classification rule |
|---|---:|---:|---|
| System | 4 | 1 | health/live/ready/status는 A, 안내 root는 B |
| Auth | 3 | 0 | login/current user/safe demo discovery는 A |
| Products | 5 | 0 | core quote 입력과 관리에 필요 |
| Competitors and references | 7 | 0 | pricing-check 근거에 필요 |
| Cost profiles | 5 | 0 | 결정론적 가격과 margin 근거에 필요 |
| Price tables core | 0 | 7 | 초기 Quote workflow에 직접 필요하지 않은 legacy artifact API |
| Quote calculations | 3 | 0 | preview/candidate/validation 계산은 A |
| Approval | 5 | 0 | approval/rejection 핵심 흐름 |
| Audit | 2 | 0 | actor와 evidence lineage |
| Customer quote requests | 7 | 0 | core workflow 시작점 |
| Dashboard and insights | 4 | 6 | summary/quote/approval/validation metrics는 A, 나머지는 B |
| Demo | 5 | 0 | production-disabled 안전한 demo support |
| Explanation | 1 | 0 | deterministic fallback과 이후 grounded AI adapter |
| HTML reports | 4 | 0 | 승인된 Quote의 report 계약 |
| CSV | 0 | 6 | operations 단계 전까지 V1 동결 |
| Price table history/comparison | 0 | 6 | non-core advanced comparison |
| Pricing simulations | 0 | 3 | advanced pricing feature |
| Scenario comparisons | 0 | 3 | advanced pricing feature |
| Strategy templates | 0 | 7 | advanced pricing feature |
| Workflow jobs | 0 | 5 | core journey에 필요하지 않은 operations abstraction |
| **Total application operations** | **55** | **44** | **99** |

Framework-provided OpenAPI/schema/docs 경로는 99개에 포함하지 않지만 production protection은 Tier A security contract다. **Rebuilding all 99 existing API operations to equal V2 product quality is not part of the initial V2 scope.**

### 9.2 System (Tier A 4, Tier B 1; 5 operations)

| Method/path | 목적 | Auth | Request -> Response | 주요 코드 | FE | Test | V2 결정/위험 |
|---|---|---|---|---|---|---|---|
| `GET /` | backend 안내 | P | - -> object | 200 | N | `test_backend_smoke.py` | Tier B; V2 core에 불필요 |
| `GET /api/health` | liveness-friendly health | P | - -> `HealthResponse` | 200 | Y | `test_health_status_hardening.py` | 그대로 유지 |
| `GET /api/health/live` | process liveness | P | - -> `HealthLiveResponse` | 200 | N | same | 그대로 유지 |
| `GET /api/health/ready` | DB/config readiness | P | - -> `HealthReadyResponse` | 200/503 | Y | same | 그대로 유지 |
| `GET /api/system/status` | secret-safe 진단 | P | - -> `SystemStatusResponse` | 200 | Y | `test_system_status_security.py` | Tier A; production admin-only, secret-safe response |

Framework contract: `GET /openapi.json`, `/docs`, `/redoc`는 현재 공개다. V2 production에서는 schema와 docs를 admin-only로 보호하거나 disabled로 배포한다. local/demo 정책은 환경별로 문서화한다.

### 9.3 Auth (Tier A; 3 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정/위험 |
|---|---|---|---|---|---|---|---|
| `POST /api/auth/login` | credential login | P | `LoginRequest` -> `LoginResponse` | 200/401/422 | Y | `test_auth_api.py` | bearer interface 유지, production seed 제거 |
| `GET /api/auth/me` | current user | U | - -> `UserResponse` | 200/401 | Y | same | 그대로 유지 |
| `GET /api/auth/demo-users` | demo credential hints | P | - -> `list[DemoUserResponse]` | 200 | Y | same | production에서 disabled/404; 명시적 demo 환경만 허용 |

### 9.4 Products (Tier A; 5 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정/위험 |
|---|---|---|---|---|---|---|---|
| `GET /api/products` | 상품 목록 | P | - -> `list[ProductResponse]` | 200 | Y | OpenAPI/간접 계산 테스트 | auth adapter 후 유지 |
| `POST /api/products` | 상품 생성 | P | `ProductCreate` -> `ProductResponse` | 201/422 | N | CSV/간접 | M 이상으로 변경 |
| `GET /api/products/{product_id}` | 상품 상세 | P | - -> `ProductResponse` | 200/404 | N | OpenAPI 중심 | V 이상으로 변경 |
| `PUT /api/products/{product_id}` | 상품 수정 | P | `ProductUpdate` -> `ProductResponse` | 200/404/422 | N | 직접 커버리지 약함 | M 이상, audit 필요 |
| `DELETE /api/products/{product_id}` | 상품 삭제 | P | - -> `ProductResponse` | 200/404 | N | 직접 커버리지 약함 | V2는 M 이상 soft-disable; referenced row hard delete 금지 |

### 9.5 Competitors and references (Tier A; 7 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정/위험 |
|---|---|---|---|---|---|---|---|
| `GET /api/competitors` | 경쟁사 목록 | P | - -> `list[CompetitorResponse]` | 200 | N | OpenAPI/CSV 간접 | V 이상 |
| `POST /api/competitors` | 경쟁사 생성 | P | `CompetitorCreate` -> `CompetitorResponse` | 201/422 | N | 직접 커버리지 약함 | M 이상, type enum 필요 |
| `GET /api/competitors/{competitor_id}` | 경쟁사 상세 | P | - -> `CompetitorResponse` | 200/404 | N | OpenAPI 중심 | V 이상 |
| `PUT /api/competitors/{competitor_id}` | 경쟁사 수정 | P | `CompetitorUpdate` -> `CompetitorResponse` | 200/404/422 | N | 직접 커버리지 약함 | M 이상, audit 필요 |
| `DELETE /api/competitors/{competitor_id}` | 경쟁사 삭제 | P | - -> `CompetitorResponse` | 200/404 | N | 직접 커버리지 약함 | soft-disable 권장 |
| `GET /api/competitor-prices` | 참고 가격 목록 | P | - -> `list[CompetitorPriceResponse]` | 200 | N | candidate/CSV 간접 | V 이상, pagination 필요 |
| `POST /api/competitor-prices` | 참고 가격 생성 | P | `CompetitorPriceCreate` -> `CompetitorPriceResponse` | 201/404/422 | N | candidate/CSV 간접 | M 이상, quantity/type 계약 재작성 |

### 9.6 Cost profiles (Tier A; 5 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정/위험 |
|---|---|---|---|---|---|---|---|
| `GET /api/cost-profiles` | 원가 목록 | P | - -> `list[CostProfileResponse]` | 200 | N | quote/candidate/CSV 간접 | manager/admin raw access; viewer에는 summary DTO만 제공 |
| `POST /api/cost-profiles` | 원가 생성 | P | `CostProfileCreate` -> `CostProfileResponse` | 201/404/422 | N | CSV/간접 | M 이상, active uniqueness |
| `GET /api/cost-profiles/{cost_profile_id}` | 원가 상세 | P | - -> `CostProfileResponse` | 200/404 | N | 간접 | manager/admin only; viewer raw component 금지 |
| `PUT /api/cost-profiles/{cost_profile_id}` | 원가 수정 | P | `CostProfileUpdate` -> `CostProfileResponse` | 200/404/422 | N | 간접 | M 이상, margin `<1` 통일 |
| `DELETE /api/cost-profiles/{cost_profile_id}` | 원가 삭제 | P | - -> `CostProfileResponse` | 200/404 | N | 간접 | soft-disable, M 이상 |

### 9.7 Price tables core (Tier B; 7 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정/위험 |
|---|---|---|---|---|---|---|---|
| `GET /api/price-tables` | 가격표 목록 | P | - -> `list[PriceTableResponse]` | 200 | Y | history/final regression | V 이상 |
| `POST /api/price-tables` | 가격표 생성 | P | `PriceTableCreate` -> `PriceTableResponse` | 201/422 | N | 직접 커버리지 약함 | M 이상, draft만 생성 |
| `GET /api/price-tables/{price_table_id}` | 가격표 상세 | P | - -> `PriceTableResponse` | 200/404 | N | OpenAPI/간접 | V 이상 |
| `PUT /api/price-tables/{price_table_id}` | 가격표/상태 수정 | P | `PriceTableUpdate` -> `PriceTableResponse` | 200/404/422 | N | 직접 커버리지 약함 | arbitrary active 금지, adapter 필요 |
| `DELETE /api/price-tables/{price_table_id}` | archived 처리 | P | - -> `PriceTableResponse` | 200/404 | N | 간접 | M 이상, endpoint semantics 문서화 |
| `GET /api/price-tables/{price_table_id}/items` | 항목 목록 | P | - -> `list[PriceTableItemResponse]` | 200/404 | N | OpenAPI/간접 | quantity tier 재작성 |
| `POST /api/price-tables/{price_table_id}/items` | 항목 생성 | P | `PriceTableItemCreate` -> `PriceTableItemResponse` | 201/404/422 | N | 간접 | M 이상, duplicate/quantity 제약 |

### 9.8 Quote calculations (Tier A; 3 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정/위험 |
|---|---|---|---|---|---|---|---|
| `POST /api/quote-preview` | 결정론적 견적 계산 | O | `QuotePreviewRequest` -> `QuotePreviewResponse` | 200/400/404/422 | Y | `test_quote_preview_api.py` | 계산 계약 선택 이관; V2에서는 authenticated V 이상 |
| `POST /api/candidate-prices` | 후보 가격 생성 | O | `CandidatePriceRequest` -> `CandidatePriceResponse` | 200/400/404/422 | Y | `test_candidate_prices_api.py` | 유지, Quote adapter 추가 |
| `POST /api/price-validation` | 후보 가격 검증 | O | `PriceValidationRequest` -> `PriceValidationResponse` | 200/400/404/422 | Y | `test_validation_engine_api.py` | core 유지, rule/result persistence 재작성 |

### 9.9 Approval (Tier A; 5 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정/위험 |
|---|---|---|---|---|---|---|---|
| `GET /api/approval-requests` | 승인 목록 | P | - -> `list[ApprovalRequestResponse]` | 200 | Y | `test_approval_workflow_api.py` | V 이상 |
| `POST /api/approval-requests` | 승인 요청 생성 | O | `ApprovalRequestCreate` -> `ApprovalRequestResponse` | 201/400/404/422 | Y | same | M 이상, quote/candidate linkage |
| `GET /api/approval-requests/{approval_request_id}` | 승인 상세 | P | - -> `ApprovalRequestResponse` | 200/404 | N | same | V 이상 |
| `POST /api/approval-requests/{approval_request_id}/approve` | 승인 | O | `ApprovalDecisionRequest` -> `ApprovalRequestResponse` | 200/400/404/422 | Y | same | M 이상, actor from token, 409 권장 |
| `POST /api/approval-requests/{approval_request_id}/reject` | 반려 | O | `ApprovalDecisionRequest` -> `ApprovalRequestResponse` | 200/400/404/422 | Y | same | M 이상, reason policy, 409 권장 |

### 9.10 Audit (Tier A; 2 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정/위험 |
|---|---|---|---|---|---|---|---|
| `GET /api/audit-logs` | filterable audit 목록 | M | query filters -> `list[AuditLogResponse]` | 200/401/403/422 | Y | `test_audit_logs_api.py` | 유지, pagination/cursor 후보 |
| `GET /api/audit-logs/{audit_log_id}` | audit 상세 | M | - -> `AuditLogResponse` | 200/404 | N | same | 유지, metadata structured response 후보 |

### 9.11 Customer quote requests (Tier A; 7 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정/위험 |
|---|---|---|---|---|---|---|---|
| `GET /api/customer-quote-requests` | 요청 목록 | V | - -> `list[CustomerQuoteRequestResponse]` | 200/401/403 | Y | `test_customer_quote_requests_api.py` | 유지 + pagination/filter |
| `POST /api/customer-quote-requests` | 요청 생성 | P | `CustomerQuoteRequestCreate` -> response | 201/400/404/422 | Y | same | V2에서는 authenticated manager/admin only; public intake 제외 |
| `GET /api/customer-quote-requests/{request_id}` | 요청 상세 | V | - -> response | 200/404 | N | same | 유지 |
| `PUT /api/customer-quote-requests/{request_id}` | 요청 수정 | M | `CustomerQuoteRequestUpdate` -> response | 200/400/404/422 | N | same | PATCH 후보, transition과 분리 |
| `POST /api/customer-quote-requests/{request_id}/status` | 상태 변경 | M | `CustomerQuoteRequestStatusUpdate` -> response | 200/400/404/422 | Y | same | strict transition + 409 |
| `POST /api/customer-quote-requests/{request_id}/quote-preview` | 요청 기반 transient preview | M | - -> `QuotePreviewResponse` | 200/400/404 | Y | same | compatibility adapter로 유지 |
| `POST /api/customer-quote-requests/{request_id}/candidate-prices` | 요청 기반 transient 후보 | M | optional `CustomerQuoteCandidatePriceRequest` -> response | 200/400/404/422 | Y | same | compatibility adapter; Quote flow로 이동 |

### 9.12 Dashboard and insights (Tier A 4, Tier B 6; 10 operations)

| Method/path | 목적 | Auth | Response | FE | Test | V2 결정 |
|---|---|---|---|---|---|---|
| `GET /api/dashboard/summary` | 통합 KPI | V | `DashboardResponse` | Y | `test_dashboard_api.py` | Tier A; Quote metrics adapter |
| `GET /api/dashboard/metrics` | summary alias 성격 | V | `DashboardResponse` | N | same | Tier B; V1 동결/deprecation 후보 |
| `GET /api/dashboard/quote-metrics` | request 지표 | V | `DashboardQuoteMetrics` | N | same | Tier A; Quote 지표로 재작성 |
| `GET /api/dashboard/approval-metrics` | 승인 지표 | V | `DashboardApprovalMetrics` | N | same | Tier A |
| `GET /api/dashboard/validation-metrics` | validation 지표 | V | `DashboardValidationMetrics` | N | same | Tier A; 새 snapshot 모델로 adapter |
| `GET /api/dashboard/pricing-metrics` | price table/cost 지표 | V | `DashboardPricingMetrics` | N | same | Tier B; V2-09 이후 재평가 |
| `GET /api/dashboard/workflow-metrics` | job 지표 | V | `DashboardWorkflowMetrics` | N | same | Tier B |
| `GET /api/dashboard/audit-metrics` | audit 지표 | V | `DashboardAuditMetrics` | N | same | Tier B; audit search와 별개 |
| `GET /api/dashboard/insights` | deterministic insight | V | `DashboardInsightsResponse` | Y | `test_dashboard_insights_api.py` | Tier B; V1 동결 |
| `GET /api/dashboard/insights/rules` | insight rule 목록 | V | `DashboardInsightRulesResponse` | N | same | Tier B; V1 동결 |

모든 dashboard operation의 주요 코드는 200/401/403이며 query validation이 있으면 422다.

### 9.13 Demo (Tier A safety scope; 5 operations)

| Method/path | 목적 | Auth | Response | 코드 | FE | Test | V2 결정 |
|---|---|---|---|---|---|---|---|
| `GET /api/demo/status` | demo 준비 상태 | V | `DemoStatusResponse` | 200/401/403 | Y | `test_demo_data_tools_api.py` | demo flag 강제 |
| `POST /api/demo/seed` | demo seed | A | `DemoSeedResponse` | 201/401/403 | Y | same | production 404/disabled |
| `POST /api/demo/reset` | known demo reset | A | `DemoResetResponse` | 200/401/403 | Y | `test_demo_reset_safety.py` | production 금지 |
| `POST /api/demo/scenario/full` | full demo 생성 | M | `DemoFullScenarioResponse` | 201/401/403 | Y | demo tests | 두 MVP 제품으로 재작성 |
| `GET /api/demo/guide` | demo 단계/credential hints | V | `DemoGuideResponse` | 200/401/403 | Y | demo tests | credential hint 환경 제한 |

### 9.14 Explanation (Tier A; 1 operation)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정 |
|---|---|---|---|---|---|---|---|
| `POST /api/explanations/quote` | stored/direct snapshot 설명 | O | `QuoteExplanationRequest` -> `QuoteExplanationResponse` | 200/400/404/422 | Y | `test_explanation_api.py` | deterministic fallback 유지; AI 과장 금지 |

### 9.15 HTML reports (Tier A; 4 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정 |
|---|---|---|---|---|---|---|---|
| `GET /api/html-reports` | report 목록 | V | - -> `list[HtmlReportResponse]` | 200/401/403 | Y | `test_html_reports_api.py` | 유지 + Quote source |
| `POST /api/html-reports` | report 생성 | M | `HtmlReportCreate` -> `HtmlReportResponse` | 201/400/404/422 | Y | same/security | adapter, approved Quote policy |
| `GET /api/html-reports/{report_id}` | metadata 상세 | V | - -> `HtmlReportResponse` | 200/404 | Y | same | 유지 |
| `GET /api/html-reports/{report_id}/content` | HTML content | V | - -> HTML Response | 200/404 | Y | same/security | V2 adapter는 strict CSP와 safe preview/download policy 필수 |

### 9.16 CSV (Tier B; 6 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정 |
|---|---|---|---|---|---|---|---|
| `POST /api/import/products` | product CSV import | M | multipart file -> `CsvImportSummary` | 200/401/403/422 | Y | `test_csv_import_export_api.py` | 유지 |
| `POST /api/import/cost-profiles` | cost CSV import | M | multipart -> summary | 200/401/403/422 | Y | same | 유지 + margin invariant |
| `POST /api/import/competitor-prices` | competitor price import | M | multipart -> summary | 200/401/403/422 | Y | same | schema version 필요 |
| `GET /api/export/products.csv` | product export | V | - -> CSV | 200/401/403 | Y | same | 유지 |
| `GET /api/export/cost-profiles.csv` | cost export | V | - -> CSV | 200/401/403 | Y | same | V2 viewer 금지; manager/admin only if reintroduced |
| `GET /api/export/competitor-prices.csv` | reference export | V | - -> CSV | 200/401/403 | Y | same | 유지 |

### 9.17 Price table history/comparison (Tier B; 6 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정 |
|---|---|---|---|---|---|---|---|
| `GET /api/price-tables/{price_table_id}/summary` | table summary | V | - -> `PriceTableSummaryResponse` | 200/404 | Y | `test_price_table_history_api.py` | adapter |
| `POST /api/price-tables/{price_table_id}/snapshots` | snapshot 생성 | M | `PriceTableSnapshotCreate` -> response | 201/404/422 | Y | same | 유지 |
| `GET /api/price-tables/{price_table_id}/snapshots` | snapshot 목록 | V | - -> list response | 200/404 | Y | same | 유지 |
| `GET /api/price-table-snapshots/{snapshot_id}` | snapshot 상세 | V | - -> response | 200/404 | N | same | 유지 |
| `POST /api/price-tables/compare` | live table 비교 | V | `PriceTableCompareRequest` -> `PriceTableComparisonResponse` | 200/404/422 | Y | same | 유지, 고급 가격 점검 |
| `POST /api/price-table-snapshots/compare` | snapshot 비교 | V | `PriceTableSnapshotCompareRequest` -> response | 200/404/422 | Y | same | 유지 |

### 9.18 Pricing simulations (Tier B; 3 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정 |
|---|---|---|---|---|---|---|---|
| `GET /api/pricing-simulations` | simulation 목록 | V | - -> `list[PricingSimulationResponse]` | 200 | Y | `test_pricing_simulation_api.py` | API 보존, 초기 UI 제외 |
| `POST /api/pricing-simulations` | simulation 생성 | M | `PricingSimulationCreate` -> response | 201/400/404/422 | Y | same | 후순위, Quote context 후보 |
| `GET /api/pricing-simulations/{simulation_id}` | simulation 상세 | V | - -> response | 200/404 | N | same | 유지 |

### 9.19 Scenario comparisons (Tier B; 3 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정 |
|---|---|---|---|---|---|---|---|
| `GET /api/scenario-comparisons` | comparison 목록 | V | - -> `list[ScenarioComparisonResponse]` | 200 | Y | `test_scenario_comparison_api.py` | API 보존, 초기 UI 제외 |
| `POST /api/scenario-comparisons` | comparison 생성 | M | `ScenarioComparisonCreate` -> response | 201/400/404/422 | Y | same | 후순위 |
| `GET /api/scenario-comparisons/{comparison_id}` | comparison 상세 | V | - -> response | 200/404 | Y | same | 유지 |

### 9.20 Strategy templates (Tier B; 7 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정 |
|---|---|---|---|---|---|---|---|
| `GET /api/strategy-templates` | template 목록 | V | - -> list response | 200 | Y | `test_strategy_templates_api.py` | API 보존, 초기 UI 제외 |
| `POST /api/strategy-templates` | template 생성 | M | `StrategyTemplateCreate` -> response | 201/400/422 | Y | same | 후순위 |
| `GET /api/strategy-templates/{template_id}` | template 상세 | V | - -> response | 200/404 | N | same | 유지 |
| `PUT /api/strategy-templates/{template_id}` | template 수정 | M | `StrategyTemplateUpdate` -> response | 200/400/404/422 | Y | same | 후순위 |
| `DELETE /api/strategy-templates/{template_id}` | soft disable | M | - -> response | 200/404 | Y | same | 유지 |
| `POST /api/strategy-templates/{template_id}/candidate-prices` | template 후보 계산 | V | `StrategyTemplateCandidatePriceRequest` -> `CandidatePriceResponse` | 200/400/404/422 | Y | same | M 권한 후보, risk semantics 필요 |
| `POST /api/strategy-templates/{template_id}/pricing-simulation` | template simulation | V | `StrategyTemplatePricingSimulationRequest` -> response | 200/400/404/422 | Y | same | M 권한 후보 |

### 9.21 Workflow jobs (Tier B; 5 operations)

| Method/path | 목적 | Auth | Request -> Response | 코드 | FE | Test | V2 결정 |
|---|---|---|---|---|---|---|---|
| `GET /api/workflow-jobs` | filtered job 목록 | V | query -> `list[WorkflowJobResponse]` | 200/422 | Y | `test_workflow_jobs_api.py` | 운영 후순위 |
| `POST /api/workflow-jobs` | job 생성 | M | `WorkflowJobCreate` -> response | 201/400/422 | Y | same | 초기 UI 제외 |
| `GET /api/workflow-jobs/{job_id}` | job 상세 | V | - -> response | 200/404 | N | same | 운영 only |
| `POST /api/workflow-jobs/{job_id}/run` | pending job 동기 실행 | M | - -> response | 200/400/404 | Y | same | background로 표현 금지 |
| `POST /api/workflow-jobs/{job_id}/cancel` | pending cancel | M | - -> response | 200/400/404 | Y | same | 유지 가능 |

## 10. Proposed V2 API Contract

### 10.1 Principles

1. V2 API는 별도 `quoteops-ai-v2` repository에서 설계한다. V1 router tree를 통째로 복사하거나 기존 앱에 `/api/v2`를 병렬 증축하지 않는다.
2. 모든 operation은 Tier A 또는 Tier B다. 초기 구현 backlog에는 Tier A만 들어가며 Tier B는 V1 frozen contract로 남는다.
3. 검증된 Tier A request/response와 golden numeric behavior는 경로를 유지할 수 있지만, 보안·Decimal·lineage 계약을 만족하도록 선택 이관한다.
4. 모든 write는 authenticated manager/admin만 가능하다. approval decision actor는 token identity에서만 결정한다.
5. viewer response는 summarized cost, resulting margin, risk, validation outcome만 포함하고 raw cost components/profile/CSV/configuration은 포함하지 않는다.
6. 계산 endpoint는 순수 결정론적 결과를 반환하고, Quote-scoped endpoint만 immutable snapshot과 lineage를 저장한다.
7. AI endpoint는 grounded text artifact만 만들며 monetary field, validation status, approval status, workflow status를 쓰는 schema를 갖지 않는다.
8. list endpoint는 처음부터 documented pagination/filter contract를 사용한다. V1 list shape 호환은 명시적으로 선택한 adapter에서만 책임진다.

### 10.2 Tier A — V2 Core Contract

| Capability | Proposed V2 contract | Source | Phase |
|---|---|---|---|
| Auth/current user/roles | login, current user, backend-enforced `admin/manager/viewer` dependencies | selected V1 behavior, new security implementation | V2-01/02 |
| Product/reference/cost inputs | authenticated product, competitor/reference, and cost management; viewer-safe summary DTO | selected V1 schemas and formulas, rewritten authorization | V2-01/05 |
| Customer request | authenticated create/list/detail/update/strict transition | selected V1 fields, rewritten state service | V2-03 |
| Persistent Quote | Quote, QuoteLine, immutable revisions, request lineage | new V2 domain | V2-04 |
| Deterministic pricing | quote preview, candidate calculation, validation | selectively migrated V1 services and golden numbers | V2-04/05 |
| Pricing evidence | candidate, pricing-check, validation snapshots with formula/source versions | new V2 persistence around verified calculations | V2-05 |
| Approval/rejection | Quote-scoped submit, separate reviewer identity, immutable decision | selected transition behavior, rewritten authorization/lineage | V2-06 |
| Reports | create/read approved-Quote reports and regeneration history | selected safe rendering behavior, new Quote source | V2-07 |
| Audit | sanitized append-only history for every mutation and decision | selected sanitization behavior, new actor/FK model | V2-01 onward |
| Core dashboard | request, Quote, approval, and validation summaries | rewritten core read models | V2-02 onward |
| Health/demo safety | public health/live/ready; protected status/docs; production-disabled demo support | selected V1 checks, rewritten guards | V2-01/09 |
| Grounded AI copilot | contextual explanation/draft endpoints with source metadata and deterministic fallback | new V2 integration; no numeric/state mutation | V2-08 |

Tier A contains the 55 classified current V1 operations where relevant plus the new persistent Quote, revision, snapshot, and grounded-copilot operations below. “Tier A” does not mean blind one-to-one porting: obsolete current operations may be replaced by a smaller coherent contract when the preserved behavior and migration evidence are documented.

### 10.3 Required new persistent Quote APIs

| Method/path | Purpose | Auth | Core request | Core response | Phase |
|---|---|---|---|---|---|
| `POST /api/customer-quote-requests/{request_id}/quotes` | convert request to persisted Quote | M | quote metadata + request version | `QuoteDetailResponse` | V2-04 |
| `GET /api/quotes` | paged Quote worklist | V | status/assignee/customer/page filters | `QuotePageResponse` | V2-04 |
| `GET /api/quotes/{quote_id}` | Quote and current revision detail | V | - | `QuoteDetailResponse` with role-safe costing | V2-04 |
| `PATCH /api/quotes/{quote_id}` | update draft metadata | M | allowed fields + optimistic version | updated `QuoteDetailResponse` | V2-04 |
| `PUT /api/quotes/{quote_id}/lines` | atomically replace ordered draft lines | M | complete line set + optimistic version | recalculated detail | V2-04 |
| `GET /api/quotes/{quote_id}/revisions` | list immutable revisions | V | page filters | `QuoteRevisionPageResponse` | V2-04 |
| `GET /api/quote-revisions/{revision_id}` | retrieve one reproducible revision | V | - | `QuoteRevisionDetailResponse` | V2-04 |
| `POST /api/quotes/{quote_id}/pricing-checks` | calculate and persist candidates/validation snapshot | M | quote version, strategy, competitor-context flag | `PricingCheckSnapshotResponse` | V2-05 |
| `GET /api/quotes/{quote_id}/pricing-checks` | list pricing evidence | V | page filters | role-safe snapshot page | V2-05 |
| `GET /api/pricing-checks/{pricing_check_id}` | retrieve immutable pricing evidence | V | - | role-safe snapshot detail | V2-05 |
| `POST /api/quotes/{quote_id}/approval-requests` | submit selected passing/warning snapshot | M | pricing-check ID, candidate ID, required reason when warning | `ApprovalRequestResponse` | V2-06 |

`QuoteLine` individual CRUD is not part of the initial contract. Atomic line replacement is the approved minimal API; adding granular endpoints requires evidence from V2-04 usability or concurrency tests.

### 10.4 Grounded AI copilot APIs (Tier A, introduced in V2-08)

| Method/path | Purpose | Auth | Mutation boundary | Response requirements |
|---|---|---|---|---|
| `POST /api/quotes/{quote_id}/copilot-outputs` | create candidate comparison, risk summary, approval-reason draft, rejection revision suggestions, or report-summary draft | M | creates text output/audit metadata only | `GroundedCopilotOutputResponse` |
| `GET /api/copilot-outputs/{output_id}` | retrieve a saved grounded output | V | read-only | role-safe grounded response |

The create request identifies `purpose`, `quote_revision_id`, and the applicable `candidate_id`, `pricing_check_id`, `approval_request_id`, or `report_id`. The response must include quote ID, quote revision, selected candidate where applicable, pricing-check snapshot, triggered rules, source-data timestamp, deterministic-fallback status, AI generation timestamp, source artifacts used, model/provider metadata when an LLM ran, and the generated text. The response has no writable numeric-price, validation-state, approval-state, report-state, or workflow-state fields. An LLM failure returns a deterministic grounded summary or an explicit unavailable result and never blocks the core workflow.

### 10.5 Tier A selective-migration rules

| Verified V1 asset | V2 treatment | Required evidence before reuse |
|---|---|---|
| quote preview/candidate/validation calculations | port service logic, not routers or UI | golden Decimal tests match approved values |
| approval transition behavior | retain terminal-state intent | actor binding, self-approval prohibition, 409 concurrency tests |
| audit sanitization | port allowlist/redaction behavior | secret and identity tests |
| selected HTML report rendering | port safe renderer only | approved Quote source, escaping/CSP tests |
| health/live/readiness | port observable behavior | public/sanitized response and failure tests |
| selected request/response shapes | retain only where they reduce migration risk | OpenAPI snapshot and security review |
| selected CSV parsing | defer to V2-09 operations scope | schema/version/permission tests |

V1 `App.jsx`, `activeSection`, source-text placement tests, public-write dependencies, optional approval authentication, startup demo seeding, and `create_all()` lifecycle are explicitly ineligible for migration.

### 10.6 Tier B — Legacy Frozen Contract

| Tier B area | Initial V2 disposition | Reconsideration point |
|---|---|---|
| legacy price-table CRUD/history/comparison | V1 only; no initial V2 UI | after core workflow evidence, V2-09 or later |
| CSV import/export | V1 only during core build | selected operations tools in V2-09 |
| strategy templates | frozen; no new features | separate product-value review after V2-10 |
| pricing simulations | frozen; no new features | separate product-value review after V2-10 |
| scenario comparisons | frozen; no new features | separate product-value review after V2-10 |
| workflow jobs | frozen; no core dependency | only if a verified asynchronous need exists |
| legacy dashboard metrics/insights | frozen; no main V2 UI | adapter only when a core role needs the data |

Tier B does not block V2 completion. A Tier B feature can be selectively reintroduced, supported by an isolated adapter, formally deprecated, or permanently excluded only after Tier A staging passes. No Tier B feature is copied merely because its V1 endpoint exists.

### 10.7 Final security contract

- Customer-request creation and every other business write require authenticated manager/admin. Initial V2 has no public intake endpoint.
- Product, competitor, cost, and pricing writes require manager/admin. Viewer is read-only.
- Viewer receives summarized total cost, resulting margin, risk, and validation outcome; raw cost components/profile/CSV/configuration are never returned.
- Approval create/approve/reject requires manager/admin, and reviewer identity comes only from the authenticated principal.
- Normal environments prohibit requester self-approval. Explicit demo mode may permit it only with a visible demo label and dedicated audit event.
- `failed/high` cannot be submitted and has no admin override. `warning/medium` requires a nonblank written reason. `passed/low` may proceed normally.
- `/api/health`, `/api/health/live`, and `/api/health/ready` are public and secret-safe. Detailed system status is admin-only in production.
- OpenAPI schema and documentation are admin-only or disabled in production. Local/demo policy is environment-specific and documented.
- Demo users, routes, and seed/reset are unavailable in production. Startup never seeds demo data in production.
- All state transitions and business mutations produce sanitized audit events with authenticated actor, entity, previous/new state, and request correlation ID.

### 10.8 Common error contract

V2는 다음 공통 오류 body를 구현한다.

```json
{
  "detail": "Human-readable summary",
  "code": "stable_machine_code",
  "field_errors": [],
  "request_id": "optional-correlation-id"
}
```

Selected V1 adapters keep `detail`; `code`, `field_errors`, and `request_id` are additive. State conflicts use 409, schema validation 422, authentication 401, authorization 403, and missing resources 404. Every Tier A endpoint contract-tests these semantics.

## 11. Domain and State Contracts

### 11.1 Entity contract

| 엔터티 | 현재 존재 | 현재 핵심 필드/관계 | V2 불변 조건 | 재사용 | migration 위험 |
|---|---|---|---|---|---|
| User | 예 | username, display_name, role, password_hash, active | role은 3종, secret 미노출 | adapter 재사용 | demo default users, custom token |
| Product | 예 | sku unique, name, category, active | V2 초기 제품은 A3 Flyer와 Product / Brand Sticker | schema 참고 후 새 V2 model | demo 5종과 기존 FK는 V2-10에서 별도 mapping |
| Cost Profile | 예 | product FK, 3 costs, target margin, active | active per product 1개, margin `<1`, Decimal | formula/field meaning 선택 이관 | Float 변환과 중복 active는 V2-10 migration gate |
| Competitor | 예 | name, channel, active | competitor type enum | 재작성 | channel 자유 문자열 |
| Competitor Price | 예 | competitor/product FK, reference_price, observed_at | quantity와 price basis 필수 | 재작성 | 기존 row에 quantity 없음 |
| Customer Request | 예 | customer, product, quantity, due date, status, assignee | strict transition, 1:N Quotes | field meaning 선택 이관, service 재작성 | 기존 quoted row의 Quote 없음 |
| Quote | **아니오 - 제안** | proposed: request FK, quote number, revision, status, currency, totals | immutable approved revision, totals reproducible | 신규 | 핵심 migration 없음; demo backfill 필요 |
| Quote Line | **아니오 - 제안** | proposed: quote FK, product, quantity, options snapshot, prices | quantity >0, ordered, Quote revision 소속 | 신규 | current Product options 자체 없음 |
| Price Candidate | **아니오 - transient만 존재** | response option: strategy, margin, prices, profit | input snapshot과 formula version 포함 | 신규 snapshot | 기존 approval로 일부 backfill 가능 |
| Price Validation Result | **아니오 - transient/snapshot만 존재** | checks, status, risk; approval에 flattened snapshot | candidate/Quote revision과 불변 연결 | 신규 snapshot | 기존 approval checks 상세 없음 |
| Approval Request | 예 | product, quantity, prices, validation, status, reviewer | Quote revision + candidate/check FK, authenticated actor, no normal self-approval | transition intent 선택 이관, model/service 재작성 | legacy rows need explicit V2-10 disposition |
| Price Table | 예 | name, status, items | Tier B frozen; core workflow가 자동 활성화하지 않음 | 초기 V2 이관 안 함 | later adapter needs quantity-tier redesign |
| Price Table Snapshot | 예 | table FK, copied items | Tier B frozen, snapshot immutable | 초기 V2 이관 안 함 | legacy item semantics |
| Pricing Simulation | 예 | product, cost, scenarios | Tier B frozen, 분석 전용 | 초기 V2 이관 안 함 | Float/constant unit cost |
| Scenario Comparison | 예 | product, summary JSON, items | Tier B frozen, 분석 전용 | 초기 V2 이관 안 함 | JSON text/versioning |
| HTML Report | 예 | type, source, HTML, summary, creator | approved Quote revision source, reproducible, read-only | safe rendering behavior 선택 이관 | generic string source, no status |
| Audit Log | 예 | actor, action, entity, metadata JSON | append-only, sanitized, authenticated actor/FK | sanitization behavior 선택 이관 | actor_user_id no FK, string metadata |
| Workflow Job | 예 | type, status, input/result JSON | Tier B frozen | 초기 V2 이관 안 함 | exception text와 pseudo-background 의미 |
| Demo Workspace | 아니오 | stable names/SKU로 demo row 식별 | separate non-production demo dataset; production seed 0 | legacy structure 제외 | workspace table is not needed for initial V2 |

### 11.2 Currency, precision, and rounding contract

| Concern | Final V2 decision |
|---|---|
| Currency | Initial V2 supports KRW only; every Quote and snapshot stores `currency="KRW"` |
| Runtime arithmetic | Python `Decimal` only, context precision 28; binary `float` is prohibited in deterministic services and saved DTO construction |
| Money storage | PostgreSQL-compatible `NUMERIC(18,2)`; SQLite tests use an exact Decimal adapter, not Float |
| Rate storage | Margin/discount/rate uses `NUMERIC(9,6)` and valid business ranges such as `0 <= margin_rate < 1` |
| Quantity storage | positive integer; no fractional MVP quantity |
| Rounding mode | `ROUND_HALF_UP` everywhere a quantization boundary is required |
| Intermediate calculation | no cent-level quantization during cost, unit-price, margin, or total formulas; calculations retain Decimal precision 28 |
| Saved snapshot boundary | every persisted monetary output is independently quantized to `Decimal("0.01")`; rate snapshots to `Decimal("0.000001")`; unrounded inputs and `formula_version` are also retained where reproduction requires them |
| API wire format | monetary and rate values are canonical decimal strings (`"3384.62"`, `"0.250000"`), never JSON binary floats; compatibility adapters may expose legacy numeric fields only under a documented adapter contract |
| Display | KRW money is rendered with thousands separators and two decimal places; rate display is percentage with two decimal places, while calculations use the stored canonical value |
| Reproduction | a snapshot records input IDs/versions, canonical Decimal inputs, formula version, rounding policy version, and output values; recomputation must match every saved value exactly |

Golden-number tests from V1 are source evidence, not permission to preserve Float. During V2-10 migration, any V1 Float-derived value is converted from its stored decimal text representation, compared against recomputation, and quarantined for review if it differs by more than `0.01` KRW.

### 11.3 Customer request state

Current:

- allowed strings: `new`, `reviewing`, `quoted`, `closed`, `cancelled`
- start: `new`
- service는 어느 상태에서 어느 상태로든 변경을 허용
- `reviewed_at`은 `reviewing`으로 변경할 때만 설정

Proposed V2:

```text
new -> reviewing -> quoted -> closed
  \         \          \
   -> cancelled <- ------
```

- actor: manager/admin
- `quoted`는 첫 persisted Quote 생성 성공 시 시스템이 설정
- terminal: `closed`, `cancelled`
- quoted 후 재견적은 request status가 아니라 Quote revision으로 표현
- invalid transition: 409

### 11.4 Quote state

Current: 영속 Quote가 없으므로 현재 상태 계약도 없다.

Proposed V2:

```text
draft -> pricing_review -> approval_pending -> approved
  ^          |                  |
  |          -> blocked         -> rejected -> new revision(draft)
  -> cancelled
```

- `draft`: metadata/lines 수정 가능
- `pricing_review`: candidate/check snapshot 생성 중 또는 선택 단계
- `blocked`: failed validation으로 승인 제출 불가
- `approval_pending`: 해당 revision 수정 불가
- `approved`: immutable, report 생성 가능
- `rejected`: immutable decision record; 수정은 새 revision
- `cancelled`: terminal

### 11.5 Pricing check state

Current result status: `passed`, `warning`, `failed`; risk: `low`, `medium`, `high`. 상태 전이는 없고 매 호출 새 transient 결과를 만든다.

Proposed Quote-level mapping:

| Validation result | Quote pricing status | 승인 제출 |
|---|---|---|
| passed | ready | 허용 |
| warning | needs_review | 허용, 사유 필수 |
| failed/high | blocked | 제출 불가; initial V2에는 admin override 없음 |

새 check를 실행하면 이전 result를 수정하지 않고 superseded snapshot으로 남긴다.

### 11.6 Approval state

Current:

```text
pending -> approved
pending -> rejected
```

Proposed:

```text
pending -> approved
pending -> rejected
pending -> cancelled
```

- actor: manager/admin
- same request는 1회만 terminal 전이
- optimistic concurrency/version check 사용
- requester self-approval은 normal/local/staging/production에서 403
- self-approval은 explicit demo mode에서만 허용할 수 있고 UI label과 `demo_self_approval_used` audit event가 필수
- approved/rejected/cancelled는 terminal

### 11.7 Report state

Current: 요청 성공 시 완성된 row가 생성되며 별도 status가 없다. 실패하면 row가 없다.

V2 초기 제안:

- 동기 HTML 생성을 유지한다.
- `ready`는 row 존재로 표현하고 불필요한 workflow state를 추가하지 않는다.
- 재생성은 새 row를 만들고 `source_quote_revision_id`를 유지한다.
- archive가 필요해질 때만 additive status를 도입한다.
- approved Quote가 아닌 source는 409.

### 11.8 Workflow job state (Tier B reference only)

Current and retained if used:

```text
pending -> running -> completed
                  -> failed
pending -> cancelled
```

- run/cancel은 manager 이상
- 현재 실행은 HTTP 요청 안에서 동기적으로 수행됨
- `running` 이외 상태 run, pending 이외 cancel은 현재 400; V2는 409 권장
- V2 초기 핵심 journey에는 포함하지 않음

## 12. Target Architecture

### 12.1 Current vs target

| 영역 | 현재 | V2 목표 | 전략 |
|---|---|---|---|
| Frontend shell | 3,168줄 `App.jsx`, state section routing | URL route + layout + feature modules | 완전 재작성 |
| API client | 340줄 단일 axios 함수 파일 | shared transport + feature API modules | 새 V2 code; legacy client 미복사 |
| Frontend state | App local state에 server/form/UI state 혼합 | server state와 form/UI state 분리 | 새 V2 code |
| Backend routers | 도메인별 V1 라우터, auth 불일치 | thin Tier A routers + uniform role dependencies | contract 참고 후 재작성 |
| Backend services | 결정론적 서비스 분리 | 검증 계산 service 선택 이관 + 새 Quote orchestration | service 단위 검증 후 port |
| Models/schemas | 단일 `models.py`/`schemas.py` | V2 domain modules | 새 schema, selected field semantics only |
| Database | SQLite default, PostgreSQL URL 지원, `create_all()` | PostgreSQL canonical + Alembic; SQLite smoke option | separate V2 DB |
| Money | Float | section 11.2의 KRW Decimal/Numeric contract | new V2 schema + verified ETL |
| Auth | custom HMAC bearer, demo seed, localStorage | backend roles, production-safe session/token handling, no prod seed | security-first rewrite |
| Audit | service와 다수 route에 구현 | 모든 Tier A mutation, structured safe metadata, actor FK | sanitization behavior만 선택 이관 |
| Demo | startup seed + route tools | explicit demo mode, two-product guided flow | 완전 재작성 |
| Deployment | V1 Render configuration | separate V1 and V2 staging/deployments; verified cutover only | V1 unchanged, V2 config 신규 |

V2 architecture work occurs only in the new `quoteops-ai-v2` repository. This V1 repository and its deployment remain frozen evidence except for critical V1 security containment. No V2 phase uses an in-place feature flag, the PR-48 frontend, or a shared production database as its rollback mechanism.

### 12.2 Frontend target

```text
frontend/src/
  app/
    App.jsx
    router.jsx
    providers.jsx
    layouts/
      PublicLayout.jsx
      WorkspaceLayout.jsx
  features/
    auth/
    dashboard/
    customer-requests/
    quotes/
    pricing-checks/
    approvals/
    reports/
    operations/
    demo/
  shared/
    api/
      http.js
    components/
    hooks/
    formatters/
    validation/
  styles/
```

확정 원칙:

- React/Vite/JavaScript/Axios 유지
- 실제 URL routing 도입은 정당화됨: 현재 8개 화면이 state-only라 bookmark, back/forward, deep link가 불가능함
- feature별 API와 UI state 분리
- 업무 화면은 list/detail 또는 editor/summary 구조
- 서버 오류를 무시하지 않고 화면별 error boundary/state 제공
- legacy JSX/CSS는 복사하지 않는다. V1 screenshot과 PR-48 IA는 behavior/reference evidence로만 사용한다.
- route permission은 UX 보조이며 backend authorization을 대체하지 않는다.
- viewer-safe DTO를 사용해 raw cost가 browser에 전달된 뒤 숨겨지는 구조를 금지한다.

Non-blocking implementation choices:

- URL router는 필수다. 구체 library는 V2-01 ADR로 기록한다.
- server-state/form library는 feature 요구와 bundle evidence로 V2-01 ADR에서 선택하며 Product Contract approval을 막지 않는다.
- JSX source 문자열 위치 검사는 V2 test strategy로 이관하지 않는다.

### 12.3 Backend target

```text
backend/
  main.py
  config.py
  db.py
  auth.py
  models/
    users.py
    catalog.py
    requests.py
    quotes.py
    pricing.py
    approvals.py
    reports.py
    audit.py
  schemas/
    ...same domain boundaries...
  routers/
    ...thin HTTP adapters...
  services/
    quote_preview_service.py
    candidate_price_service.py
    validation_service.py
    quote_workflow_service.py
    approval_service.py
    report_service.py
    copilot_service.py
  agents/
    grounded_pricing_copilot.py
  migrations/
```

라우터는 auth, schema, status mapping만 담당한다. 계산과 상태 전이는 services에 둔다. AI orchestration은 `agents/`에 두고 deterministic service output만 읽는다. repository 계층은 SQLAlchemy query 중복이 실제로 문제가 될 때만 추가한다. 각 Tier A module은 V1 code copy가 아니라 verified behavior와 tests를 입력으로 새 repository에서 작성한다.

### 12.4 Database and migration

- PostgreSQL is the canonical V2 staging/production database.
- Alembic revision is the only V2 schema deployment path; application startup never calls `create_all()` in staging/production.
- SQLite may support fast local smoke tests, but PostgreSQL integration is a release gate.
- Money/currency follow section 11.2 exactly; every financial response includes `currency="KRW"`.
- Timestamps are timezone-aware UTC and API serialization is ISO 8601 with `Z`.
- unique/check/FK constraints and approval concurrency protection exist in the database as well as services.
- V2 begins with a clean schema. V1 rows are not silently accepted through nullable legacy columns.
- V2-10 uses read-only V1 export -> versioned transform -> validation report -> V2 import. Rejected rows are quarantined without modifying V1.
- V1 and V2 use separate databases and credentials through staging verification and rollback window.

### 12.5 Observability and operations

- health/live/ready remain public and secret-safe
- detailed system status is admin-only in production; OpenAPI is admin-only or disabled
- request correlation ID is required from V2-01 and is returned in common errors/audit metadata
- raw exception, token, password, DB URL은 API/audit/UI에 금지
- audit covers every Tier A mutation and decision; legacy workflow jobs remain Tier B
- production monitoring vendor는 V2 초기 범위 제외

## 13. Test Strategy

V2 tests live in `quoteops-ai-v2` and prove the new contracts. The V1 suite remains frozen in the V1 repository and is run only when extracting or comparing a selectively migrated behavior. Passing V1 tests is useful source evidence but never substitutes for V2 security, Decimal, persistence, or workflow tests.

| Layer | Required coverage | Primary execution | Release gate |
|---|---|---|---|
| Domain unit | pricing formulas, Decimal rounding, margin invariants, validation severity, quote revisions, approval transitions, report snapshot consistency | pytest on every backend change | every invariant and golden boundary case passes |
| API contract | every Tier A request/response, auth, role matrix, 401/403/409/422, additive error fields, OpenAPI policy | pytest + TestClient + schema snapshot | all implemented Tier A operations pass; Tier B absence is not failure |
| Database integration | Alembic, PostgreSQL compatibility, Numeric precision, FK/unique/check, rollback, concurrent approval | PostgreSQL CI service on schema/workflow changes | clean upgrade, previous-revision upgrade, downgrade/forward recovery, transaction tests pass |
| Frontend component | screen contracts, permissions, loading/empty/failure, forms, actions, route navigation | Vitest + React Testing Library | feature interaction tests pass with role-safe API fixtures |
| Core workflow | complete request-to-report lineage and rejection revision | Playwright against isolated V2 stack | required workflow cases pass on desktop and mobile |
| Security | anonymous/viewer mutation rejection, self-approval, demo production guards, OpenAPI/status, secret sanitization | pytest + HTTP smoke | zero unauthorized mutation and zero exposed secret/demo credential |
| AI copilot | grounding, fallback, no numeric/state mutation, source fidelity, LLM failure isolation | deterministic provider fixtures + contract tests | all prompts/outputs remain artifact-grounded; core passes with provider disabled |
| Deployment smoke | health/live/ready, login, protected endpoints, frontend/backend, CORS, credentials | staging HTTP/browser suite | V2 staging passes with production-like flags |
| Manual visual QA | desktop/tablet/mobile, navigation, overflow, loading/empty/error, roles, guided demo, complete workflow | recorded browser checklist/screenshots | milestone sign-off before V2-10 release |

### 13.1 Domain unit tests

- Pricing formula tests use `Decimal` inputs and assert exact canonical strings, including half-way `ROUND_HALF_UP` cases.
- Margin tests cover zero, minimum boundary, warning boundary, failed/high, and invalid `>=1` rates.
- Validation tests prove deterministic severity and that AI availability cannot alter results.
- Quote tests prove immutable approved revisions, new revision after rejection, optimistic version conflicts, and exact totals.
- Approval tests prove legal transitions, one terminal decision, authenticated reviewer, normal self-approval prohibition, and warning reason requirement.
- Report tests prove source revision consistency, regeneration lineage, escaping, and unchanged snapshot numbers.

### 13.2 API contract and authorization tests

- Every Tier A mutation is parameterized for anonymous, viewer, manager, and admin.
- Anonymous and viewer writes return 401 and 403 respectively without side effects or audit records that imply success.
- State/version conflicts return 409; invalid schemas return 422; additive error fields have stable types.
- Viewer Quote/pricing/report DTOs include summarized total cost, margin, risk, and validation outcome but exclude raw cost components/profile/CSV/configuration.
- Current V1 endpoint count is not a V2 completion assertion. V2 OpenAPI is checked against the explicit Tier A inventory only.
- Production-mode tests require admin for detailed status and require OpenAPI/schema to be protected or disabled.

### 13.3 Database integration tests

- Migrate an empty PostgreSQL database from base to head.
- Upgrade from every supported V2 release revision, then exercise downgrade/forward recovery where the revision is reversible.
- Assert `NUMERIC(18,2)` money and `NUMERIC(9,6)` rate round trips exactly.
- Assert active-cost uniqueness, Quote/request/revision FKs, immutable evidence constraints, and transaction rollback.
- Race two approval decisions and prove exactly one commits while the other receives 409.
- Test V1 export transformation with accepted and quarantined rows without connecting V2 tests to the V1 production database.

### 13.4 Frontend component tests

- Test rendered behavior through accessible roles, labels, routes, user actions, and mocked Tier A responses.
- Cover loading, empty, validation, authorization, network failure, conflict refresh, and successful states for every core screen.
- Prove viewer CTA absence together with 403 handling; frontend hiding is not treated as authorization evidence.
- Tests must not depend primarily on whether visible strings occur at a particular position inside JSX source files.

### 13.5 Required core workflow tests

1. Create an authenticated customer request.
2. Convert it into a persisted Quote.
3. Add and save Quote lines and create a reproducible revision.
4. Generate deterministic candidates without an LLM.
5. Create and retrieve a pricing-check/validation snapshot.
6. Submit a passed result or warning with written reason for approval; prove failed/high is blocked.
7. Approve with a different authorized actor or reject and create a new revision.
8. Generate and retrieve a report only from an approved revision.
9. Verify end-to-end IDs, actors, source versions, numeric snapshots, and audit lineage.
10. Verify no workflow action automatically activates a price table or sends a customer price.

### 13.6 Security tests

- Reject every anonymous business write and every viewer write.
- Enforce manager/admin permissions in the backend, independent of frontend navigation.
- Reject normal self-approval; explicit demo self-approval requires environment gate, label metadata, and audit event.
- Prove production startup creates zero demo users/data and all seed/reset/credential-hint routes are unavailable.
- Protect OpenAPI and detailed system status in production while keeping health/live/ready public and sanitized.
- Scan API bodies, logs, reports, and audit metadata for tokens, password hashes, DB URLs, API keys, raw exceptions, and private keys.

### 13.7 AI copilot tests

- Every output records grounding IDs, source artifacts/timestamps, triggered rules, fallback status, generation timestamp, and provider metadata where applicable.
- Snapshot numeric fields before/after generation and prove byte-for-byte canonical equality.
- Prove AI endpoints cannot mutate validation, approval, Quote, report, workflow, or price-table state.
- Reject or flag provider output containing unsupported facts; saved text references only supplied artifacts.
- Force timeout, malformed response, provider error, and disabled-provider modes; deterministic core workflow and reports still pass.

### 13.8 Deployment smoke and manual visual QA

- Automated smoke covers public health/live/ready, authenticated login/current user, protected Tier A reads/writes, frontend-to-backend connection, allowed CORS origin, and absence of exposed credentials.
- Manual QA records desktop, tablet, and mobile evidence for navigation, overflow, loading, empty/failure states, role-specific screens, guided demo, and the complete workflow.

### 13.9 Evidence migration rules

- Keep V1 tests and release/tag evidence in V1; do not copy the 410-test suite wholesale into V2.
- For each selectively migrated service, record V1 source commit, source tests, approved invariants, V2 module, and V2 replacement tests.
- Port golden numeric expectations as Decimal fixtures and explain any intentional contract change.
- Use an isolated database per test; never depend on repository-root `quoteops.db` or live V1 data.
- Do not migrate `App.jsx`, `activeSection`, or JSX source-placement tests.
- Treat warnings as debt with a CI budget; new deprecations introduced by V2 fail the relevant gate.

## V2-01 Entry Gate

V2-01 may begin only after every row below is confirmed. This gate approves starting foundation work in a new repository; it does not start V2-01 in this task.

| Entry condition | Status | Contract evidence |
|---|---|---|
| Stable baseline branch/tag identified | Confirmed | `origin/main` is the stable functional baseline; `v0.1.0` is a historical release marker |
| Stable baseline commit recorded | Confirmed | `08362d5d086d5deb7f37fe3be46c5cbf1b08575c` |
| PR-48 classified as reference only | Confirmed | `pr-48-cpq-workflow-app-shell-restructure` at `7bda36360c5cb7196ee8bc0c8ad06f4f24f3e277` |
| Clean V2 repository strategy approved | Confirmed | new `quoteops-ai-v2`; V1 frozen as evidence |
| Tier A scope finalized | Confirmed | sections 4, 9, and 10; current-operation reference count 55 plus required new V2 operations |
| Tier B frozen scope finalized | Confirmed | sections 4, 9, and 10; 44 current operations, not a core completion gate |
| Roles and permissions finalized | Confirmed | admin/manager writes, viewer safe reads, backend enforcement |
| V1 classified as demo-only | Confirmed | not production-secure or production-ready; no real business data |
| V2 public-write APIs prohibited | Confirmed | no anonymous business-data mutation; internal intake is manager/admin only |
| Production demo seeding prohibited | Confirmed | zero production demo users/data and no startup seed |
| KRW Decimal/Numeric policy finalized | Confirmed | section 11.2 |
| AI responsibility boundary finalized | Confirmed | grounded text only, no numeric/state mutation, core independent of LLM |
| Core acceptance journey finalized | Confirmed | Request -> Quote -> Pricing Check -> Approval/Reject -> Report and section 13.5 |
| No blocking user decisions remain | Confirmed | section 15 lists none |
| Security baseline is measurable | Confirmed | thresholds below |

V2-01 security baseline measurements:

- anonymous business mutation operations permitted: **0**
- optional-authentication approval mutation operations: **0**
- production startup-created demo users or business rows: **0**
- production-accessible demo seed/reset/credential-hint operations: **0**
- normal-environment self-approval attempts accepted: **0**; expected 403
- failed/high approval submissions accepted: **0**; expected 409
- warning/medium submissions without written reason accepted: **0**; expected 422
- viewer responses exposing raw cost components/profile/CSV/configuration: **0**
- unauthenticated production detailed-status/OpenAPI access accepted: **0**; expected 401/403 or disabled 404
- Tier A state-changing operations without sanitized audit actor metadata: **0**
- staging/production schema changes outside Alembic: **0**
- committed or response-exposed secrets: **0**

**Entry result:** all contract prerequisites are confirmed, so V2-01 is eligible to begin only after this V2-00 document is accepted. If any row changes to unresolved, V2-01 must not begin until the contract is revised.

## 14. Migration Plan

Each phase executes in `quoteops-ai-v2` unless explicitly described as V1 read-only evidence work. V1 and its deployment remain independently recoverable throughout.

### V2-00 — Product Contract

- **Goal:** finalize product scope, baselines, repository strategy, security gates, AI boundary, API tiers, and implementation entry conditions.
- **Inputs:** stable `origin/main`, historical `v0.1.0`, PR-48 reference, OpenAPI inventory, models/services/tests, deployment files, and the CPQ research PDF.
- **Outputs:** this approved V2-00.1 contract and measurable V2-01 Entry Gate.
- **V1 assets selectively reused:** none; all repository assets are read-only evidence.
- **New V2 components:** none.
- **V1 intentionally unchanged:** application, tests, config, database, deployment, branches, and release state.
- **Security gate:** prominent V1 demo-only classification and explicit prohibition on inheriting public writes/optional approval auth.
- **Test gate:** repository facts and counts are reproducible from recorded commands/evidence; document consistency audit passes.
- **Rollback:** revert only this documentation file; no runtime rollback exists because implementation did not begin.
- **Measurable completion:** stable commit recorded, 99 current operations classified 55 A/44 B, 32 feature decisions classified, no blocking decisions, exactly one final verdict.

### V2-01 — V2 Repository Foundation and Security Baseline

- **Goal:** create clean `quoteops-ai-v2` with secure frontend/backend boundaries, migration infrastructure, and exact financial primitives before business screens.
- **Inputs:** approved V2-00, Tier A inventory, role matrix, Decimal policy, selected V1 service evidence.
- **Outputs:** new repository, CI, modular FastAPI/React skeleton, auth/roles, Alembic, PostgreSQL tests, common errors, environment policy, protected diagnostics.
- **V1 assets selectively reused:** dependency choices, health/readiness behavior, audit sanitization rules, selected CI ideas; no source tree wholesale copy.
- **New V2 components:** repository structure, auth/session implementation, role dependencies, V2 schema base, migration runner, correlation IDs, test harness.
- **V1 intentionally unchanged:** V1 repository/deployment/database and all product behavior.
- **Security gate:** 0 anonymous business writes, 0 optional approval mutations, 0 production demo seeds, protected status/docs, 0 raw cost leaks to viewer, 0 secrets.
- **Test gate:** backend compile/lint as configured, frontend build, role matrix, common errors, migration up/down/forward recovery, PostgreSQL Decimal round trip, production-mode guards.
- **Rollback:** delete/disable only V2 staging resources and restore the prior V2 schema snapshot; V1 remains the serving fallback without code rollback.
- **Measurable completion:** every Entry Gate threshold is executable and green; Alembic owns 100% of V2 schema changes; no full business screen is present.

### V2-02 — Public Landing, Authentication, and App Shell

- **Goal:** deliver public landing, login, safe demo entry, routed authenticated shell, permission-aware navigation, and dashboard shell.
- **Inputs:** V2-01 auth/API client foundation, screen contracts, PR-48 as IA/problem reference only.
- **Outputs:** route layouts, login/logout/session recovery, dashboard shell, role navigation, protected-route UX.
- **V1 assets selectively reused:** product positioning copy and verified login/current-user response concepts; no legacy JSX/CSS/component code.
- **New V2 components:** public/workspace layouts, URL router, auth provider, feature navigation, core dashboard read model shell.
- **V1 intentionally unchanged:** `App.jsx`, `activeSection`, V1 routes, and V1 deployment.
- **Security gate:** unauthorized workspace routes redirect safely; hidden navigation never substitutes for API authorization; production demo entry reveals no credentials.
- **Test gate:** component interactions, deep links, refresh/back-forward, session expiry, role navigation, desktop/mobile Playwright login, frontend build.
- **Rollback:** undeploy V2 frontend build or route traffic to previous V2 artifact; V1 URL remains separate.
- **Measurable completion:** every contracted screen has a stable URL, all three roles see the correct navigation, and normal screens expose no diagnostics/credentials.

### V2-03 — Customer Request Workflow

- **Goal:** implement authenticated intake, request list/detail, strict transitions, audit actor, and Quote-conversion readiness.
- **Inputs:** V2-01 identity/data foundation, V2-02 shell, customer-request state contract.
- **Outputs:** request schema/model/migration/service/API/UI, pagination/filtering, transition/audit evidence.
- **V1 assets selectively reused:** field semantics and selected validation/error behavior after source-commit review.
- **New V2 components:** strict transition service, manager/admin intake, request pages, actor-linked audit events.
- **V1 intentionally unchanged:** public V1 request route, V1 data, pricing services, and deployment.
- **Security gate:** internal create/update/transition is manager/admin only; viewer is read-only; no public V2 intake endpoint exists.
- **Test gate:** role matrix, 409 invalid transitions, 422 fields, audit identity, DB constraints, browser create/review/cancel path.
- **Rollback:** roll back only the V2 migration/release artifact or disable V2 request routes; V1 data is never modified.
- **Measurable completion:** a manager creates, reviews, and prepares a request for conversion with every transition and actor queryable after refresh.

### V2-04 — Persistent Quote and Quote Line Domain

- **Goal:** create persistent Quote, QuoteLine, revisions, request lineage, deterministic totals, and Quote Workspace.
- **Inputs:** convertible V2 request, product/cost inputs, section 11 state/numeric contracts, V1 quote-preview evidence.
- **Outputs:** Quote migrations/models/services/Tier A APIs, list/editor/detail UI, immutable revision snapshots.
- **V1 assets selectively reused:** verified quote-preview formulas, golden values, and proven error cases after Decimal port review.
- **New V2 components:** Quote/Line/Revision domains, optimistic versioning, atomic line replacement, role-safe DTOs.
- **V1 intentionally unchanged:** V1 quote preview endpoint/data and all approval/report behavior.
- **Security gate:** manager/admin mutate drafts; viewer receives safe summaries only; approved/pending revisions reject edits; all mutations audited.
- **Test gate:** exact Decimal totals, line constraints, revision immutability, transaction rollback, optimistic conflicts, request-to-Quote E2E.
- **Rollback:** downgrade/forward-recover V2 Quote migrations and deploy prior V2 artifact; V1 remains independent.
- **Measurable completion:** refresh reproduces IDs, lines, totals, currency, formula version, and revision exactly; V1 golden cases match approved V2 Decimal expectations.

### V2-05 — Pricing Check and Deterministic Decision Workspace

- **Goal:** persist candidates, validation, competitor context, and decision evidence against one Quote revision.
- **Inputs:** immutable Quote revision, active cost profile, competitor references, verified candidate/validation services.
- **Outputs:** candidate/pricing-check/validation snapshot models and APIs, Pricing Check Workspace, approval-readiness result.
- **V1 assets selectively reused:** candidate formulas, validation rules, competitor weighting where covered by repository tests, golden notes only as behavior reference.
- **New V2 components:** Decimal service ports, formula/source versions, immutable evidence snapshots, role-safe pricing DTOs.
- **V1 intentionally unchanged:** V1 pricing APIs, price tables, simulations, scenarios, templates, and production data.
- **Security gate:** no AI numeric input, no automatic activation, `failed/high` submit path absent, viewer raw cost hidden, every calculation source recorded.
- **Test gate:** formula/rule boundaries, competitor context, snapshot reproduction, warning reason readiness, failed/high block, LLM-disabled E2E.
- **Rollback:** deploy prior V2 service and retain snapshots as read-only evidence or restore V2 DB snapshot; never fall through to AI-generated numbers.
- **Measurable completion:** every displayed candidate and rule can be exactly recomputed from stored Decimal inputs/version; readiness is deterministic.

### V2-06 — Approval Inbox and Audit Lineage

- **Goal:** implement Quote-scoped approval request, authenticated reviewer, self-approval policy, approve/reject transitions, immutable evidence, and inbox UI.
- **Inputs:** selected eligible V2 pricing-check/candidate snapshot and requester identity.
- **Outputs:** approval migration/model/service/APIs, inbox/detail/timeline, terminal decision audit.
- **V1 assets selectively reused:** pending-to-terminal behavior and sanitization patterns; not optional authentication or client-supplied reviewer identity.
- **New V2 components:** Quote/revision/check linkage, separate requester/reviewer FKs, concurrency token, warning reason, demo self-approval audit.
- **V1 intentionally unchanged:** V1 approval rows/routes and price-table state.
- **Security gate:** M/A only, normal self-approval 403, failed/high 409, warning without reason 422, reviewer from auth context, no automatic price-table activation.
- **Test gate:** role/state matrix, two-reviewer race, immutable decision, reject/new-revision path, audit lineage, approve/reject E2E.
- **Rollback:** deploy prior V2 artifact; preserve committed decisions as immutable and disable new submissions rather than rewriting history; V1 unaffected.
- **Measurable completion:** every terminal decision identifies request, Quote revision, check, candidate, requester, reviewer, reason, timestamp, version, and audit event.

### V2-07 — Report Center

- **Goal:** generate, preview, retrieve, and regenerate a report from an approved Quote revision with complete grounding metadata.
- **Inputs:** approved V2 Quote revision and decision evidence.
- **Outputs:** report model/service/Tier A APIs, Report Center list/preview/history, safe HTML artifact.
- **V1 assets selectively reused:** verified escaping/rendering/storage behavior and relevant security tests; generic source strings are not reused.
- **New V2 components:** approved-source FK, regeneration lineage, canonical snapshot renderer, role-safe report DTO.
- **V1 intentionally unchanged:** V1 report rows/types and deployment; PDF/email/signature/payment remain out of scope.
- **Security gate:** approved source only, escaped content/CSP, no raw secret/cost component for viewer, no executable untrusted content.
- **Test gate:** source status, numeric equality, snapshot consistency, escaping/CSP, role matrix, browser preview/regeneration.
- **Rollback:** disable V2 report generation and serve existing immutable V2 reports read-only; V1 reports remain separate.
- **Measurable completion:** report values exactly match the approved revision and every regenerated artifact identifies source revision and predecessor.

### V2-08 — Grounded AI Pricing Copilot

- **Goal:** add contextual candidate explanations, validation summaries, approval-reason drafts, rejection revision suggestions, and grounded report summaries without numeric/state authority.
- **Inputs:** immutable V2 Quote, candidate, pricing-check, validation, approval, and report artifacts plus deterministic fallback templates.
- **Outputs:** grounded copilot service/agent, Tier A output APIs, contextual UI panels, output/audit metadata.
- **V1 assets selectively reused:** deterministic explanation fallback concepts only after source-fact review; no claim that current template output is external AI.
- **New V2 components:** provider abstraction, grounding pack, source citation metadata, prompt/output guard, deterministic fallback, copilot audit store.
- **V1 intentionally unchanged:** every V1 AI/explanation path, all numeric formulas, approval/report/workflow states.
- **Security gate:** least-data prompts, no secrets/raw viewer-restricted cost, no numeric or state mutation capability, provider-disabled mode, output source validation.
- **Test gate:** all section 13.7 tests, malicious/unsupported output fixtures, timeout/failure, exact before/after snapshots, core E2E with LLM disabled.
- **Rollback:** disable provider and copilot routes/panels while deterministic fallback and entire core workflow remain available; no data rollback required for numeric/state records.
- **Measurable completion:** 100% saved outputs carry required grounding metadata, 0 numeric/state diffs, and all five contextual use cases pass with provider success and failure fixtures.

### V2-09 — Operations, Demo, and Selected Legacy Adapters

- **Goal:** add a restrained operations console, selected CSV tools, audit search, safe diagnostics, guided two-product demo, and only justified legacy adapters.
- **Inputs:** verified Tier A core, security policy, V1 CSV/health/audit evidence, explicit adapter value cases.
- **Outputs:** operations UI/APIs, production-safe demo mode, selected CSV functions, adapter/deprecation records.
- **V1 assets selectively reused:** chosen CSV parser behavior, health/readiness checks, audit filters, security QA scripts; Tier B only with written justification.
- **New V2 components:** environment-gated demo fixture/reset, operations role boundary, versioned import schema, adapter isolation layer.
- **V1 intentionally unchanged:** V1 Tier B endpoints/data and deployment; strategy/simulation/scenario/job UIs are not copied.
- **Security gate:** production demo users/data/routes 0, admin-only destructive operations, safe diagnostics, import size/schema controls, viewer raw cost CSV denied.
- **Test gate:** demo-disabled production suite, reset isolation, CSV authorization/rollback, diagnostics sanitization, audit search, adapter-specific contract tests.
- **Rollback:** disable individual operations/demo/adapter flags in V2 and deploy prior artifact; no V1 branch or data change.
- **Measurable completion:** guided demo completes core journey for exactly two MVP products, production exposes no demo credential/tool, and every adapter has owner/evidence/disposition.

### V2-10 — Staging Verification, Migration, and Portfolio Release

- **Goal:** verify complete workflow/security/data/rollback, compare V1/V2, deploy V2 staging, publish portfolio release, and make an explicit cutover decision.
- **Inputs:** completed V2-01 through V2-09, read-only V1 export, migration mapping, separate V1/V2 staging, rollback runbook.
- **Outputs:** migration/parity/security reports, staging evidence, release artifact, rollback rehearsal, cutover approval or rejection.
- **V1 assets selectively reused:** versioned read-only exports, golden expectations, final regression/security scripts after V2 adaptation.
- **New V2 components:** ETL tool/report, quarantine output, release smoke suite, staging configuration, cutover/rollback runbooks.
- **V1 intentionally unchanged:** V1 repository/branch/deployment/database remain available and are never merged into or overwritten by V2.
- **Security gate:** complete security suite and secret scan green, production-like flags, separate credentials/databases, no public writes/demo seed/status/docs exposure.
- **Test gate:** all Tier A, PostgreSQL, core E2E, AI-disabled/enabled, deployment smoke, manual visual QA, migration dry-run, and rollback rehearsal pass.
- **Rollback:** keep V1 serving path and immutable pre-cutover backups; route back to V1 and restore only V2 DB from verified snapshot without reverse-writing V1.
- **Measurable completion:** 100% Tier A DoD passes, 0 unexplained migrated-row loss, all quarantines reviewed, full core journey passes staging, rollback recovery objective is demonstrated, and cutover is separately approved.

## 15. Risks, Assumptions, and Final Decisions

### 15.1 Confirmed facts

- stable functional baseline은 `origin/main` commit `08362d5d086d5deb7f37fe3be46c5cbf1b08575c`이며 GitHub Actions `backend-checks`가 성공했다.
- `v0.1.0`은 commit `8387c5a1445615055c94fc50278b3ffb66f0f412`의 historical release marker이며 stable main의 ancestor다.
- 현재 working branch는 `pr-48-cpq-workflow-app-shell-restructure`; commit `7bda36360c5cb7196ee8bc0c8ad06f4f24f3e277`은 `origin/main`보다 한 commit 앞선 PR-48 reference다.
- PR-48과 stable main 사이 backend, requirements, deployment, and CI behavior에는 diff가 없고 PR-48 diff는 frontend/research/test-reference 범위다.
- current OpenAPI는 99 application operations/74 paths이며 framework docs/schema paths는 별도다.
- current branch tests 410개는 격리 임시 DB에서 통과했다; stable main에는 별도의 successful GitHub Actions evidence가 있다.
- persisted Quote/QuoteLine/Candidate/ValidationResult는 없다.
- 상품/경쟁사/원가/가격표 write와 approval decisions 일부는 인증 없이 가능하다.
- app startup은 environment와 무관하게 demo seed를 호출한다.
- `QUOTEOPS_DEMO_TOOLS_ENABLED`는 demo route를 차단하지 않는다.
- current backend는 external OpenAI API를 호출하지 않는다.
- price table item에는 quantity가 없다.
- competitor reference에는 quantity가 없고 competitor channel은 weighting에 사용되지 않는다.
- 현재 프런트엔드는 3,168줄 App와 state-only navigation을 사용한다.

### 15.2 Design decisions in this contract

- V2 is a lightweight pricing operations SaaS and pricing operations copilot.
- V1 is frozen evidence; V2 is built in the separate clean `quoteops-ai-v2` repository.
- Only verified Tier A behavior is selectively migrated; Tier B remains frozen and does not block completion.
- 영속 Quote/Line/revisions, pricing/validation snapshots, approval lineage, and grounded copilot outputs are core V2 domains.
- 자동 가격표 활성화는 V2에서도 금지한다.
- 시뮬레이션/시나리오/전략/워크플로 job/legacy insights are Tier B and excluded from the core V2 UI.
- React/Vite/JavaScript, FastAPI, PostgreSQL 방향을 유지한다.
- All saved financial values follow the KRW Decimal/Numeric contract in section 11.2.
- The grounded AI copilot is committed V2-08 scope, but the complete core workflow works with no external LLM.
- Browser E2E, PostgreSQL integration, API security contracts, and AI non-mutation tests are release gates.

### 15.3 Unverified assumptions and external facts

| Item | Classification | Why it is not silently assumed | Gate/owner |
|---|---|---|---|
| Current deployed V1 database contains no real/confidential business data | **unverified assumption** | repository files cannot prove deployed row contents | deployment owner inventories read-only export before V2-10 migration; until then V1 remains demo-only and must not receive such data |
| Current public V1 URL is private/access-restricted/clearly demo-labeled | **unverified assumption** | live access policy is external state | deployment owner verifies immediate containment; failure does not change V2-01 architecture but prohibits real V1 use |
| Live V1 environment secrets/CORS match repository examples | **unverified assumption** | deployed environment values are not stored in the repository | deployment owner performs secret/CORS review before any V1 exposure and again at V2-10 |

These are operational verification tasks, not unresolved Product Contract choices. They do not block V2-01 because V2 uses separate code, database, credentials, and staging. They block V1-to-V2 data import or cutover if not verified by V2-10.

### 15.4 High-priority risks

| 위험 | 심각도 | 영향 | 완화 게이트 |
|---|---|---|---|
| V1 production-like deployment creates known demo users/data | Critical | credential abuse and false production trust | V1 demo-only containment now; V2-01 production seed/routes count 0 |
| V1 public/optional-auth writes and approval | Critical | unauthorized pricing/approval mutation | no real V1 operations; V2-01 anonymous business writes and optional approval mutations 0 |
| V1 arbitrary public price-table `active` update | Critical | approval boundary bypass | Tier B frozen in V1; V2 core has no activation API or automatic activation |
| Quote lineage 부재 | High | 감사/리포트/승인 근거 불명 | V2-04 additive Quote domain |
| Float money | High | rounding and reproducibility errors | section 11.2, V2 Decimal port and golden/integration tests |
| V1 migration framework 부재 | High | schema drift and unsafe rollback | clean V2 Alembic from V2-01; read-only V1 ETL at V2-10 |
| cost margin `1.0` 저장 가능 | High | division by zero | schema+DB check `<1` |
| V1 demo-tools flag incomplete | High | production reset/seed surface | V1 demo-only containment; V2 production routes unavailable and tested |
| 3,168-line App/state coupling | High | frontend regression and inaccessible navigation | clean V2 routed shell; legacy frontend not migrated |
| source-string UI tests | Medium | test count overstates user behavior | new RTL/Playwright interaction evidence; no source-placement migration |
| V1 localStorage bearer token | Medium/High | token theft after XSS | V1 contains no real data; V2-01 rewrites auth transport and adds browser security tests |
| naive UTC timestamps | Medium | timezone/deprecation 문제 | aware UTC migration |
| demo 5개 추가 제품 | Medium | MVP 포지셔닝과 fixture 혼선 | two-product seed contract |
| lists without pagination | Medium | data 증가 시 응답/UX 저하 | V2 feature별 pagination |
| no tenant boundary | Medium | initial SaaS cannot safely mix organizations | initial V2 is single-organization per deployment; multi-tenant workspace is an explicit non-goal |
| clean-repo behavior drift | High | selective port may subtly change verified formulas/errors | source-commit ledger, Decimal golden tests, contract comparison, V1 untouched rollback |
| V1/V2 cutover data uncertainty | High | missing or misconverted records | read-only inventory, versioned ETL, quarantine, rollback rehearsal before cutover |

## Blocking User Decisions

None. Customer intake, viewer cost visibility, self-approval, failed-validation handling, currency/rounding, AI phase/boundary, diagnostics exposure, advanced-feature deferral, repository strategy, and separate staging/rollback are finalized in this contract. The unverified operational facts in section 15.3 require later evidence but do not require a Product Contract choice before V2-01.

## 16. V2 Definition of Done

V2 전체는 다음 조건을 모두 만족할 때 완료다.

### Product and workflow

- 요청 -> Quote -> 가격 점검 -> 승인/반려 -> 리포트가 동일 lineage로 연결된다.
- 승인된 Quote revision과 report 숫자가 재현 가능하다.
- failed/high is never submitted and has no initial override; warning/medium requires a written reason; passed proceeds normally.
- normal self-approval is prohibited; any explicit demo exception is labeled and audited.
- 자동 가격표 활성화, email, payment, scraping은 존재하지 않는다.
- 초기 제품 데이터와 demo는 A3 Flyer, Product / Brand Sticker만 사용한다.
- core workflow passes with the external LLM disabled.

### API tiers

- Every Tier A capability in section 10 is implemented or selectively migrated, secured, contract-tested, and connected to persistent lineage.
- New Quote, line, revision, pricing snapshot, approval, report, audit, dashboard, health/demo-safety, and grounded-copilot contracts pass their phase gates.
- Tier B remains frozen by default, receives no new feature work during core rebuild, and does not block V2 completion; non-selected Tier B is absent from V2 UI and any justified V2-09 adapter is isolated under Operations rather than core navigation.
- Every selected Tier B adapter has written justification, isolated tests, and a reintroduce/deprecate/exclude disposition.
- Rebuilding all 99 V1 application operations to equal V2 quality is not a completion criterion.

### Security and roles

- production startup에서 demo user/data가 생성되지 않는다.
- demo-disabled 환경에서 demo credential/tool endpoint가 동작하지 않는다.
- anonymous business-data write APIs are 0; initial V2 has no public customer intake.
- viewer/manager/admin API matrix 테스트가 전부 통과한다.
- approval reviewer는 authenticated actor다.
- viewer can read summarized total cost, resulting margin, risk, and validation outcome but cannot obtain raw cost components/profile/CSV/configuration.
- detailed system status is admin-only and OpenAPI/schema is admin-only or disabled in production; health/live/ready remain public and sanitized.
- secret/token/password hash/raw DB URL 노출 0건이다.

### Data

- Alembic upgrade succeeds from empty DB and every supported prior V2 revision; documented recovery/downgrade checks pass.
- PostgreSQL integration test가 통과한다.
- money/rates match section 11.2 exactly, with no saved Float and exact API decimal strings.
- active cost profile uniqueness와 margin `<1`이 DB와 schema에서 강제된다.
- approved Quote revision과 audit/report snapshots는 immutable하다.
- V1 migration uses versioned read-only export/transform/import with quarantine; no unexplained loss and no reverse write to V1.

### Frontend

- 공개/인증 layout이 분리된다.
- 8개 인증 화면은 URL로 직접 접근, 새로고침, back/forward가 가능하다.
- loading/empty/error/permission states가 각 핵심 화면에 존재한다.
- 일반 업무 화면에 DB/OpenAPI/readiness/raw JSON이 없다.
- V2 repository contains no migrated legacy `App.jsx` feature structure, `activeSection` navigation, or JSX source-placement test dependency.
- desktop/tablet/mobile에서 core journey 수동 시각 QA가 통과한다.

### Grounded AI copilot

- V2-08 delivers all five committed contextual uses: candidate explanation, validation summary, approval-reason draft, rejection revision suggestion, and grounded report summary.
- Every saved output identifies required grounding artifacts/timestamps, fallback status, generation timestamp, and provider metadata where applicable.
- AI numeric/state mutations and fabricated source facts are 0; snapshot equality and source consistency tests pass.
- Provider-disabled, timeout, and failure modes preserve the deterministic core and produce a fallback or explicit unavailable result.

### Verification

- backend compile, full pytest, frontend build가 통과한다.
- domain/API/DB/role/component/E2E/security/AI/deployment-smoke layers are enforced in CI or release gates.
- complete happy path and rejection/new-revision Playwright flows pass.
- selected V1 Tier A behaviors have a source/evidence ledger and V2 replacement tests; Tier B is explicitly frozen/adapted/deprecated/excluded.
- tracked `.env`, DB, dist, node_modules, secret가 없다.
- V2 staging passes public health/live/ready, protected system/OpenAPI policy, auth/CORS, and complete core journey.
- V1 and V2 staging/deployments/databases remain separate until migration and rollback verification pass.
- V2 rollback to the prior artifact/database snapshot and traffic return to unchanged V1 are rehearsed before cutover.

## 17. Evidence Appendix

### 17.1 Baseline and repository

- Stable functional baseline: `origin/main`
- Stable commit: `08362d5d086d5deb7f37fe3be46c5cbf1b08575c` (`Clean remaining visible UI artifacts (#47)`)
- Stability evidence: latest fetched main, successful GitHub Actions `backend-checks` at `https://github.com/ohsewool/quoteops-ai/actions/runs/28515022109/job/84524516550`
- Historical release marker: `v0.1.0` -> `8387c5a1445615055c94fc50278b3ffb66f0f412`, verified ancestor of stable main
- PR-48 reference branch: `pr-48-cpq-workflow-app-shell-restructure`
- PR-48 reference commit: `7bda36360c5cb7196ee8bc0c8ad06f4f24f3e277`
- PR-48 relationship: merge base is stable main; `origin/main...HEAD` is `0 1`
- PR-48 diff scope: frontend shell/research and UI/source-contract tests; backend, requirements, Render configuration, and CI are unchanged from stable main
- Stable-contract dependency: backend behavior, APIs, models, deterministic rules, tests, and deployment configuration are evaluated from stable main; PR-48 informs only IA and known frontend problems
- Remote: `https://github.com/ohsewool/quoteops-ai.git`
- Product constraints: `AGENTS.md`
- Product/status docs: `README.md`, `docs/MVP_SPEC.md`, `docs/PROJECT_CONTEXT.md`, `docs/safety-boundaries.md`

### 17.2 Frontend evidence

- `frontend/src/App.jsx:137`: current eight-item navigation
- `frontend/src/App.jsx:503`: monolithic App state begins
- `frontend/src/App.jsx:623`: localStorage token restoration
- `frontend/src/App.jsx:1440`: unauthenticated public shell
- `frontend/src/App.jsx:1584`: state-based workspace navigation
- `frontend/src/App.jsx:1599`: dashboard
- `frontend/src/App.jsx:2061`: shared workflow page conditionals
- `frontend/src/App.jsx:2613`: approval table
- `frontend/src/App.jsx:2691`: customer requests
- `frontend/src/App.jsx:2772`: operations/data/CSV/workflow/audit
- `frontend/src/api/client.js`: 55 exported API functions and Axios bearer configuration
- `frontend/package.json`: React/Vite/Axios; no router, component test, or browser test dependency
- `frontend/src/styles.css`: current responsive/design rules

### 17.3 Backend composition and configuration

- `backend/main.py`: lifespan, router registration, startup demo seed
- `backend/config.py`: database/CORS/environment/demo/OpenAI safe settings
- `backend/db.py`: SQLite/PostgreSQL engine config, `create_all`, session
- `backend/auth.py`: PBKDF2 password, HMAC token, 8-hour TTL, roles
- `backend/seed.py`: default demo credentials, two startup products, price tables
- `.env.example`: local defaults and placeholders
- `render.yaml`: Render backend service only
- `docs/deployment/render-backend.md`
- `docs/deployment/render-frontend.md`

### 17.4 Model and schema evidence

- `backend/models.py`: ORM entities and relationships
- `backend/schemas.py`: request/response contracts and Literal states
- Runtime SQLAlchemy mapper inspection: 19 ORM classes
- Runtime OpenAPI inspection: 101 schemas

Actual mapper classes inspected:

```text
AuditLog
Competitor
CompetitorPrice
CostProfile
CustomerQuoteRequest
HtmlReport
PriceApprovalRequest
PriceTable
PriceTableItem
PriceTableSnapshot
PriceTableSnapshotItem
PricingSimulation
PricingSimulationScenario
PricingStrategyTemplate
Product
ScenarioComparison
ScenarioComparisonItem
User
WorkflowJob
```

### 17.5 Pricing and workflow services

- `backend/services/quote_preview_service.py`: cost/margin quote formula
- `backend/services/candidate_price_service.py`: default margins and candidate formula
- `backend/services/validation_service.py`: four current checks and risk mapping
- `backend/services/customer_quote_request_service.py`: request states and transient calculations
- `backend/services/approval_service.py`: pending/approve/reject state
- `backend/services/price_table_history_service.py`: snapshot and comparison
- `backend/services/pricing_simulation_service.py`: quantity x margin scenarios
- `backend/services/scenario_comparison_service.py`: comparison summary
- `backend/services/html_report_service.py`: six report types and safe HTML escaping
- `backend/services/audit_service.py`: sensitive metadata filtering
- `backend/services/workflow_job_service.py`: synchronous job state machine
- `backend/services/strategy_template_service.py`: preset margin application
- `backend/services/demo_data_service.py`: extended demo data, reset boundaries, guided flow

### 17.6 Router and API evidence

- `backend/routers/*.py`: 23 registered router modules
- Runtime `app.openapi()`: 99 application operations, 74 paths, 101 schemas
- Runtime dependency inspection: 34 public, 7 optional-auth, 1 authenticated, 35 viewer+, 20 manager+, 2 admin operations
- `backend/routers/health_api.py`: health/live/ready/status
- `backend/routers/auth_api.py`: login/me/demo users
- `backend/routers/customer_quote_requests_api.py`: request workflow and audit
- `backend/routers/approval_requests_api.py`: optional-auth decision routes
- `backend/routers/import_export_api.py`: role-protected CSV and audit
- `backend/routers/demo_api.py`: role checks but no environment flag guard

### 17.7 Test evidence

- `tests/`: 54 files, 410 test functions
- `tests/test_final_regression_business_flow.py`: current deterministic cross-feature flow
- `tests/test_auth_api.py`: current token/role helper behavior
- `tests/test_approval_workflow_api.py`: unauthenticated approval behavior is part of current tests
- `tests/test_customer_quote_requests_api.py`: request lifecycle and adapters
- `tests/test_candidate_prices_api.py`
- `tests/test_validation_engine_api.py`
- `tests/test_price_table_history_api.py`
- `tests/test_pricing_simulation_api.py`
- `tests/test_scenario_comparison_api.py`
- `tests/test_html_reports_api.py`, `tests/test_html_report_security.py`
- `tests/test_health_status_hardening.py`, `tests/test_system_status_security.py`
- `tests/test_frontend_navigation_structure.py`, `tests/test_cpq_workflow_app_shell_restructure.py`: source-string UI contracts
- `.github/workflows/ci.yml`: compile, pytest, frontend build, docs-only implementation guard

Current-branch verification executed for repository analysis; stable main has the separate successful CI evidence recorded in 17.1:

```text
TEST_DATABASE=C:\Users\82105\AppData\Local\Temp\quoteops_v2_contract_tests_35848092-4540-411b-a6a5-28a21ae0bdeb.db
410 passed, 1131 warnings in 74.93s (0:01:14)
```

### 17.8 Research reference

- External reference only: `D:\다운로드\QuoteOps AI 인증 앱 구조 리서치.pdf`
- 14 pages, A4, visually rendered and inspected outside the repository
- Relevant conclusions used as design evidence:
  - pre-login persuades; post-login executes
  - dashboard prioritizes work, not features
  - Quote uses editor + summary + next action
  - pricing check unifies cost/margin/candidate/rules/comparison
  - simulation belongs under pricing check
  - approval uses inbox/list/detail
  - report manages artifacts, not raw API output
  - operations isolates DB/OpenAPI/health/CSV/audit
  - demo is a guided business flow
- The PDF is not tracked and must not be committed.

---

Approval-condition audit:

- stable functional baseline and commit: verified
- clean repository strategy: finalized
- Tier A and Tier B: finalized across matrix, API contracts, phases, tests, and DoD
- AI responsibility and V2-08 delivery boundary: finalized
- V2-01 measurable security gate: finalized
- blocking user decisions: none
- repository strategy, screen/API contracts, migration/rollback, tests, and DoD: internally aligned

## V2-00 APPROVED FOR IMPLEMENTATION
