import { useAuth } from "../auth/AuthProvider.jsx";

export default function DashboardShell() {
  const { user } = useAuth();
  return (
    <section className="workspace-page" aria-labelledby="dashboard-title">
      <p className="eyebrow">Workspace overview</p>
      <h1 data-route-heading id="dashboard-title" tabIndex="-1">대시보드</h1>
      <p className="page-lede">{user.display_name}님, 현재 대시보드는 실제 운영 데이터가 쌓이는 순서에 맞춰 준비됩니다.</p>
      <div className="honest-panel">
        <h2>현재 준비된 기반</h2>
        <ul>
          <li>권한 기반 업무 공간과 안전한 세션 복구</li>
          <li>공개 health/readiness 및 관리자 전용 운영 상태</li>
          <li>고객 요청, 견적, 가격 검토, 승인, 리포트의 안정된 URL</li>
        </ul>
      </div>
      <p className="empty-note">아직 고객, 견적, 승인 또는 가격 KPI는 표시하지 않습니다. 해당 데이터는 각 workflow phase가 검증된 뒤에만 나타납니다.</p>
    </section>
  );
}
