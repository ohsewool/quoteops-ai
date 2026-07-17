import { useState } from "react";

import { ApiClientError } from "../api/client.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import PublicLayout from "../layouts/PublicLayout.jsx";
import { navigate, requestedDestination } from "../router.jsx";

const demoEnabled = import.meta.env.VITE_DEMO_ENABLED === "true";

function safeLoginMessage(error) {
  if (error instanceof ApiClientError && error.code === "invalid_credentials") {
    return "아이디 또는 비밀번호를 확인하세요.";
  }
  if (error instanceof ApiClientError && error.code === "authentication_unavailable") {
    return "로그인을 지금 사용할 수 없습니다. 잠시 후 다시 시도하세요.";
  }
  return "로그인 요청을 완료하지 못했습니다. 다시 시도하세요.";
}

export default function LoginPage() {
  const { login, state } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login({ username, password });
      navigate(requestedDestination(window.location.search), { replace: true });
    } catch (requestError) {
      setError(safeLoginMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PublicLayout>
      <main className="login-page">
        <section className="login-surface" aria-labelledby="login-title">
          <p className="eyebrow">Secure workspace</p>
          <h1 id="login-title">업무 공간 로그인</h1>
          <p>권한에 맞는 QuoteOps AI 업무 공간으로 이동합니다.</p>
          <form onSubmit={handleSubmit} noValidate>
            <label htmlFor="username">아이디</label>
            <input id="username" autoComplete="username" maxLength="64" minLength="3" onChange={(event) => setUsername(event.target.value)} required value={username} />
            <label htmlFor="password">비밀번호</label>
            <input id="password" autoComplete="current-password" maxLength="256" minLength="1" onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
            {error ? <p className="form-error" role="alert">{error}</p> : null}
            <button className="button button-primary" disabled={submitting || state === "restoring"} type="submit">
              {submitting ? "로그인 확인 중" : "로그인"}
            </button>
          </form>
          {demoEnabled ? <p className="demo-note">데모 모드가 명시적으로 활성화되어 있습니다. 계정 정보는 제공되지 않습니다.</p> : null}
        </section>
      </main>
    </PublicLayout>
  );
}
