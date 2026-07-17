import PublicLayout from "../layouts/PublicLayout.jsx";
import { navigate } from "../router.jsx";

const workflow = ["고객 요청", "견적 초안", "결정적 가격 검토", "사람의 승인", "근거 있는 보고서"];

export default function PublicLanding() {
  return (
    <PublicLayout>
      <main>
        <section className="landing-hero" aria-labelledby="landing-title">
          <div className="landing-copy">
            <p className="eyebrow">Pricing operations for print teams</p>
            <h1 id="landing-title">QuoteOps AI</h1>
            <p className="landing-lede">
              소규모 인쇄·주문제작 팀이 원가, 시장 기준, 최소 마진과 사람의 검토를 함께 사용해 안전한 견적을 운영합니다.
            </p>
            <div className="hero-actions">
              <button className="button button-primary" type="button" onClick={() => navigate("/login")}>업무 공간으로 로그인</button>
            </div>
          </div>
          <figure className="product-visual" aria-label="A3 flyer and product sticker examples">
            <div className="flyer-sheet"><span>A3</span><strong>FLYER</strong></div>
            <div className="sticker-sheet"><span>BRAND</span><strong>STICKER</strong></div>
            <figcaption>초기 지원 제품: A3 Flyer, Product / Brand Sticker</figcaption>
          </figure>
        </section>

        <section className="content-band workflow-band" aria-labelledby="workflow-title">
          <div className="section-heading">
            <p className="eyebrow">Core workflow</p>
            <h2 id="workflow-title">숫자는 결정적으로, 결정은 사람에게</h2>
          </div>
          <ol className="workflow-list">
            {workflow.map((step, index) => <li key={step}><span>{String(index + 1).padStart(2, "0")}</span>{step}</li>)}
          </ol>
        </section>

        <section className="content-band safety-band" aria-labelledby="safety-title">
          <div className="section-heading">
            <p className="eyebrow">Safety by design</p>
            <h2 id="safety-title">AI가 가격이나 승인 상태를 바꾸지 않습니다.</h2>
          </div>
          <div className="safety-grid">
            <article>
              <h3>결정적 가격 계산</h3>
              <p>원가, 마진, 수량과 검증 규칙은 서버의 Decimal 계산으로 재현됩니다.</p>
            </article>
            <article>
              <h3>승인 전 검토</h3>
              <p>후보 가격은 검증과 사람의 승인 없이는 활성화되지 않습니다.</p>
            </article>
            <article>
              <h3>근거 보존</h3>
              <p>요청, 견적, 검토, 승인과 보고서는 연결된 기록으로 남습니다.</p>
            </article>
          </div>
        </section>
      </main>
    </PublicLayout>
  );
}
