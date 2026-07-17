import { AuthProvider } from "./app/auth/AuthProvider.jsx";
import { useAuth } from "./app/auth/AuthProvider.jsx";
import WorkspaceLayout from "./app/layouts/WorkspaceLayout.jsx";
import { useLocation } from "./app/router.jsx";
import AccessDeniedPage from "./app/pages/AccessDeniedPage.jsx";
import {
  CustomerRequestDetailPage,
  CustomerRequestsPage,
  NewCustomerRequestPage
} from "./features/customerRequests/CustomerRequestsWorkspace.jsx";
import DashboardShell from "./app/pages/DashboardShell.jsx";
import DemoShell from "./app/pages/DemoShell.jsx";
import FuturePhasePage from "./app/pages/FuturePhasePage.jsx";
import LoginPage from "./app/pages/LoginPage.jsx";
import OperationsPage from "./app/pages/OperationsPage.jsx";
import ProtectedRoute from "./app/pages/ProtectedRoute.jsx";
import PublicLanding from "./app/pages/PublicLanding.jsx";
import { ApprovalInboxPage } from "./features/approvals/ApprovalInbox.jsx";
import { PricingChecksPage } from "./features/pricingChecks/PricingChecksWorkspace.jsx";
import { QuoteDetailPage, QuotesPage } from "./features/quotes/QuoteWorkspace.jsx";
import { ReportCenterPage } from "./features/reports/ReportCenter.jsx";

const demoEnabled = import.meta.env.VITE_DEMO_ENABLED === "true";

function WorkspaceRoutes() {
  const location = useLocation();
  const { user } = useAuth();
  const path = location.split("?")[0];
  let page;

  if (path === "/app" || path === "/app/") {
    page = <DashboardShell />;
  } else if (path === "/app/dashboard") {
    page = <DashboardShell />;
  } else if (path === "/app/requests") {
    page = <CustomerRequestsPage />;
  } else if (path === "/app/requests/new") {
    page = <NewCustomerRequestPage />;
  } else if (/^\/app\/requests\/\d+$/.test(path)) {
    page = <CustomerRequestDetailPage customerRequestId={Number(path.split("/").at(-1))} />;
  } else if (path === "/app/quotes") {
    page = <QuotesPage />;
  } else if (/^\/app\/quotes\/\d+$/.test(path)) {
    page = <QuoteDetailPage quoteId={Number(path.split("/").at(-1))} />;
  } else if (path === "/app/pricing") {
    page = <PricingChecksPage />;
  } else if (path === "/app/approvals") {
    page = <ApprovalInboxPage />;
  } else if (path === "/app/reports") {
    page = <ReportCenterPage />;
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
