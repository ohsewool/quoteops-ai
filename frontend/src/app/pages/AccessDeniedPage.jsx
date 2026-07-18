export default function AccessDeniedPage() {
  return (
    <section className="workspace-page" aria-labelledby="access-title">
      <p className="eyebrow">Permission required</p>
      <h1 data-route-heading id="access-title" tabIndex="-1">접근 권한이 없습니다</h1>
      <p className="page-lede">이 화면은 현재 역할에 제공되지 않습니다. 서버도 별도로 권한을 검증합니다.</p>
    </section>
  );
}
