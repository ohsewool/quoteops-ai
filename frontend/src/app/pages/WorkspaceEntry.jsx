import { useAuth } from "../auth/AuthProvider.jsx";

export default function WorkspaceEntry() {
  const { logout, user } = useAuth();
  return (
    <main className="workspace-entry" aria-labelledby="workspace-title">
      <section>
        <p className="eyebrow">Authenticated session</p>
        <h1 id="workspace-title">{user.display_name}님의 업무 공간</h1>
        <p>V2-02B에서 역할별 내비게이션과 대시보드 shell이 준비됩니다.</p>
        <button className="button button-secondary" onClick={logout} type="button">로그아웃</button>
      </section>
    </main>
  );
}
