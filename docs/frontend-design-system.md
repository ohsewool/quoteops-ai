# QuoteOps AI 프론트엔드 디자인 시스템 기초

PR-37은 전체 화면 재설계가 아니라 이후 UI/UX 개선 PR에서 함께 사용할 토큰과 반응형 레이아웃 기초를 추가한다.

## 토큰

`frontend/src/styles.css`의 `:root`에 다음 기준 토큰을 둔다.

- 색상: `--color-bg`, `--color-surface`, `--color-text`, `--color-muted`, `--color-border`, `--color-primary`, `--color-success`, `--color-warning`, `--color-danger`, `--color-info`
- 형태: `--radius`, `--radius-sm`, `--shadow`
- 간격: `--space-1`부터 `--space-8`
- 글자 크기: `--text-xs`부터 `--text-3xl`

## 반응형 기준

- 데스크톱: `1200px` 이상
- 랩톱: `1024px`부터 `1199px`
- 태블릿: `768px`부터 `1023px`
- 모바일: `767px` 이하

모바일에서는 주요 버튼과 내비게이션 터치 영역을 넓히고, 카드와 상태 영역은 줄바꿈되며, 표는 `table-wrap` 안에서 가로 스크롤된다.

## 재사용 클래스

주요 클래스는 다음 흐름을 기준으로 사용한다.

- 앱 골격: `app-shell`, `app-header`, `app-main`, `page-container`
- 콘텐츠: `section`, `section-header`, `card`, `card-grid`, `status-grid`
- 입력: `form-grid`, `field`
- 액션: `button`, `button-primary`, `button-secondary`, `button-ghost`
- 상태: `badge`, `badge-success`, `badge-warning`, `badge-danger`, `empty-state`, `error-state`
- 표: `table-wrap`
- 홈 화면: `overview-home`, `overview-hero`, `overview-grid`, `workflow-grid`, `workflow-card`

## 이번 PR에서 바꾸지 않는 것

PR-37은 가격 계산, 승인, 인증, 데이터베이스, 백엔드 API, 워크플로 구조를 변경하지 않는다. PR-38은 홈 화면 첫인상만 개선하고 다른 업무 화면의 구조 변경은 이후 PR에서 다룬다.
