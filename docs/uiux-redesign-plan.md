# QuoteOps AI UI/UX 리디자인 계획

이 문서는 PR-37부터 PR-42까지의 프론트엔드 UI/UX 개선 방향을 정리한 실행 계획이다. 이번 PR-36에서는 실제 화면을 바꾸지 않고, 이후 작업이 일관된 기준으로 진행되도록 정보 구조, 반응형 전략, 한국어 카피 원칙, 단계별 PR 범위를 정의한다.

## 1. 요약 결론

QuoteOps AI v0.1.0은 기능과 배포 기반은 갖췄지만, 현재 첫 화면은 기능 검증용 내부 관리자 화면에 가깝다. 다음 리디자인의 핵심은 기능을 더 많이 보여주는 것이 아니라, 사용자가 "지금 무엇을 해야 하는지"를 빠르게 이해하도록 흐름을 줄이는 것이다.

핵심 방향은 다음과 같다.

- 첫 화면은 "견적 시작"과 "최근 작업" 중심으로 단순화한다.
- 상위 메뉴를 7개 업무 단위로 줄인다: 홈, 견적, 가격, 승인, 분석, 운영, 데모.
- 로그인, 시스템 상태, 관리자 도구는 보조 정보로 낮춘다.
- 복잡한 기능은 progressive disclosure 방식으로 단계별 노출한다.
- 한국어 UI 카피는 직역을 피하고 짧은 업무 언어로 쓴다.
- 데스크톱, 노트북, 태블릿, 모바일에서 카드, 표, 폼, 결과 패널이 무너지지 않도록 반응형 기준을 먼저 세운다.

## 2. 현재 UI 문제 진단

현재 UI 문제 진단은 기능 부족이 아니라 표현 방식의 문제다.

- 첫 화면에 기능이 과도하게 노출되어 핵심 작업이 보이지 않는다.
- 탐색 구조가 API 기능 목록처럼 보여 실제 업무 흐름을 만들지 못한다.
- 견적 요청, 가격 계산, 검증, 승인, 리포트의 순서가 한눈에 보이지 않는다.
- 로그인, 상태, 데모, 관리자성 요소가 주요 업무보다 시각적으로 강하다.
- 표와 카드가 많아 우선순위가 흐려지고, 화면 밀도가 높다.
- 영어 개념을 그대로 번역하면 한국어 문장이 길고 딱딱해질 가능성이 높다.
- 모바일과 태블릿에서는 표, 버튼, 상태 카드, 로그인 영역이 겹치거나 길어질 위험이 있다.

## 3. 테스트 페이지처럼 보이는가?

현재 화면은 실제 SaaS 제품보다 "모든 엔드포인트를 눌러보는 테스트 콘솔"에 가깝게 보인다. 사용자가 처음 들어왔을 때 제품의 약속보다 기능 목록이 먼저 보이고, 업무 목적보다 내부 상태가 먼저 보인다.

테스트 페이지처럼 보이는 징후는 다음과 같다.

- 메뉴가 기능 단위로 너무 세분화되어 있다.
- 버튼 문구가 사용자의 업무 언어보다 개발 기능명에 가깝다.
- 데모 도구와 상태 정보가 첫 화면에서 과도하게 눈에 띈다.
- 결과 패널과 입력 폼이 같은 시각적 무게로 나열된다.
- "무엇을 먼저 눌러야 하는지"가 카피와 배치로 안내되지 않는다.

## 4. 실제 SaaS처럼 보이기 위한 원칙

실제 SaaS처럼 보이려면 화면이 기능을 과시하기보다 사용자의 업무 결정을 돕는 구조가 되어야 한다.

- 한 화면의 주 작업은 하나만 둔다.
- 첫 화면은 요약, 다음 행동, 최근 활동으로 제한한다.
- 상세 기능은 업무 흐름 안에서 단계별로 열리게 한다.
- 상태 정보는 문제 발생 시 드러나고, 평상시에는 축약한다.
- 관리 도구와 데모 도구는 별도 영역으로 분리한다.
- CTA는 "견적 시작"처럼 행동 중심으로 쓴다.
- 경고, 승인 대기, 검증 실패 같은 중요한 상태만 색과 강조를 사용한다.

## 5. Apple / ChatGPT / Chrome에서 참고할 원칙

Apple, ChatGPT, Chrome의 시각 스타일을 복사하지 않는다. 참고할 것은 형태가 아니라 원칙이다.

- 단순함: 첫 인지 부담을 낮춘다.
- 여백: 화면을 기능별 박스로 가득 채우지 않는다.
- 낮은 시각 소음: 색, 그림자, 배지를 제한한다.
- 명확한 계층: 제목, 설명, 행동, 결과가 순서대로 읽힌다.
- 빠른 주 행동 접근: 사용자가 가장 자주 하는 작업을 1-2번 클릭 안에 둔다.
- 반복 사용성: 매일 쓰는 업무 화면은 화려함보다 예측 가능성이 중요하다.

## 6. 한국어 UI 카피 원칙

한국어 UI 카피 원칙은 직역이 아니라 실제 업무자가 말할 법한 짧은 표현을 쓰는 것이다.

좋은 카피 방향:

- 명사 나열보다 행동 중심으로 쓴다.
- 긴 설명은 카드 본문이 아니라 도움말이나 상세 패널로 보낸다.
- 버튼은 2-5음절 중심으로 짧게 쓴다.
- "AI가 해준다"보다 "계산, 검증, 승인 흐름을 돕는다"로 표현한다.
- 자동 반영이나 자동 승인처럼 오해될 수 있는 표현은 피한다.

예시 카피:

- 견적 가격 운영을 한곳에서
- 계산, 원가, 승인, 리포트까지 한 흐름으로
- 견적 시작
- 데모 보기
- 자동 반영 없음
- 데모 계정
- 가격 원가
- 승인 대기
- 리포트 생성
- 다시 불러오기
- 검증 결과
- 승인 요청
- 최근 작업
- 다음 단계

## 7. 정보구조 재설계안

정보구조 재설계안은 현재의 많은 상위 메뉴를 업무 단위로 묶는 것이다. 목표는 상위 탐색을 줄이고, 각 섹션 안에서 필요한 기능을 단계적으로 보여주는 것이다.

권장 상위 구조:

- 홈
- 견적
- 가격
- 승인
- 분석
- 운영
- 데모

기능 그룹:

홈:

- product summary
- system status summary
- main workflow cards
- recent activity
- demo start

견적:

- customer requests
- quote preview
- quote workflow status

가격:

- candidate prices
- price validation
- cost profiles
- strategy templates
- price table comparison/history

승인:

- approval requests
- approve/reject workflow
- approval logs
- audit logs

분석:

- pricing simulations
- scenario comparisons
- KPI dashboard
- dashboard insights
- reports

운영:

- CSV import/export
- workflow jobs
- system status
- health/readiness
- security/deployment checks

데모:

- demo data tools
- demo credentials
- sample scenarios
- presenter flow

## 8. 첫 화면 재설계안

첫 화면은 제품의 전체 기능 목록이 아니라 "오늘 할 일"을 보여줘야 한다.

권장 구성:

- 상단: 제품명, 짧은 설명, 주 CTA "견적 시작"
- 보조 CTA: "데모 보기"
- 중앙: 3개의 업무 카드
  - 견적 요청 확인
  - 가격 검증 진행
  - 승인 대기 확인
- 하단: 최근 활동, 주요 상태 요약, 데모 시작 안내
- 우측 또는 하단 보조 영역: 로그인 정보, 시스템 상태, 배포/보안 체크

첫 화면에서 감출 것:

- 전체 API 기능 목록
- 상세 테이블
- 긴 JSON 결과
- 관리자 도구 전체
- 데모 reset 같은 위험해 보이는 버튼

## 9. 반응형 레이아웃 전략

반응형 레이아웃 전략은 화면 폭마다 탐색, 카드, 폼, 결과 패널, 표, 버튼, 상태 카드, 로그인 패널이 어떻게 바뀌는지 명확히 정하는 것이다.

### 데스크톱: 1200px 이상

- navigation behavior: 좌측 사이드바 또는 상단+좌측 혼합 구조를 사용한다.
- card grid behavior: 3열 카드 그리드를 기본으로 한다.
- form layout: 입력 폼과 결과 패널을 2열로 배치한다.
- result panel layout: 결과 요약은 우측 고정 패널로 보여준다.
- table behavior: 표는 전체 폭을 사용하고 주요 열을 모두 보여준다.
- button behavior: 주요 CTA와 보조 CTA를 분리한다.
- status card behavior: 4개 이하의 상태 카드를 한 줄로 배치한다.
- login panel behavior: 우측 상단 또는 보조 영역으로 축소한다.

### 노트북: 1024px-1199px

- navigation behavior: 상단 메뉴와 접히는 보조 메뉴를 조합한다.
- card grid behavior: 2열 카드 그리드를 기본으로 한다.
- form layout: 폼은 한 열, 결과는 아래 또는 우측 좁은 패널로 둔다.
- result panel layout: 핵심 수치만 먼저 보이고 상세는 접는다.
- table behavior: 중요 열 중심으로 축약하고 나머지는 상세 패널에서 본다.
- button behavior: CTA는 한 줄에 2개 이하로 제한한다.
- status card behavior: 2열로 정리한다.
- login panel behavior: 사용자명과 역할만 간단히 보여준다.

### 태블릿: 768px-1023px

- navigation behavior: 상단 탭 또는 햄버거 메뉴로 전환한다.
- card grid behavior: 1-2열 혼합을 사용하고 카드 높이를 안정화한다.
- form layout: 모든 폼은 단일 열로 배치한다.
- result panel layout: 결과 패널은 폼 아래에 단계별로 쌓는다.
- table behavior: 표는 카드형 리스트 또는 가로 스크롤로 전환한다.
- button behavior: 주요 버튼은 넓게, 보조 버튼은 텍스트 링크처럼 약하게 둔다.
- status card behavior: 2열 또는 단일 열로 전환한다.
- login panel behavior: 접이식 계정 패널로 둔다.

### 모바일: 768px 미만

- navigation behavior: 하단 또는 햄버거 메뉴로 핵심 5-7개만 노출한다.
- card grid behavior: 단일 열 카드만 사용한다.
- form layout: 입력 필드는 한 줄에 하나씩 배치한다.
- result panel layout: 핵심 결과를 먼저 보여주고 상세는 펼치기 방식으로 둔다.
- table behavior: 표 대신 카드 리스트를 우선 사용한다.
- button behavior: 주요 CTA는 full width로 배치한다.
- status card behavior: 상태는 작은 배지와 한 줄 요약으로 줄인다.
- login panel behavior: 로그인/역할 정보는 프로필 버튼 안으로 숨긴다.

## 10. 화면별 개선 방향

화면별 개선 방향은 기능을 새로 만드는 것이 아니라 기존 기능을 업무 흐름 안에 다시 배치하는 것이다.

- 홈: 업무 시작 카드, 최근 활동, 시스템 정상 여부, 데모 시작만 보여준다.
- 견적: customer requests -> quote preview -> quote workflow status 순서로 안내한다.
- 가격: candidate prices, price validation, cost profiles, strategy templates를 한 흐름으로 묶는다.
- 승인: approval requests와 audit logs를 분리하되 승인 대기 상태를 가장 먼저 보여준다.
- 분석: pricing simulations, scenario comparisons, KPI dashboard, dashboard insights, reports를 의사결정용 화면으로 묶는다.
- 운영: CSV, workflow jobs, system status, health/readiness, security/deployment checks를 관리자 업무로 분리한다.
- 데모: demo data tools, demo credentials, sample scenarios, presenter flow를 발표용 시작점으로 정리한다.

## 11. 디자인 시스템 방향

디자인 시스템 방향은 새로운 장식보다 일관성을 우선한다.

- 색상: 회색 기반에 하나의 주요 액션 색만 사용한다.
- 타이포그래피: 제목, 설명, 메타 정보의 크기 차이를 명확히 한다.
- 카드: 중첩 카드를 피하고, 반복 항목에만 카드 스타일을 사용한다.
- 버튼: 주요 CTA, 보조 CTA, 위험 액션을 명확히 구분한다.
- 배지: 상태 표현에만 사용하고 장식용 배지는 줄인다.
- 폼: 라벨, 도움말, 오류 메시지를 같은 위치에 둔다.
- 표: 모든 데이터를 한 번에 보여주기보다 요약과 상세를 나눈다.
- 빈 상태: "아직 데이터가 없습니다"보다 다음 행동을 안내한다.

## 12. PR-37부터 PR-42까지의 실행 계획

### PR-37: Design system and responsive layout foundation

- goal: 레이아웃, 타이포그래피, 버튼, 카드, 배지, 반응형 토큰의 기반을 정리한다.
- expected files changed: `frontend/src/App.jsx`, `frontend/src/styles.css`, 관련 프론트엔드 테스트.
- what not to touch: backend, database models, pricing formulas, authentication logic.
- acceptance criteria: 주요 레이아웃 컨테이너와 버튼/카드 스타일이 일관되고, 1200/1024/768/mobile 기준이 코드에 반영된다.
- test commands: `pytest -q`, `cd frontend && npm run build`.
- Render redeploy check: 프론트엔드 재배포 후 첫 화면이 깨지지 않고 CSS가 적용되는지 확인한다.

### PR-38: Overview redesign

- goal: 홈 화면을 최소화하고 "견적 시작", 최근 작업, 상태 요약 중심으로 재구성한다.
- expected files changed: `frontend/src/App.jsx`, `frontend/src/styles.css`, overview 관련 테스트.
- what not to touch: backend APIs, database, deployment config.
- acceptance criteria: 첫 화면에서 주요 CTA가 명확하고, 로그인/상태/데모 요소가 보조 역할로 내려간다.
- test commands: `pytest -q`, `cd frontend && npm run build`.
- Render redeploy check: 배포 화면 첫 진입 시 blank page 없이 홈이 표시되는지 확인한다.

### PR-39: Quote/Pricing/Approval workflow restructure

- goal: 견적, 가격, 승인 흐름을 업무 순서대로 재배치한다.
- expected files changed: `frontend/src/App.jsx`, `frontend/src/styles.css`, 관련 프론트엔드 구조 테스트.
- what not to touch: pricing formulas, approval business logic, auth behavior.
- acceptance criteria: customer request -> quote preview -> candidate price -> validation -> approval 흐름이 명확하다.
- test commands: `pytest -q`, `cd frontend && npm run build`.
- Render redeploy check: 배포 환경에서 견적/가격/승인 섹션 이동과 주요 폼 렌더링을 확인한다.

### PR-40: Dashboard/Reports/Admin/Demo polish

- goal: 분석, 운영, 데모 영역을 업무 목적별로 정리하고 과도한 관리자 느낌을 줄인다.
- expected files changed: `frontend/src/App.jsx`, `frontend/src/styles.css`, demo/dashboard/report 관련 테스트.
- what not to touch: report generation logic, demo backend endpoints, security checks.
- acceptance criteria: 분석 화면은 의사결정 중심, 운영 화면은 관리 중심, 데모 화면은 발표 흐름 중심으로 분리된다.
- test commands: `pytest -q`, `cd frontend && npm run build`.
- Render redeploy check: Dashboard, Reports, Demo Tools가 배포 환경에서 정상 표시되는지 확인한다.

### PR-41: Mobile and tablet responsive QA

- goal: 768px 미만과 768-1023px 구간에서 폼, 표, 카드, 버튼이 겹치지 않게 보정한다.
- expected files changed: `frontend/src/styles.css`, `frontend/src/App.jsx`, responsive contract tests.
- what not to touch: backend logic, database, release tags.
- acceptance criteria: 모바일에서 주요 CTA, 카드, 폼, 결과 패널, 표가 읽을 수 있는 구조로 전환된다.
- test commands: `pytest -q`, `cd frontend && npm run build`.
- Render redeploy check: 실제 배포 URL을 모바일/태블릿 폭으로 확인하고 가로 스크롤/겹침을 점검한다.

### PR-42: Final portfolio UI QA and Render redeploy check

- goal: 포트폴리오 관점에서 전체 UI를 최종 점검하고 배포 화면을 검증한다.
- expected files changed: `frontend/src/App.jsx`, `frontend/src/styles.css`, docs 또는 QA 테스트.
- what not to touch: backend business logic, database models, pricing formulas, auth logic.
- acceptance criteria: 첫 화면, 견적 흐름, 분석, 운영, 데모 흐름이 한국어 SaaS 제품처럼 일관되게 보인다.
- test commands: `python -m compileall backend`, `pytest -q`, `cd frontend && npm run build`.
- Render redeploy check: Render frontend/backend URL에서 health, first screen, quote flow, dashboard, report, demo flow를 확인한다.

## 13. 구현 때 건드리면 안 되는 범위

PR-37부터 PR-42까지 UI/UX 개선 중에도 다음 범위는 건드리지 않는다.

- backend business logic
- database models
- pricing formulas
- authentication logic
- approval workflow semantics
- release tags
- GitHub Release
- Render backend deployment settings
- rescue-pr01-pr35-uncommitted-work

## 14. 완료 기준

리디자인 완료 기준은 "예쁘다"가 아니라 "업무 흐름이 명확하다"이다.

- 첫 화면에서 견적 시작 경로가 즉시 보인다.
- 상위 메뉴가 홈, 견적, 가격, 승인, 분석, 운영, 데모로 정리된다.
- 한국어 카피가 짧고 자연스럽다.
- 로그인과 시스템 상태는 보조 정보로 보인다.
- 데스크톱, 노트북, 태블릿, 모바일에서 레이아웃이 겹치지 않는다.
- 표와 결과 패널은 화면 폭에 맞게 축약된다.
- 데모 흐름은 발표자가 따라가기 쉽다.
- Render 배포 화면에서 blank page, overflow, 버튼 겹침이 없다.

## 검증 키워드

테스트 안정성을 위한 키워드: 현재 UI 문제 진단, 정보구조, 반응형, 한국어 UI 카피, 점진적 공개, 홈, 견적, 가격, 승인, 분석, 운영, 데모, PR-37, PR-38, PR-39, PR-40, PR-41, PR-42.
