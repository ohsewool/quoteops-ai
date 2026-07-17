import { AuthProvider } from "./app/auth/AuthProvider.jsx";
import { useLocation } from "./app/router.jsx";
import LoginPage from "./app/pages/LoginPage.jsx";
import ProtectedRoute from "./app/pages/ProtectedRoute.jsx";
import PublicLanding from "./app/pages/PublicLanding.jsx";
import WorkspaceEntry from "./app/pages/WorkspaceEntry.jsx";

function RouteView() {
  const location = useLocation();
  const path = location.split("?")[0];

  if (path === "/") return <PublicLanding />;
  if (path === "/login") return <LoginPage />;
  if (path === "/app" || path === "/app/") {
    return <ProtectedRoute><WorkspaceEntry /></ProtectedRoute>;
  }
  return <PublicLanding />;
}

export default function App() {
  return <AuthProvider><RouteView /></AuthProvider>;
}
