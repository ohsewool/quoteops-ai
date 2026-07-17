import { useEffect, useState } from "react";

import { useAuth } from "../auth/AuthProvider.jsx";

export default function OperationsPage() {
  const { request } = useAuth();
  const [state, setState] = useState({ status: "loading", data: null });

  useEffect(() => {
    let active = true;
    request("/api/system/status")
      .then((data) => active && setState({ status: "ready", data }))
      .catch(() => active && setState({ status: "error", data: null }));
    return () => { active = false; };
  }, [request]);

  return (
    <section className="workspace-page" aria-labelledby="operations-title">
      <p className="eyebrow">Admin only</p>
      <h1 data-route-heading id="operations-title" tabIndex="-1">운영</h1>
      <p className="page-lede">안전한 V2 foundation 상태만 표시합니다. 연결 문자열, 인증 헤더, 비밀번호와 raw log는 표시하지 않습니다.</p>
      {state.status === "loading" ? <p className="inline-state" aria-live="polite">운영 상태를 확인하고 있습니다.</p> : null}
      {state.status === "error" ? <p className="form-error" role="alert">운영 상태를 지금 불러올 수 없습니다. 다시 시도하세요.</p> : null}
      {state.status === "ready" ? (
        <dl className="status-list">
          <div><dt>환경</dt><dd>{state.data.environment}</dd></div>
          <div><dt>데이터베이스 설정</dt><dd>{state.data.database_configured ? "확인됨" : "확인 필요"}</dd></div>
          <div><dt>문서 노출</dt><dd>{state.data.docs_enabled ? "현재 환경에서 허용" : "비활성"}</dd></div>
          <div><dt>OpenAPI 노출</dt><dd>{state.data.openapi_enabled ? "현재 환경에서 허용" : "비활성"}</dd></div>
        </dl>
      ) : null}
    </section>
  );
}
