import { useEffect } from "react";

import { useAuth } from "../auth/AuthProvider.jsx";
import { currentPath, loginPath, navigate } from "../router.jsx";

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, state } = useAuth();

  useEffect(() => {
    if (state === "anonymous") {
      navigate(loginPath(currentPath()), { replace: true });
    }
  }, [state]);

  if (state === "restoring" || state === "authenticating") {
    return <main className="route-state" aria-live="polite">세션을 확인하고 있습니다.</main>;
  }
  if (!isAuthenticated) {
    return <main className="route-state" aria-live="polite">안전하게 로그인 화면으로 이동합니다.</main>;
  }
  return children;
}
