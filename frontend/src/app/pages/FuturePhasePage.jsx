export default function FuturePhasePage({ title, phase, description }) {
  return (
    <section className="workspace-page future-page" aria-labelledby="future-title">
      <p className="eyebrow">Planned in {phase}</p>
      <h1 data-route-heading id="future-title" tabIndex="-1">{title}</h1>
      <p className="page-lede">{description}</p>
      <div className="honest-panel">
        <h2>아직 표시하지 않는 이유</h2>
        <p>이 화면의 실제 데이터와 작업은 {phase}의 persistence, authorization, tests, and audit gates가 통과된 뒤에만 제공됩니다.</p>
      </div>
    </section>
  );
}
