# PR-42 포트폴리오 UI QA

## PR-42 목적

QuoteOps AI를 포트폴리오용 SaaS MVP로 보여주기 전에 최종 화면 흐름, 반응형 상태, 안전 문구, Render 재배포 확인 절차를 정리한다. 이 단계는 기능 추가가 아니라 최종 QA와 데모 준비 문서화다.

## 최종 화면 평가 범위

- 홈
- 견적
- 고객 요청
- 가격
- 승인
- 시뮬레이션
- 분석
- 리포트
- 운영
- 데모

각 화면에서 navigation, cards, forms, buttons, table-wrap, badges, empty/error state가 데스크톱, 노트북, 태블릿, 모바일에서 깨지지 않는지 확인한다.

## 포트폴리오 시연 흐름

1. 홈에서 서비스 목적 확인
2. 데모 계정으로 로그인
3. 샘플 데이터 준비
4. 견적 생성
5. 가격 평가
6. 승인 요청/처리
7. 시뮬레이션 확인
8. 리포트 생성
9. 운영 상태 확인

## 권장 스크린샷 목록

- 홈 첫 화면
- 견적 흐름
- 가격 도구
- 승인 관리
- 시뮬레이션
- 리포트
- 운영 상태
- 데모 화면
- 모바일 화면 1장

## Render 재배포 확인 방법

Frontend:

```text
https://quoteops-ai-frontend.onrender.com
```

Backend health:

```text
https://quoteops-ai-backend.onrender.com/api/health
```

Backend ready:

```text
https://quoteops-ai-backend.onrender.com/api/health/ready
```

Backend OpenAPI:

```text
https://quoteops-ai-backend.onrender.com/openapi.json
```

PowerShell 로컬 배포 QA 명령:

```powershell
$env:QUOTEOPS_DEPLOYED_BACKEND_URL="https://quoteops-ai-backend.onrender.com"
$env:QUOTEOPS_DEPLOYED_FRONTEND_URL="https://quoteops-ai-frontend.onrender.com"
python scripts/render_deployed_qa.py
```

## 라이브 데모 확인 URL

- Frontend: https://quoteops-ai-frontend.onrender.com
- Backend health: https://quoteops-ai-backend.onrender.com/api/health
- Backend ready: https://quoteops-ai-backend.onrender.com/api/health/ready
- Backend OpenAPI: https://quoteops-ai-backend.onrender.com/openapi.json

## 최종 QA 체크리스트

- 홈, 견적, 고객 요청, 가격, 승인, 시뮬레이션, 분석, 리포트, 운영, 데모 화면이 모두 접근 가능하다.
- 데스크톱 1200px 이상에서 화면이 과하게 넓어 보이지 않는다.
- 노트북 1024px-1199px에서 navigation과 cards가 자연스럽게 줄바꿈된다.
- 태블릿 768px-1023px에서 forms와 status grids가 읽기 쉽게 쌓인다.
- 모바일 768px 미만에서 buttons가 넘치지 않고 cards가 단일 컬럼으로 쌓인다.
- table-wrap 안의 표만 가로 스크롤되고 페이지 전체에는 가로 넘침이 없다.
- 안전 문구 `승인 전 자동 반영 없음`이 유지된다.
- UI는 가격을 자동 승인, 자동 활성화, 자동 전송한다고 암시하지 않는다.
- frontend/dist와 node_modules는 커밋하지 않는다.

## 알려진 제한사항

- 이 프로젝트는 포트폴리오 SaaS MVP다.
- 가격을 자동 승인, 자동 활성화, 자동 전송하지 않는다.
- 실제 경쟁사 웹사이트 스크래핑을 하지 않는다.
- 실제 결제를 처리하지 않는다.
- 데모 데이터는 발표와 테스트용이다.

## PR-43 최종 문구 정리

PR-43에서는 홈 헤드라인, 주요 상태 카드, 보조 버튼 위계, 견적/고객 요청 폼의 한국어 라벨을 정리한다. 기능, API, 가격 계산식, 인증, 데이터베이스 구조는 변경하지 않는다.

## PR-44 공개 랜딩과 시각 정체성

PR-44부터 로그인 전에는 공개 랜딩을 먼저 보여주고, 로그인 또는 데모 역할 선택 후에 내부 앱 셸을 보여준다. 내부 기술 상태는 공개 랜딩에 노출하지 않고 운영 화면에서 확인한다. 최종 스크린샷은 공개 랜딩과 인증 후 앱 화면을 모두 포함한다.

선택 팔레트는 Pure Orange `#fe7902`, Charcoal `#292929`, Cream `#fffff5`이다. 반응형 QA는 desktop, laptop, tablet, mobile에서 공개 랜딩 hero, CTA, 데모 패널, 내부 앱 navigation을 함께 확인한다.
