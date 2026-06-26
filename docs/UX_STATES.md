# UX States

PR-31 standardizes frontend loading, empty, error, permission, backend
unavailable, and OpenAI fallback messaging. It does not change pricing formulas,
candidate generation, validation rules, approval rules, role enforcement,
database behavior, health/status behavior, or demo reset behavior.

## Loading

Use a visible loading state when a section is waiting for backend data:

```text
데이터를 불러오는 중입니다.
잠시만 기다려 주세요.
```

## Empty Data

Tables and panels should explain that no records exist instead of rendering a
blank area:

```text
아직 표시할 데이터가 없습니다.
먼저 샘플 데이터를 준비하거나 관련 항목을 추가해 주세요.
```

Empty states must not insert fake data automatically.

## API Errors

API failures should show the safest useful message:

- `401`: 관리자 로그인이 필요합니다.
- `403`: 현재 계정 권한으로는 이 작업을 수행할 수 없습니다.
- `404`: 요청한 데이터를 찾을 수 없습니다.
- `422`: 입력값을 다시 확인해 주세요.
- network/backend unavailable: `VITE_API_BASE_URL` and backend status should be checked.

Errors must not expose raw `DATABASE_URL`, passwords, bearer tokens, OpenAI API
keys, or stack traces.

## Permission Denied

Permission states should explain which role is needed while keeping backend role
checks as the source of truth:

```text
현재 계정 권한으로는 이 작업을 수행할 수 없습니다.
필요한 경우 owner 계정으로 다시 시도해 주세요.
```

The frontend may disable buttons for clarity, but protected backend endpoints
still enforce owner/manager/viewer behavior.

## Backend Unavailable

When the frontend cannot reach the API:

```text
백엔드 서버에 연결할 수 없습니다.
VITE_API_BASE_URL 설정과 백엔드 실행 상태를 확인해 주세요.
```

## OpenAI Fallback

Missing `OPENAI_API_KEY` is expected in local demos. The UI should state:

```text
OpenAI API 키가 없으면 기본 설명 모드로 동작합니다.
AI 설명은 가격 숫자를 생성하지 않습니다.
```

Fallback explanation is allowed because numeric prices, margins, validation
results, approval decisions, and activation remain deterministic backend
behavior.

## Known Limitations

- PR-31 keeps the workspace as a single-page React app.
- UX state coverage is focused on existing MVP sections and smoke-testable
  workflows.
- Exhaustive per-field validation remains backend-driven; the frontend adds
  simple required-field and positive-number guidance only where useful.
