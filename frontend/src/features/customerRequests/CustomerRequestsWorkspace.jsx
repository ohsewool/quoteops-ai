import { useCallback, useEffect, useRef, useState } from "react";

import { ApiClientError } from "../../app/api/client.js";
import { useAuth } from "../../app/auth/AuthProvider.jsx";
import { navigate } from "../../app/router.jsx";
import {
  createCustomerRequest,
  getCustomerRequest,
  getCustomerRequestAuditEvents,
  listCustomerRequests,
  transitionCustomerRequest,
  updateCustomerRequest
} from "./customerRequestApi.js";

const PRODUCT_LABELS = {
  a3_flyer: "A3 Flyer",
  brand_sticker: "Product / Brand Sticker"
};

const STATUS_LABELS = {
  new: "신규",
  reviewing: "검토 중",
  quoted: "견적 연결됨",
  closed: "완료",
  cancelled: "취소됨"
};

const STATUS_ACTIONS = {
  reviewing: "검토 시작",
  closed: "완료 처리",
  cancelled: "요청 취소"
};

function canManage(role) {
  return role === "admin" || role === "manager";
}

function formatDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
}

function formatQuantity(value) {
  return Number.isFinite(value) ? value.toLocaleString("ko-KR") : "-";
}

function requestErrorMessage(error) {
  if (!(error instanceof ApiClientError)) return "요청을 처리하지 못했습니다. 잠시 후 다시 시도하세요.";
  if (error.code === "stale_customer_request") return "다른 변경이 먼저 저장되었습니다. 최신 요청을 다시 확인하세요.";
  if (error.code === "permission_denied") return "이 작업을 수행할 권한이 없습니다.";
  if (error.code === "customer_request_not_found") return "고객 요청을 찾을 수 없습니다.";
  if (error.code === "quote_conversion_required") return "견적 전환은 V2-04에서 실제 Quote와 함께 수행됩니다.";
  if (error.code === "network_unavailable") return "서버에 연결할 수 없습니다. 연결 상태를 확인하세요.";
  if (error.code === "validation_error") return "입력 값을 확인하세요.";
  return "요청을 처리하지 못했습니다. 잠시 후 다시 시도하세요.";
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
  return <span className={`status-badge status-${status}`}>{STATUS_LABELS[status] || status}</span>;
}

function RequestForm({ initialRequest, onCancel, onSave, submitting }) {
  const isEdit = Boolean(initialRequest);
  const [values, setValues] = useState(() => ({
    customerName: initialRequest?.customer_name || "",
    contactName: initialRequest?.contact_name || "",
    productCode: initialRequest?.product_code || "a3_flyer",
    quantity: String(initialRequest?.quantity || ""),
    dueDate: initialRequest?.due_date || "",
    notes: initialRequest?.notes || "",
    assigneeUserId: initialRequest?.assignee_user_id ? String(initialRequest.assignee_user_id) : ""
  }));
  const [localError, setLocalError] = useState("");

  useEffect(() => {
    setValues({
      customerName: initialRequest?.customer_name || "",
      contactName: initialRequest?.contact_name || "",
      productCode: initialRequest?.product_code || "a3_flyer",
      quantity: String(initialRequest?.quantity || ""),
      dueDate: initialRequest?.due_date || "",
      notes: initialRequest?.notes || "",
      assigneeUserId: initialRequest?.assignee_user_id ? String(initialRequest.assignee_user_id) : ""
    });
    setLocalError("");
  }, [initialRequest]);

  const setValue = (key) => (event) => setValues((current) => ({ ...current, [key]: event.target.value }));

  const submit = (event) => {
    event.preventDefault();
    const customerName = values.customerName.trim();
    const quantity = Number(values.quantity);
    const assigneeUserId = values.assigneeUserId ? Number(values.assigneeUserId) : null;
    if (!customerName || !Number.isInteger(quantity) || quantity <= 0) {
      setLocalError("고객명과 0보다 큰 수량을 입력하세요.");
      return;
    }
    if (values.assigneeUserId && (!Number.isInteger(assigneeUserId) || assigneeUserId <= 0)) {
      setLocalError("담당자 사용자 ID는 양의 정수여야 합니다.");
      return;
    }
    setLocalError("");
    onSave({
      customer_name: customerName,
      contact_name: values.contactName.trim() || null,
      product_code: values.productCode,
      quantity,
      due_date: values.dueDate || null,
      notes: values.notes.trim() || null,
      assignee_user_id: assigneeUserId
    });
  };

  return (
    <form className="request-form" noValidate onSubmit={submit}>
      <div className="request-form-grid">
        <label htmlFor="customer-name">고객명
          <input autoComplete="organization" id="customer-name" maxLength="160" onChange={setValue("customerName")} required value={values.customerName} />
        </label>
        <label htmlFor="contact-name">담당자명
          <input autoComplete="name" id="contact-name" maxLength="128" onChange={setValue("contactName")} value={values.contactName} />
        </label>
        <label htmlFor="product-code">제품
          <select id="product-code" onChange={setValue("productCode")} value={values.productCode}>
            {Object.entries(PRODUCT_LABELS).map(([code, label]) => <option key={code} value={code}>{label}</option>)}
          </select>
        </label>
        <label htmlFor="quantity">수량
          <input id="quantity" inputMode="numeric" min="1" onChange={setValue("quantity")} required step="1" type="number" value={values.quantity} />
        </label>
        <label htmlFor="due-date">희망 납기일
          <input id="due-date" onChange={setValue("dueDate")} type="date" value={values.dueDate} />
        </label>
        <label htmlFor="assignee-user-id">담당자 사용자 ID
          <input id="assignee-user-id" inputMode="numeric" min="1" onChange={setValue("assigneeUserId")} step="1" type="number" value={values.assigneeUserId} />
        </label>
      </div>
      <label className="request-notes" htmlFor="request-notes">요청 메모
        <textarea id="request-notes" maxLength="2000" onChange={setValue("notes")} rows="5" value={values.notes} />
      </label>
      {localError ? <p className="form-error" role="alert">{localError}</p> : null}
      <div className="request-form-actions">
        {onCancel ? <button className="button button-secondary" onClick={onCancel} type="button">취소</button> : null}
        <button className="button button-primary" disabled={submitting} type="submit">
          {submitting ? "저장 중" : isEdit ? "변경 저장" : "고객 요청 만들기"}
        </button>
      </div>
    </form>
  );
}

export function CustomerRequestsPage() {
  const { request, user } = useAuth();
  const [draftFilters, setDraftFilters] = useState({ search: "", status: "" });
  const [filters, setFilters] = useState({ search: "", status: "" });
  const [state, setState] = useState({ loading: true, error: "", payload: null });

  useEffect(() => {
    let active = true;
    setState({ loading: true, error: "", payload: null });
    listCustomerRequests(request, filters)
      .then((payload) => active && setState({ loading: false, error: "", payload }))
      .catch((error) => active && setState({ loading: false, error: requestErrorMessage(error), payload: null }));
    return () => { active = false; };
  }, [filters, request]);

  const applyFilters = (event) => {
    event.preventDefault();
    setFilters({ search: draftFilters.search.trim(), status: draftFilters.status });
  };
  const clearFilters = () => {
    setDraftFilters({ search: "", status: "" });
    setFilters({ search: "", status: "" });
  };
  const editable = canManage(user.role);
  const items = state.payload?.items || [];

  return (
    <section className="workspace-page requests-page" aria-labelledby="requests-title">
      <div className="page-heading-row">
        <div>
          <p className="eyebrow">Customer request workflow</p>
          <h1 data-route-heading id="requests-title" tabIndex="-1">고객 요청</h1>
          <p className="page-lede">실제 저장된 요청을 검토하고, 견적으로 전환하기 전의 정보를 관리합니다.</p>
        </div>
        {editable ? <AppLink className="button button-primary" to="/app/requests/new">새 고객 요청</AppLink> : null}
      </div>
      {!editable ? <p className="read-only-note">Viewer 권한에서는 고객 요청을 조회할 수 있지만 만들기·수정·상태 변경은 할 수 없습니다.</p> : null}
      <form className="request-filter-bar" onSubmit={applyFilters}>
        <label htmlFor="request-search">고객명 검색
          <input id="request-search" onChange={(event) => setDraftFilters((current) => ({ ...current, search: event.target.value }))} value={draftFilters.search} />
        </label>
        <label htmlFor="request-status">상태
          <select id="request-status" onChange={(event) => setDraftFilters((current) => ({ ...current, status: event.target.value }))} value={draftFilters.status}>
            <option value="">모든 상태</option>
            {Object.entries(STATUS_LABELS).map(([status, label]) => <option key={status} value={status}>{label}</option>)}
          </select>
        </label>
        <div className="request-filter-actions">
          <button className="button button-secondary" type="button" onClick={clearFilters}>초기화</button>
          <button className="button button-primary" type="submit">검색</button>
        </div>
      </form>
      {state.loading ? <p className="inline-state" role="status">고객 요청을 불러오는 중입니다.</p> : null}
      {state.error ? <div className="request-message request-message-error" role="alert"><p>{state.error}</p><button className="button button-secondary" onClick={() => setFilters({ ...filters })} type="button">다시 시도</button></div> : null}
      {!state.loading && !state.error && items.length === 0 ? (
        <div className="request-empty-state">
          <h2>저장된 고객 요청이 없습니다.</h2>
          <p>새 고객 요청이 등록되면 이 목록에 실제 상태와 제품 정보가 표시됩니다.</p>
        </div>
      ) : null}
      {!state.loading && !state.error && items.length > 0 ? (
        <div className="request-table-wrap">
          <table className="request-table">
            <thead><tr><th scope="col">고객</th><th scope="col">제품</th><th scope="col">수량</th><th scope="col">상태</th><th scope="col">희망 납기</th><th scope="col">상세</th></tr></thead>
            <tbody>{items.map((item) => (
              <tr key={item.id}>
                <td><strong>{item.customer_name}</strong>{item.contact_name ? <small>{item.contact_name}</small> : null}</td>
                <td>{PRODUCT_LABELS[item.product_code] || item.product_code}</td>
                <td>{formatQuantity(item.quantity)}</td>
                <td><StatusBadge status={item.status} /></td>
                <td>{formatDate(item.due_date)}</td>
                <td><AppLink className="text-link" to={`/app/requests/${item.id}`}>열기</AppLink></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

export function NewCustomerRequestPage() {
  const { request, user } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!canManage(user.role)) {
    return <PermissionNotice />;
  }

  const save = async (payload) => {
    setSubmitting(true);
    setError("");
    try {
      const created = await createCustomerRequest(request, payload);
      navigate(`/app/requests/${created.id}`, { replace: true });
    } catch (requestError) {
      setError(requestErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="workspace-page request-editor-page" aria-labelledby="new-request-title">
      <p className="eyebrow">Customer request workflow</p>
      <h1 data-route-heading id="new-request-title" tabIndex="-1">새 고객 요청</h1>
      <p className="page-lede">견적을 만들기 전, 고객 요청의 실제 입력값을 기록합니다.</p>
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      <RequestForm onCancel={() => navigate("/app/requests")} onSave={save} submitting={submitting} />
    </section>
  );
}

function PermissionNotice() {
  return (
    <section className="workspace-page" aria-labelledby="request-permission-title">
      <p className="eyebrow">Permission required</p>
      <h1 data-route-heading id="request-permission-title" tabIndex="-1">작성 권한이 없습니다</h1>
      <p className="page-lede">Viewer 권한은 고객 요청을 읽을 수 있지만 만들거나 변경할 수 없습니다. 서버도 동일하게 권한을 검증합니다.</p>
      <AppLink className="button button-secondary" to="/app/requests">고객 요청 목록으로</AppLink>
    </section>
  );
}

function AuditTrail({ events, warning }) {
  if (warning) return <p className="audit-warning">감사 이벤트를 지금 불러오지 못했습니다. 요청 정보는 그대로 확인할 수 있습니다.</p>;
  if (!events.length) return <p className="empty-note">표시할 감사 이벤트가 없습니다.</p>;
  return (
    <ol className="audit-trail">
      {events.map((event) => (
        <li key={event.id}>
          <strong>{event.action}</strong>
          <span>{event.actor_username}</span>
          <time dateTime={event.created_at}>{new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(event.created_at))}</time>
        </li>
      ))}
    </ol>
  );
}

export function CustomerRequestDetailPage({ customerRequestId }) {
  const { request, user } = useAuth();
  const [state, setState] = useState({ loading: true, error: "", item: null, auditEvents: [], auditWarning: false });
  const [editing, setEditing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const loadGeneration = useRef(0);
  const editable = canManage(user.role);

  const load = useCallback(async () => {
    const generation = ++loadGeneration.current;
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const item = await getCustomerRequest(request, customerRequestId);
      let auditEvents = [];
      let auditWarning = false;
      try {
        const audit = await getCustomerRequestAuditEvents(request, customerRequestId);
        auditEvents = audit.items;
      } catch {
        auditWarning = true;
      }
      if (generation !== loadGeneration.current) return;
      setState({ loading: false, error: "", item, auditEvents, auditWarning });
    } catch (error) {
      if (generation !== loadGeneration.current) return;
      setState({ loading: false, error: requestErrorMessage(error), item: null, auditEvents: [], auditWarning: false });
    }
  }, [customerRequestId, request]);

  useEffect(() => {
    load();
    return () => { loadGeneration.current += 1; };
  }, [load]);

  const saveEdit = async (payload) => {
    if (!state.item) return;
    setSubmitting(true);
    setState((current) => ({ ...current, error: "" }));
    try {
      const updated = await updateCustomerRequest(request, customerRequestId, { ...payload, version: state.item.version });
      setState((current) => ({ ...current, item: updated }));
      setEditing(false);
      await load();
    } catch (error) {
      setState((current) => ({ ...current, error: requestErrorMessage(error) }));
    } finally {
      setSubmitting(false);
    }
  };

  const transition = async (targetStatus) => {
    if (!state.item) return;
    setSubmitting(true);
    setState((current) => ({ ...current, error: "" }));
    try {
      const updated = await transitionCustomerRequest(request, customerRequestId, { version: state.item.version, target_status: targetStatus });
      setState((current) => ({ ...current, item: updated }));
      await load();
    } catch (error) {
      setState((current) => ({ ...current, error: requestErrorMessage(error) }));
    } finally {
      setSubmitting(false);
    }
  };

  if (state.loading) return <p className="inline-state" role="status">고객 요청을 불러오는 중입니다.</p>;
  if (!state.item) {
    return (
      <section className="workspace-page" aria-labelledby="request-error-title">
        <p className="eyebrow">Customer request workflow</p>
        <h1 data-route-heading id="request-error-title" tabIndex="-1">고객 요청을 열 수 없습니다</h1>
        <p className="page-lede">{state.error || "요청 정보를 불러오지 못했습니다."}</p>
        <div className="request-form-actions"><AppLink className="button button-secondary" to="/app/requests">목록으로</AppLink><button className="button button-primary" onClick={load} type="button">다시 시도</button></div>
      </section>
    );
  }

  const item = state.item;
  const availableActions = editable ? (item.allowed_transitions || []).filter((status) => STATUS_ACTIONS[status]) : [];

  return (
    <section className="workspace-page request-detail-page" aria-labelledby="request-detail-title">
      <div className="page-heading-row">
        <div>
          <p className="eyebrow">Customer request workflow</p>
          <h1 data-route-heading id="request-detail-title" tabIndex="-1">{item.customer_name}</h1>
          <p className="page-lede">고객 요청 #{item.id} · <StatusBadge status={item.status} /></p>
        </div>
        <AppLink className="button button-secondary" to="/app/requests">목록으로</AppLink>
      </div>
      {state.error ? <p className="form-error" role="alert">{state.error}</p> : null}
      {editing ? (
        <div className="request-edit-surface">
          <h2>요청 정보 수정</h2>
          <RequestForm initialRequest={item} onCancel={() => setEditing(false)} onSave={saveEdit} submitting={submitting} />
        </div>
      ) : (
        <>
          <dl className="request-detail-list">
            <div><dt>제품</dt><dd>{PRODUCT_LABELS[item.product_code] || item.product_code}</dd></div>
            <div><dt>수량</dt><dd>{formatQuantity(item.quantity)}</dd></div>
            <div><dt>담당자 사용자 ID</dt><dd>{item.assignee_user_id || "미지정"}</dd></div>
            <div><dt>희망 납기일</dt><dd>{formatDate(item.due_date)}</dd></div>
            <div><dt>요청자</dt><dd>{item.contact_name || "미입력"}</dd></div>
            <div><dt>현재 버전</dt><dd>{item.version}</dd></div>
          </dl>
          {item.notes ? <div className="request-notes-display"><h2>요청 메모</h2><p>{item.notes}</p></div> : null}
          {editable ? <div className="request-actions"><button className="button button-secondary" disabled={submitting} onClick={() => setEditing(true)} type="button">요청 수정</button>{availableActions.map((status) => <button className={status === "cancelled" ? "button button-danger" : "button button-primary"} disabled={submitting} key={status} onClick={() => transition(status)} type="button">{STATUS_ACTIONS[status]}</button>)}</div> : <p className="read-only-note">Viewer 권한에서는 이 요청을 변경할 수 없습니다.</p>}
          {item.ready_for_quote_conversion ? <p className="quote-conversion-note">견적 생성은 V2-04에서 영속 Quote와 함께 수행됩니다. 이 화면에서는 고객 요청만 관리합니다.</p> : null}
        </>
      )}
      <section className="request-audit-section" aria-labelledby="audit-title">
        <h2 id="audit-title">감사 이벤트</h2>
        <AuditTrail events={state.auditEvents} warning={state.auditWarning} />
      </section>
    </section>
  );
}
