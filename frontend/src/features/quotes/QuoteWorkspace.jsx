import { useCallback, useEffect, useRef, useState } from "react";

import { ApiClientError } from "../../app/api/client.js";
import { useAuth } from "../../app/auth/AuthProvider.jsx";
import { navigate } from "../../app/router.jsx";
import { getQuote, getQuoteRevisions, listQuotes, replaceQuoteLines, updateQuote } from "./quoteApi.js";

const PRODUCT_LABELS = {
  a3_flyer: "A3 Flyer",
  brand_sticker: "Product / Brand Sticker"
};

const STATUS_LABELS = {
  draft: "초안",
  pricing_review: "가격 점검 중",
  blocked: "점검 차단",
  approval_pending: "승인 대기",
  approved: "승인됨",
  rejected: "반려됨",
  cancelled: "취소됨"
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

function formatDateTime(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function quoteErrorMessage(error) {
  if (!(error instanceof ApiClientError)) return "견적 요청을 처리하지 못했습니다. 잠시 후 다시 시도하세요.";
  if (error.code === "stale_quote") return "다른 변경이 먼저 저장되었습니다. 현재 초안은 유지되며 최신 견적을 다시 확인하세요.";
  if (error.code === "quote_not_editable") return "현재 상태의 견적은 수정할 수 없습니다.";
  if (error.code === "permission_denied") return "이 작업을 수행할 권한이 없습니다.";
  if (error.code === "quote_not_found") return "견적을 찾을 수 없습니다.";
  if (error.code === "validation_error" || error.code === "invalid_quote_title") return "입력 값을 확인하세요.";
  if (error.code === "network_unavailable") return "서버에 연결할 수 없습니다. 연결 상태를 확인하세요.";
  return "견적 요청을 처리하지 못했습니다. 잠시 후 다시 시도하세요.";
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

function StatusBadge({ status }) {
  return <span className={`status-badge quote-status-${status}`}>{STATUS_LABELS[status] || status}</span>;
}

function cloneLine(line) {
  return {
    description: line.description || "",
    product_code: line.product_code || "a3_flyer",
    quantity: String(line.quantity ?? ""),
    unit_price: line.unit_price || "0.00",
    options: line.options || {}
  };
}

function newLine() {
  return { description: "", product_code: "a3_flyer", quantity: "1", unit_price: "0.00", options: {} };
}

function QuoteLineEditor({ lines, onChange, onCancel, onSave, saving }) {
  const [localError, setLocalError] = useState("");

  const updateLine = (index, field, value) => {
    onChange((currentLines) => currentLines.map((line, currentIndex) => currentIndex === index ? { ...line, [field]: value } : line));
  };
  const removeLine = (index) => onChange((currentLines) => currentLines.filter((_, currentIndex) => currentIndex !== index));
  const submit = (event) => {
    event.preventDefault();
    const normalized = [];
    for (const line of lines) {
      const quantity = Number(line.quantity);
      if (!line.description.trim() || !Number.isInteger(quantity) || quantity <= 0 || !/^\d+(?:\.\d+)?$/.test(String(line.unit_price).trim())) {
        setLocalError("각 라인에 설명, 양의 정수 수량, 0 이상의 가격을 입력하세요.");
        return;
      }
      normalized.push({
        description: line.description.trim(),
        product_code: line.product_code,
        quantity,
        unit_price: String(line.unit_price).trim(),
        options: line.options || {}
      });
    }
    setLocalError("");
    onSave(normalized);
  };

  return (
    <form className="quote-line-editor" noValidate onSubmit={submit}>
      <div className="quote-line-editor-head"><h2>라인 편집</h2><button className="button button-secondary" onClick={() => onChange((currentLines) => [...currentLines, newLine()])} type="button">라인 추가</button></div>
      {lines.length === 0 ? <p className="empty-note">라인이 없습니다. 라인을 추가하면 결정적 합계가 서버에서 계산됩니다.</p> : null}
      <div className="quote-line-input-list">
        {lines.map((line, index) => (
          <div className="quote-line-input-row" key={index}>
            <label>설명<input aria-label={`라인 ${index + 1} 설명`} maxLength="200" onChange={(event) => updateLine(index, "description", event.target.value)} value={line.description} /></label>
            <label>제품<select aria-label={`라인 ${index + 1} 제품`} onChange={(event) => updateLine(index, "product_code", event.target.value)} value={line.product_code}>{Object.entries(PRODUCT_LABELS).map(([code, label]) => <option key={code} value={code}>{label}</option>)}</select></label>
            <label>수량<input aria-label={`라인 ${index + 1} 수량`} inputMode="numeric" min="1" onChange={(event) => updateLine(index, "quantity", event.target.value)} step="1" type="number" value={line.quantity} /></label>
            <label>단가<input aria-label={`라인 ${index + 1} 단가`} inputMode="decimal" min="0" onChange={(event) => updateLine(index, "unit_price", event.target.value)} step="0.01" value={line.unit_price} /></label>
            <button className="button button-danger" onClick={() => removeLine(index)} type="button">삭제</button>
          </div>
        ))}
      </div>
      {localError ? <p className="form-error" role="alert">{localError}</p> : null}
      <div className="request-form-actions"><button className="button button-secondary" onClick={onCancel} type="button">취소</button><button className="button button-primary" disabled={saving} type="submit">{saving ? "저장 중" : "라인 저장"}</button></div>
    </form>
  );
}

function QuoteMetadataEditor({ quote, onCancel, onSave, saving }) {
  const [title, setTitle] = useState(quote.title);
  const [notes, setNotes] = useState(quote.notes || "");
  const [localError, setLocalError] = useState("");

  const submit = (event) => {
    event.preventDefault();
    if (!title.trim()) {
      setLocalError("견적 제목을 입력하세요.");
      return;
    }
    setLocalError("");
    onSave({ title: title.trim(), notes: notes.trim() || null });
  };

  return (
    <form className="quote-metadata-editor" noValidate onSubmit={submit}>
      <h2>견적 정보 수정</h2>
      <label htmlFor="quote-title">견적 제목<input id="quote-title" maxLength="200" onChange={(event) => setTitle(event.target.value)} value={title} /></label>
      <label htmlFor="quote-notes">메모<textarea id="quote-notes" maxLength="2000" onChange={(event) => setNotes(event.target.value)} rows="5" value={notes} /></label>
      {localError ? <p className="form-error" role="alert">{localError}</p> : null}
      <div className="request-form-actions"><button className="button button-secondary" onClick={onCancel} type="button">취소</button><button className="button button-primary" disabled={saving} type="submit">{saving ? "저장 중" : "정보 저장"}</button></div>
    </form>
  );
}

export function QuotesPage() {
  const { request, user } = useAuth();
  const [draftFilters, setDraftFilters] = useState({ customer: "", status: "" });
  const [filters, setFilters] = useState({ customer: "", status: "" });
  const [state, setState] = useState({ loading: true, error: "", payload: null });

  useEffect(() => {
    let active = true;
    setState({ loading: true, error: "", payload: null });
    listQuotes(request, filters)
      .then((payload) => active && setState({ loading: false, error: "", payload }))
      .catch((error) => active && setState({ loading: false, error: quoteErrorMessage(error), payload: null }));
    return () => { active = false; };
  }, [filters, request]);

  const applyFilters = (event) => {
    event.preventDefault();
    setFilters({ customer: draftFilters.customer.trim(), status: draftFilters.status });
  };
  const clearFilters = () => {
    setDraftFilters({ customer: "", status: "" });
    setFilters({ customer: "", status: "" });
  };
  const items = state.payload?.items || [];
  const editable = canManage(user.role);

  return (
    <section className="workspace-page quotes-page" aria-labelledby="quotes-title">
      <div className="page-heading-row"><div><p className="eyebrow">Persistent quote workspace</p><h1 data-route-heading id="quotes-title" tabIndex="-1">견적</h1><p className="page-lede">저장된 견적과 불변 revision을 검토하고, 초안일 때만 실제 라인을 수정합니다.</p></div>{editable ? <AppLink className="button button-primary" to="/app/requests">요청에서 견적 만들기</AppLink> : null}</div>
      {!editable ? <p className="read-only-note">Viewer 권한에서는 견적과 revision을 조회할 수 있지만 수정할 수 없습니다.</p> : null}
      <form className="request-filter-bar" onSubmit={applyFilters}>
        <label htmlFor="quote-customer-search">고객명 검색<input id="quote-customer-search" onChange={(event) => setDraftFilters((current) => ({ ...current, customer: event.target.value }))} value={draftFilters.customer} /></label>
        <label htmlFor="quote-status-filter">상태<select id="quote-status-filter" onChange={(event) => setDraftFilters((current) => ({ ...current, status: event.target.value }))} value={draftFilters.status}><option value="">모든 상태</option>{Object.entries(STATUS_LABELS).map(([status, label]) => <option key={status} value={status}>{label}</option>)}</select></label>
        <div className="request-filter-actions"><button className="button button-secondary" onClick={clearFilters} type="button">초기화</button><button className="button button-primary" type="submit">검색</button></div>
      </form>
      {state.loading ? <p className="inline-state" role="status">견적을 불러오는 중입니다.</p> : null}
      {state.error ? <div className="request-message request-message-error" role="alert"><p>{state.error}</p><button className="button button-secondary" onClick={() => setFilters({ ...filters })} type="button">다시 시도</button></div> : null}
      {!state.loading && !state.error && items.length === 0 ? <div className="request-empty-state"><h2>저장된 견적이 없습니다.</h2><p>검토 중인 고객 요청을 견적으로 전환하면 이 목록에 실제 견적과 상태가 나타납니다.</p></div> : null}
      {!state.loading && !state.error && items.length > 0 ? <div className="request-table-wrap"><table className="request-table quote-table"><thead><tr><th scope="col">견적</th><th scope="col">고객</th><th scope="col">상태</th><th scope="col">합계</th><th scope="col">revision</th><th scope="col">상세</th></tr></thead><tbody>{items.map((quote) => <tr key={quote.id}><td><strong>{quote.quote_number}</strong><small>{quote.title}</small></td><td>{quote.customer_name}</td><td><StatusBadge status={quote.status} /></td><td>{formatKrw(quote.total_amount)}</td><td>{quote.current_revision_number}</td><td><AppLink className="text-link" to={`/app/quotes/${quote.id}`}>열기</AppLink></td></tr>)}</tbody></table></div> : null}
    </section>
  );
}

export function QuoteDetailPage({ quoteId }) {
  const { request, user } = useAuth();
  const [state, setState] = useState({ loading: true, error: "", quote: null, revisions: [] });
  const [editingLines, setEditingLines] = useState(false);
  const [editingMetadata, setEditingMetadata] = useState(false);
  const [draftLines, setDraftLines] = useState([]);
  const [saving, setSaving] = useState(false);
  const loadGeneration = useRef(0);
  const editable = canManage(user.role);

  const load = useCallback(async () => {
    const generation = ++loadGeneration.current;
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const [quote, revisionPage] = await Promise.all([getQuote(request, quoteId), getQuoteRevisions(request, quoteId)]);
      if (generation !== loadGeneration.current) return;
      setState({ loading: false, error: "", quote, revisions: revisionPage.items });
      setDraftLines(quote.lines.map(cloneLine));
    } catch (error) {
      if (generation !== loadGeneration.current) return;
      setState({ loading: false, error: quoteErrorMessage(error), quote: null, revisions: [] });
    }
  }, [quoteId, request]);

  useEffect(() => {
    load();
    return () => { loadGeneration.current += 1; };
  }, [load]);

  const saveLines = async (lines) => {
    if (!state.quote) return;
    setSaving(true);
    setState((current) => ({ ...current, error: "" }));
    try {
      const quote = await replaceQuoteLines(request, quoteId, { version: state.quote.version, lines });
      setState((current) => ({ ...current, quote }));
      setDraftLines(quote.lines.map(cloneLine));
      setEditingLines(false);
      await load();
    } catch (error) {
      setState((current) => ({ ...current, error: quoteErrorMessage(error) }));
    } finally {
      setSaving(false);
    }
  };

  const saveMetadata = async (payload) => {
    if (!state.quote) return;
    setSaving(true);
    setState((current) => ({ ...current, error: "" }));
    try {
      const quote = await updateQuote(request, quoteId, { ...payload, version: state.quote.version });
      setState((current) => ({ ...current, quote }));
      setEditingMetadata(false);
      await load();
    } catch (error) {
      setState((current) => ({ ...current, error: quoteErrorMessage(error) }));
    } finally {
      setSaving(false);
    }
  };

  if (state.loading) return <p className="inline-state" role="status">견적을 불러오는 중입니다.</p>;
  if (!state.quote) return <section className="workspace-page" aria-labelledby="quote-error-title"><p className="eyebrow">Persistent quote workspace</p><h1 data-route-heading id="quote-error-title" tabIndex="-1">견적을 열 수 없습니다</h1><p className="page-lede">{state.error || "견적 정보를 불러오지 못했습니다."}</p><div className="request-form-actions"><AppLink className="button button-secondary" to="/app/quotes">견적 목록으로</AppLink><button className="button button-primary" onClick={load} type="button">다시 시도</button></div></section>;

  const quote = state.quote;
  const isDraft = quote.status === "draft";
  const eligibleForPricing = isDraft && quote.lines.length > 0;

  return (
    <section className="workspace-page quote-detail-page" aria-labelledby="quote-detail-title">
      <div className="page-heading-row"><div><p className="eyebrow">Persistent quote workspace</p><h1 data-route-heading id="quote-detail-title" tabIndex="-1">{quote.title}</h1><p className="page-lede">{quote.quote_number} · <StatusBadge status={quote.status} /> · revision {quote.current_revision_number}</p></div><AppLink className="button button-secondary" to="/app/quotes">목록으로</AppLink></div>
      {state.error ? <p className="form-error" role="alert">{state.error}</p> : null}
      <div className="quote-summary-grid"><section><h2>고객 요청 연결</h2><dl className="request-detail-list"><div><dt>고객</dt><dd>{quote.customer_name}</dd></div><div><dt>요청 ID</dt><dd>{quote.customer_request_id}</dd></div><div><dt>제품</dt><dd>{PRODUCT_LABELS[quote.request_product_code] || quote.request_product_code}</dd></div><div><dt>요청 수량</dt><dd>{quote.request_quantity.toLocaleString("ko-KR")}</dd></div><div><dt>요청 버전</dt><dd>{quote.source_request_version}</dd></div><div><dt>담당자 사용자 ID</dt><dd>{quote.assignee_user_id || "미지정"}</dd></div></dl></section><section className="quote-total-panel"><h2>결정적 합계</h2><strong>{formatKrw(quote.total_amount)}</strong><p>합계는 현재 저장된 라인의 수량과 단가를 서버에서 계산한 값입니다.</p><dl><div><dt>통화</dt><dd>{quote.currency}</dd></div><div><dt>수식 버전</dt><dd>{quote.formula_version}</dd></div><div><dt>반올림 정책</dt><dd>{quote.rounding_policy_version}</dd></div></dl></section></div>
      {editingMetadata ? <QuoteMetadataEditor quote={quote} onCancel={() => setEditingMetadata(false)} onSave={saveMetadata} saving={saving} /> : <div className="quote-metadata-display"><h2>견적 메모</h2><p>{quote.notes || "입력된 메모가 없습니다."}</p>{editable && isDraft ? <button className="button button-secondary" disabled={saving} onClick={() => setEditingMetadata(true)} type="button">견적 정보 수정</button> : null}</div>}
      <section className="quote-lines-section" aria-labelledby="quote-lines-title"><div className="quote-line-editor-head"><div><h2 id="quote-lines-title">견적 라인</h2><p>현재 초안 라인은 revision {quote.current_revision_number}에 스냅샷으로 보존됩니다.</p></div>{editable && isDraft && !editingLines ? <button className="button button-primary" disabled={saving} onClick={() => setEditingLines(true)} type="button">라인 수정</button> : null}</div>{editingLines ? <QuoteLineEditor lines={draftLines} onCancel={() => { setDraftLines(quote.lines.map(cloneLine)); setEditingLines(false); }} onChange={setDraftLines} onSave={saveLines} saving={saving} /> : quote.lines.length === 0 ? <p className="empty-note">아직 저장된 라인이 없습니다.</p> : <div className="request-table-wrap"><table className="request-table quote-line-table"><thead><tr><th scope="col">순서</th><th scope="col">설명</th><th scope="col">제품</th><th scope="col">수량</th><th scope="col">단가</th><th scope="col">라인 합계</th></tr></thead><tbody>{quote.lines.map((line) => <tr key={line.id}><td>{line.position}</td><td>{line.description}</td><td>{PRODUCT_LABELS[line.product_code] || line.product_code}</td><td>{line.quantity.toLocaleString("ko-KR")}</td><td>{formatKrw(line.unit_price)}</td><td>{formatKrw(line.line_total)}</td></tr>)}</tbody></table></div>}</section>
      <section className="quote-revision-section" aria-labelledby="quote-revisions-title"><h2 id="quote-revisions-title">revision 기록</h2>{state.revisions.length === 0 ? <p className="empty-note">표시할 revision이 없습니다.</p> : <ol className="quote-revision-list">{state.revisions.map((revision) => <li key={revision.id}><strong>revision {revision.revision_number}</strong><span>{STATUS_LABELS[revision.status] || revision.status}</span><span>{formatKrw(revision.total_amount)}</span><time dateTime={revision.created_at}>{formatDateTime(revision.created_at)}</time></li>)}</ol>}</section>
      <div className="quote-next-action">{eligibleForPricing ? <AppLink className="button button-primary" to={`/app/pricing?quote_id=${quote.id}`}>가격 점검으로</AppLink> : <p>가격 점검은 초안 상태에서 하나 이상의 견적 라인이 저장된 후에만 진행할 수 있습니다.</p>}</div>
    </section>
  );
}
