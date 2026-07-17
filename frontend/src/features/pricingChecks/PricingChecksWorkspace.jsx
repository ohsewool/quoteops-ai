import { useCallback, useEffect, useRef, useState } from "react";

import { ApiClientError } from "../../app/api/client.js";
import { useAuth } from "../../app/auth/AuthProvider.jsx";
import { navigate, useLocation } from "../../app/router.jsx";
import { getQuote, listQuotes } from "../quotes/quoteApi.js";
import { createPricingCheck, getPricingCheck, listPricingChecks } from "./pricingCheckApi.js";

const PRODUCT_LABELS = {
  a3_flyer: "A3 Flyer",
  brand_sticker: "Product / Brand Sticker"
};

const CHECK_STATUS_LABELS = {
  ready: "승인 제출 가능",
  needs_review: "검토 사유 필요",
  blocked: "점검 차단"
};

const VALIDATION_STATUS_LABELS = {
  passed: "통과",
  warning: "주의",
  failed: "실패"
};

const RISK_LABELS = {
  low: "낮음",
  medium: "중간",
  high: "높음"
};

const STRATEGY_LABELS = {
  low_margin: "낮은 마진",
  target_margin: "기준 마진",
  premium_margin: "프리미엄 마진"
};

function canManage(role) {
  return role === "admin" || role === "manager";
}

function formatKrw(value) {
  const [rawWhole = "0", rawFraction = "00"] = String(value || "0.00").split(".");
  const negative = rawWhole.startsWith("-");
  const whole = (negative ? rawWhole.slice(1) : rawWhole).replace(/^0+(?=\d)/, "") || "0";
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${negative ? "-" : ""}${grouped}.${rawFraction.padEnd(2, "0").slice(0, 2)} KRW`;
}

function formatPercent(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : "-";
}

function formatDateTime(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function pricingErrorMessage(error) {
  if (!(error instanceof ApiClientError)) return "가격 점검을 처리하지 못했습니다. 잠시 후 다시 시도하세요.";
  if (error.code === "active_product_not_found") return "이 견적 제품의 활성 상품 설정이 필요합니다.";
  if (error.code === "active_cost_profile_not_found") return "가격 점검 전에 활성 원가 프로필이 필요합니다.";
  if (error.code === "quote_has_no_lines") return "가격 점검을 위해 견적 라인을 먼저 저장하세요.";
  if (error.code === "mixed_quote_products_not_supported") return "현재 가격 점검은 요청 제품과 동일한 견적 라인만 지원합니다.";
  if (error.code === "stale_quote" || error.code === "stale_quote_revision") return "견적이 변경되었습니다. 최신 견적을 확인한 뒤 다시 실행하세요.";
  if (error.code === "permission_denied") return "이 작업을 수행할 권한이 없습니다.";
  if (error.code === "quote_not_found" || error.code === "pricing_check_not_found") return "요청한 가격 점검 정보를 찾을 수 없습니다.";
  if (error.code === "network_unavailable") return "서버에 연결할 수 없습니다. 연결 상태를 확인하세요.";
  return "가격 점검을 처리하지 못했습니다. 잠시 후 다시 시도하세요.";
}

function AppLink({ children, className, to }) {
  return (
    <a
      className={className}
      href={to}
      onClick={(event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        navigate(to);
      }}
    >
      {children}
    </a>
  );
}

function CheckStatusBadge({ status }) {
  return <span className={`status-badge pricing-status-${status}`}>{CHECK_STATUS_LABELS[status] || status}</span>;
}

function ValidationBadge({ status }) {
  return <span className={`status-badge validation-status-${status}`}>{VALIDATION_STATUS_LABELS[status] || status}</span>;
}

function RiskBadge({ risk }) {
  return <span className={`status-badge risk-level-${risk}`}>{RISK_LABELS[risk] || risk}</span>;
}

function quoteIdFromLocation(location) {
  const value = new URLSearchParams(location.split("?")[1] || "").get("quote_id");
  const quoteId = Number(value);
  return Number.isInteger(quoteId) && quoteId > 0 ? quoteId : null;
}

function PricingCheckForm({ quote, onCreate, saving }) {
  const [strategy, setStrategy] = useState("target_margin");
  const [includeCompetitorContext, setIncludeCompetitorContext] = useState(true);

  useEffect(() => {
    setStrategy("target_margin");
    setIncludeCompetitorContext(true);
  }, [quote?.id]);

  const submit = (event) => {
    event.preventDefault();
    onCreate({
      quote_version: quote.version,
      quote_revision_id: quote.current_revision.id,
      selected_strategy: strategy,
      include_competitor_context: includeCompetitorContext
    });
  };

  return (
    <form className="pricing-check-form" noValidate onSubmit={submit}>
      <div><h2>새 가격 점검</h2><p>revision {quote.current_revision_number}의 저장된 라인으로 후보와 검증 snapshot을 생성합니다.</p></div>
      <label htmlFor="pricing-strategy">선택 전략<select id="pricing-strategy" onChange={(event) => setStrategy(event.target.value)} value={strategy}>{Object.entries(STRATEGY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label className="pricing-context-option" htmlFor="competitor-context"><input checked={includeCompetitorContext} id="competitor-context" onChange={(event) => setIncludeCompetitorContext(event.target.checked)} type="checkbox" />경쟁사 참고 포함</label>
      <button className="button button-primary" disabled={saving} type="submit">{saving ? "점검 생성 중" : "가격 점검 생성"}</button>
    </form>
  );
}

function CandidateTable({ candidates }) {
  if (!candidates.length) return <p className="empty-note">저장된 후보가 없습니다.</p>;
  return (
    <div className="request-table-wrap pricing-candidate-table-wrap">
      <table className="request-table pricing-candidate-table">
        <thead><tr><th scope="col">전략</th><th scope="col">마진</th><th scope="col">총 원가</th><th scope="col">총 가격</th><th scope="col">총 이익</th><th scope="col">검증</th><th scope="col">위험</th></tr></thead>
        <tbody>{candidates.map((candidate) => <tr className={candidate.is_selected ? "pricing-candidate-selected" : undefined} key={candidate.id}><td><strong>{STRATEGY_LABELS[candidate.strategy] || candidate.strategy}</strong>{candidate.is_selected ? <small>선택됨</small> : null}</td><td>{formatPercent(candidate.estimated_margin_rate)}</td><td>{formatKrw(candidate.total_cost)}</td><td>{formatKrw(candidate.total_price)}</td><td>{formatKrw(candidate.estimated_gross_profit)}</td><td><ValidationBadge status={candidate.validation.status} /></td><td><RiskBadge risk={candidate.validation.risk_level} /></td></tr>)}</tbody>
      </table>
    </div>
  );
}

function ValidationList({ candidate }) {
  if (!candidate) return null;
  return (
    <section className="pricing-validation-section" aria-labelledby="pricing-validation-title">
      <div className="pricing-section-heading"><div><h2 id="pricing-validation-title">선택 후보 검증</h2><p>{STRATEGY_LABELS[candidate.strategy] || candidate.strategy} · 마진 {formatPercent(candidate.estimated_margin_rate)}</p></div><div className="pricing-badge-pair"><ValidationBadge status={candidate.validation.status} /><RiskBadge risk={candidate.validation.risk_level} /></div></div>
      <ul className="pricing-validation-list">{candidate.validation.checks.map((check) => <li key={check.code}><span className={`validation-mark ${check.passed ? "validation-passed" : "validation-failed"}`}>{check.passed ? "통과" : "확인 필요"}</span><div><strong>{check.code}</strong><p>{check.message}</p></div><span className={`validation-severity validation-severity-${check.severity}`}>{check.severity === "error" ? "차단 규칙" : "주의 규칙"}</span></li>)}</ul>
    </section>
  );
}

function PricingCheckDetail({ check }) {
  const selectedCandidate = check.candidates.find((candidate) => candidate.id === check.selected_candidate_id);
  const competitorContext = check.competitor_context;
  return (
    <>
      <section className="pricing-check-summary" aria-labelledby="pricing-summary-title">
        <div><p className="eyebrow">Immutable pricing evidence</p><h2 id="pricing-summary-title">가격 점검 #{check.id}</h2><p>Quote revision {check.quote_revision_id} · {formatDateTime(check.created_at)}</p></div>
        <div className="pricing-summary-status"><CheckStatusBadge status={check.status} /><ValidationBadge status={check.validation_status} /><RiskBadge risk={check.risk_level} /></div>
      </section>
      <div className="pricing-summary-grid"><section><h3>선택 가격</h3><strong>{formatKrw(check.selected_total_price)}</strong><dl><div><dt>총 원가</dt><dd>{formatKrw(check.total_cost)}</dd></div><div><dt>예상 이익</dt><dd>{formatKrw(check.selected_gross_profit)}</dd></div><div><dt>예상 마진</dt><dd>{formatPercent(check.selected_margin_rate)}</dd></div></dl></section><section><h3>경쟁사 context</h3><dl><div><dt>참고 포함</dt><dd>{competitorContext.included ? "포함" : "제외"}</dd></div><div><dt>참고 건수</dt><dd>{competitorContext.reference_count.toLocaleString("ko-KR")}</dd></div><div><dt>평균 단가</dt><dd>{competitorContext.average_unit_price ? formatKrw(competitorContext.average_unit_price) : "없음"}</dd></div></dl></section></div>
      <section className="pricing-candidates-section" aria-labelledby="pricing-candidates-title"><div className="pricing-section-heading"><div><h2 id="pricing-candidates-title">후보 비교</h2><p>모든 금액과 검증은 서버에서 저장된 deterministic snapshot입니다.</p></div></div><CandidateTable candidates={check.candidates} /></section>
      <ValidationList candidate={selectedCandidate} />
    </>
  );
}

export function PricingChecksPage() {
  const { request, user } = useAuth();
  const location = useLocation();
  const quoteId = quoteIdFromLocation(location);
  const [quoteListState, setQuoteListState] = useState({ loading: true, error: "", items: [] });
  const [quoteState, setQuoteState] = useState({ loading: false, error: "", quote: null, checks: [] });
  const [checkState, setCheckState] = useState({ loading: false, error: "", check: null });
  const [selectedCheckId, setSelectedCheckId] = useState(null);
  const [saving, setSaving] = useState(false);
  const loadGeneration = useRef(0);
  const detailGeneration = useRef(0);
  const loadedQuoteId = useRef(null);
  const manager = canManage(user.role);

  const loadQuoteList = useCallback(async () => {
    setQuoteListState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const payload = await listQuotes(request);
      setQuoteListState({ loading: false, error: "", items: payload.items });
    } catch (error) {
      setQuoteListState({ loading: false, error: pricingErrorMessage(error), items: [] });
    }
  }, [request]);

  const loadQuote = useCallback(async () => {
    if (!quoteId) {
      loadedQuoteId.current = null;
      setQuoteState({ loading: false, error: "", quote: null, checks: [] });
      setSelectedCheckId(null);
      setCheckState({ loading: false, error: "", check: null });
      return;
    }
    if (loadedQuoteId.current !== quoteId) {
      loadedQuoteId.current = quoteId;
      setSelectedCheckId(null);
      setCheckState({ loading: false, error: "", check: null });
    }
    const generation = ++loadGeneration.current;
    setQuoteState({ loading: true, error: "", quote: null, checks: [] });
    try {
      const [quote, checkPage] = await Promise.all([getQuote(request, quoteId), listPricingChecks(request, quoteId)]);
      if (generation !== loadGeneration.current) return;
      setQuoteState({ loading: false, error: "", quote, checks: checkPage.items });
      setSelectedCheckId((current) => current || checkPage.items[0]?.id || null);
    } catch (error) {
      if (generation !== loadGeneration.current) return;
      setQuoteState({ loading: false, error: pricingErrorMessage(error), quote: null, checks: [] });
      setSelectedCheckId(null);
    }
  }, [quoteId, request]);

  useEffect(() => { loadQuoteList(); }, [loadQuoteList]);
  useEffect(() => { loadQuote(); }, [loadQuote]);

  const loadCheck = useCallback((pricingCheckId) => {
    if (!pricingCheckId) {
      setCheckState({ loading: false, error: "", check: null });
      return;
    }
    const generation = ++detailGeneration.current;
    setCheckState({ loading: true, error: "", check: null });
    getPricingCheck(request, pricingCheckId)
      .then((check) => generation === detailGeneration.current && setCheckState({ loading: false, error: "", check }))
      .catch((error) => generation === detailGeneration.current && setCheckState({ loading: false, error: pricingErrorMessage(error), check: null }));
  }, [request]);

  useEffect(() => { loadCheck(selectedCheckId); }, [loadCheck, selectedCheckId]);

  const selectQuote = (event) => {
    const nextQuoteId = Number(event.target.value);
    if (Number.isInteger(nextQuoteId) && nextQuoteId > 0) navigate(`/app/pricing?quote_id=${nextQuoteId}`);
  };

  const create = async (payload) => {
    if (!quoteState.quote) return;
    setSaving(true);
    setQuoteState((current) => ({ ...current, error: "" }));
    try {
      const check = await createPricingCheck(request, quoteState.quote.id, payload);
      setQuoteState((current) => ({ ...current, checks: [
        {
          id: check.id,
          quote_id: check.quote_id,
          quote_revision_id: check.quote_revision_id,
          quote_version: check.quote_version,
          status: check.status,
          selected_strategy: check.selected_strategy,
          selected_candidate_id: check.selected_candidate_id,
          selected_total_price: check.selected_total_price,
          selected_gross_profit: check.selected_gross_profit,
          selected_margin_rate: check.selected_margin_rate,
          minimum_margin_rate: check.minimum_margin_rate,
          candidate_count: check.candidate_count,
          validation_status: check.validation_status,
          risk_level: check.risk_level,
          currency: check.currency,
          formula_version: check.formula_version,
          validation_rule_version: check.validation_rule_version,
          rounding_policy_version: check.rounding_policy_version,
          created_by_user_id: check.created_by_user_id,
          created_at: check.created_at
        },
        ...current.checks
      ] }));
      setCheckState({ loading: false, error: "", check });
      setSelectedCheckId(check.id);
    } catch (error) {
      setQuoteState((current) => ({ ...current, error: pricingErrorMessage(error) }));
    } finally {
      setSaving(false);
    }
  };

  const quote = quoteState.quote;
  const eligible = quote?.status === "draft" && quote.lines.length > 0;

  return (
    <section className="workspace-page pricing-checks-page" aria-labelledby="pricing-checks-title">
      <div className="page-heading-row"><div><p className="eyebrow">Deterministic pricing workspace</p><h1 data-route-heading id="pricing-checks-title" tabIndex="-1">가격 검토</h1><p className="page-lede">저장된 Quote revision을 기준으로 후보 가격과 검증 결과를 비교합니다.</p></div>{quote ? <AppLink className="button button-secondary" to={`/app/quotes/${quote.id}`}>견적으로 돌아가기</AppLink> : <AppLink className="button button-secondary" to="/app/quotes">견적 목록</AppLink>}</div>
      <label className="pricing-quote-select" htmlFor="pricing-quote">견적 선택<select disabled={quoteListState.loading} id="pricing-quote" onChange={selectQuote} value={quoteId || ""}><option value="">견적을 선택하세요</option>{quoteListState.items.map((item) => <option key={item.id} value={item.id}>{item.quote_number} · {item.title}</option>)}</select></label>
      {quoteListState.loading ? <p className="inline-state" role="status">견적 목록을 불러오는 중입니다.</p> : null}
      {quoteListState.error ? <div className="request-message request-message-error" role="alert"><p>{quoteListState.error}</p><button className="button button-secondary" onClick={loadQuoteList} type="button">다시 시도</button></div> : null}
      {!quoteId && !quoteListState.loading && !quoteListState.error ? <div className="request-empty-state"><h2>가격 검토할 견적을 선택하세요.</h2><p>저장된 견적을 선택하면 기존 점검 결과와 생성 가능한 다음 점검이 표시됩니다.</p></div> : null}
      {quoteState.loading ? <p className="inline-state" role="status">가격 점검 정보를 불러오는 중입니다.</p> : null}
      {quoteState.error ? <div className="request-message request-message-error" role="alert"><p>{quoteState.error}</p><button className="button button-secondary" onClick={loadQuote} type="button">다시 시도</button></div> : null}
      {quote ? <>
        <section className="pricing-quote-context"><div><h2>{quote.title}</h2><p>{quote.quote_number} · {PRODUCT_LABELS[quote.request_product_code] || quote.request_product_code} · revision {quote.current_revision_number}</p></div><strong>{formatKrw(quote.total_amount)}</strong></section>
        {quoteState.error ? null : manager && eligible ? <PricingCheckForm quote={quote} onCreate={create} saving={saving} /> : null}
        {quoteState.error ? null : manager && !eligible ? <div className="pricing-ineligible"><p>초안 상태에서 하나 이상의 견적 라인이 저장된 뒤 가격 점검을 생성할 수 있습니다.</p><AppLink className="button button-secondary" to={`/app/quotes/${quote.id}`}>견적 열기</AppLink></div> : null}
        {!manager ? <p className="read-only-note">Viewer 권한에서는 저장된 가격 점검 결과를 조회할 수 있습니다.</p> : null}
        <section className="pricing-history" aria-labelledby="pricing-history-title"><div className="pricing-section-heading"><div><h2 id="pricing-history-title">저장된 점검</h2><p>각 점검은 생성 당시의 Quote revision과 source context를 유지합니다.</p></div></div>{quoteState.checks.length === 0 ? <p className="empty-note">아직 저장된 가격 점검이 없습니다.</p> : <ol className="pricing-history-list">{quoteState.checks.map((item) => <li key={item.id}><button aria-pressed={selectedCheckId === item.id} onClick={() => setSelectedCheckId(item.id)} type="button"><span><strong>점검 #{item.id}</strong><small>{STRATEGY_LABELS[item.selected_strategy] || item.selected_strategy} · {formatDateTime(item.created_at)}</small></span><span><CheckStatusBadge status={item.status} /><RiskBadge risk={item.risk_level} /></span></button></li>)}</ol>}</section>
      </> : null}
      {checkState.loading ? <p className="inline-state" role="status">점검 snapshot을 불러오는 중입니다.</p> : null}
      {checkState.error ? <div className="request-message request-message-error" role="alert"><p>{checkState.error}</p><button className="button button-secondary" onClick={() => loadCheck(selectedCheckId)} type="button">다시 시도</button></div> : null}
      {checkState.check ? <PricingCheckDetail check={checkState.check} /> : null}
    </section>
  );
}
