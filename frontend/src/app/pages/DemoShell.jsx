export default function DemoShell() {
  return (
    <section className="workspace-page" aria-labelledby="demo-title">
      <p className="eyebrow">Explicit non-production demo mode</p>
      <h1 data-route-heading id="demo-title" tabIndex="-1">데모</h1>
      <p className="page-lede">데모 흐름과 reset isolation은 V2-09에서 검증됩니다. 이 shell은 계정, 가격, 고객 또는 reset 도구를 제공하지 않습니다.</p>
    </section>
  );
}
