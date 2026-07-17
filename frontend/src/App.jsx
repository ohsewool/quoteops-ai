import { AuthProvider } from "./app/auth/AuthProvider.jsx";
import { useAuth } from "./app/auth/AuthProvider.jsx";
import WorkspaceLayout from "./app/layouts/WorkspaceLayout.jsx";
import { useLocation } from "./app/router.jsx";
import AccessDeniedPage from "./app/pages/AccessDeniedPage.jsx";
import DashboardShell from "./app/pages/DashboardShell.jsx";
import DemoShell from "./app/pages/DemoShell.jsx";
import FuturePhasePage from "./app/pages/FuturePhasePage.jsx";
import LoginPage from "./app/pages/LoginPage.jsx";
import OperationsPage from "./app/pages/OperationsPage.jsx";
import ProtectedRoute from "./app/pages/ProtectedRoute.jsx";
import PublicLanding from "./app/pages/PublicLanding.jsx";

const demoEnabled = import.meta.env.VITE_DEMO_ENABLED === "true";

const plannedPages = {
  "/app/requests": { title: "고객 요청", phase: "V2-03", description: "고객 요청 workflow는 V2-03에서 구현됩니다." },
  "/app/quotes": { title: "견적", phase: "V2-04", description: "지속형 견적과 line-item workspace는 V2-04에서 구현됩니다." },
  "/app/pricing": { title: "가격 검토", phase: "V2-05", description: "결정적 candidate와 validation workspace는 V2-05에서 구현됩니다." },
  "/app/approvals": { title: "승인", phase: "V2-06", description: "Quote-scoped approval inbox는 V2-06에서 구현됩니다." },
  "/app/reports": { title: "리포트", phase: "V2-07", description: "승인된 견적 기반 report center는 V2-07에서 구현됩니다." }
};

function WorkspaceRoutes() {
  const location = useLocation();
  const { user } = useAuth();
  const path = location.split("?")[0];
  let page;

  if (path === "/app" || path === "/app/") {
    page = <DashboardShell />;
  } else if (path === "/app/dashboard") {
    page = <DashboardShell />;
  } else if (plannedPages[path]) {
    page = <FuturePhasePage {...plannedPages[path]} />;
  } else if (path === "/app/operations") {
    page = user.role === "admin" ? <OperationsPage /> : <AccessDeniedPage />;
  } else if (path === "/app/demo") {
    page = demoEnabled && ["admin", "manager"].includes(user.role) ? <DemoShell /> : <AccessDeniedPage />;
  } else {
    page = <FuturePhasePage title="업무 공간" phase="V2" description="요청한 업무 공간을 찾을 수 없습니다." />;
  }

  return <WorkspaceLayout>{page}</WorkspaceLayout>;
}

function RouteView() {
  const location = useLocation();
  const path = location.split("?")[0];

  if (path === "/") return <PublicLanding />;
  if (path === "/login") return <LoginPage />;
  if (path.startsWith("/app")) {
    return <ProtectedRoute><WorkspaceRoutes /></ProtectedRoute>;
  }
  return <PublicLanding />;
}

export default function App() {
  return <AuthProvider><RouteView /></AuthProvider>;
}
