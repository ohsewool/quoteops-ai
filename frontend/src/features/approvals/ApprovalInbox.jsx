import { useCallback, useEffect, useRef, useState } from "react";

import { ApiClientError } from "../../app/api/client.js";
import { useAuth } from "../../app/auth/AuthProvider.jsx";
import { navigate, useLocation } from "../../app/router.jsx";
import { decideApprovalRequest, getApprovalRequest, listApprovalRequests } from "./approvalApi.js";

const APPROVAL_STATUS_LABELS = {
  pending: "승인 대기",
  approved: "승인됨",
  rejected: "반려됨",
  cancelled: "취소됨"
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

const QUOTE_STATUS_LABELS = {
  draft: "초안",
  approval_pending: "승인 대기",
  approved: "승인됨",
  rejected: "반려됨"
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

function approvalErrorMessage(error) {
  if (!(error instanceof ApiClientError)) return "승인 요청을 처리하지 못했습니다. 잠시 후 다시 시도하세요.";
  if (error.code === "self_approval_prohibited") return "요청자는 자신의 승인 요청을 결정할 수 없습니다.";
  if (error.code === "approval_already_decided" || error.code === "stale_approval_request") return "이미 처리되었거나 최신 상태가 아닙니다. 목록을 새로고침하세요.";
  if (error.code === "rejection_reason_required") return "반려할 때는 사유를 입력하세요.";
  if (error.code === "permission_denied") return "이 작업을 수행할 권한이 없습니다.";
  if (error.code === "approval_request_not_found") return "승인 요청을 찾을 수 없습니다.";
  if (error.code === "network_unavailable") return "서버에 연결할 수 없습니다. 연결 상태를 확인하세요.";
  return "승인 요청을 처리하지 못했습니다. 잠시 후 다시 시도하세요.";
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

function ApprovalStatusBadge({ status }) {
  return <span className={`status-badge approval-status-${status}`}>{APPROVAL_STATUS_LABELS[status] || status}</span>;
}

function ValidationBadge({ status }) {
  return <span className={`status-badge validation-status-${status}`}>{VALIDATION_STATUS_LABELS[status] || status}</span>;
}

function RiskBadge({ risk }) {
  return <span className={`status-badge risk-level-${risk}`}>{RISK_LABELS[risk] || risk}</span>;
}

function approvalIdFromLocation(location) {
  const value = new URLSearchParams(location.split("?")[1] || "").get("approval_id");
  const approvalId = Number(value);
  return Number.isInteger(approvalId) && approvalId > 0 ? approvalId : null;
}

function ApprovalInboxList({ items, onSelect, selectedId }) {
  if (!items.length) return <p className="empty-note">처리할 승인 요청이 없습니다.</p>;
  return (
    <ol className="approval-inbox-list">
      {items.map((item) => (
        <li key={item.id}>
          <button aria-pressed={selectedId === item.id} onClick={() => onSelect(item.id)} type="button">
            <span>
              <strong>승인 요청 #{item.id}</strong>
              <small>Quote #{item.quote_id} · revision {item.quote_revision_id} · {formatDateTime(item.created_at)}</small>
            </span>
            <span><ApprovalStatusBadge status={item.status} /><RiskBadge risk={item.risk_level} /></span>
          </button>
        </li>
      ))}
    </ol>
  );
}

function ApprovalTimeline({ approval }) {
  return (
    <section className="approval-timeline" aria-labelledby="approval-timeline-title">
      <h2 id="approval-timeline-title">승인 타임라인</h2>
      <ol>
        <li><strong>승인 요청</strong><span>요청자 #{approval.requester_user_id} · Quote revision {approval.quote_revision_id}</span><time dateTime={approval.created_at}>{formatDateTime(approval.created_at)}</time></li>
        {approval.decision ? <li><strong>{approval.decision.decision === "approved" ? "승인 결정" : "반려 결정"}</strong><span>reviewer #{approval.decision.reviewer_user_id}{approval.decision.reason ? ` · ${approval.decision.reason}` : ""}</span><time dateTime={approval.decision.created_at}>{formatDateTime(approval.decision.created_at)}</time></li> : <li><strong>검토 대기</strong><span>별도 reviewer의 결정을 기다리고 있습니다.</span><time dateTime={approval.updated_at}>{formatDateTime(approval.updated_at)}</time></li>}
      </ol>
    </section>
  );
}

function DecisionControls({ approval, onDecide, saving, user }) {
  const [reason, setReason] = useState("");
  const [localError, setLocalError] = useState("");

  useEffect(() => {
    setReason("");
    setLocalError("");
  }, [approval.id, approval.version]);

  if (!canManage(user.role)) {
    return <p className="read-only-note">Viewer 권한에서는 승인 근거와 결정 이력을 조회할 수 있습니다.</p>;
  }
  if (approval.status !== "pending") return null;
  if (approval.requester_user_id === user.id) {
    return <p className="approval-own-request-note">본인이 요청한 건입니다. 별도 reviewer만 승인 또는 반려할 수 있습니다.</p>;
  }

  const decide = (target) => {
    const normalized = reason.trim();
    if (target === "reject" && !normalized) {
      setLocalError("반려 사유를 입력하세요.");
      return;
    }
    setLocalError("");
    onDecide(target, normalized || null);
  };

  return (
    <section className="approval-decision-controls" aria-labelledby="approval-decision-title">
      <div><h2 id="approval-decision-title">검토 결정</h2><p>결정은 한 번만 저장되며 저장된 pricing evidence를 변경하지 않습니다.</p></div>
      <label htmlFor="approval-decision-reason">검토 메모 / 반려 사유<textarea id="approval-decision-reason" maxLength="2000" onChange={(event) => setReason(event.target.value)} placeholder="반려 시 사유는 필수입니다." rows="4" value={reason} /></label>
      {localError ? <p className="form-error" role="alert">{localError}</p> : null}
      <div className="request-form-actions">
        <button className="button button-secondary" disabled={saving} onClick={() => decide("approve")} type="button">승인</button>
        <button className="button button-danger" disabled={saving} onClick={() => decide("reject")} type="button">반려</button>
      </div>
    </section>
  );
}

function ApprovalDetail({ approval, onDecide, saving, user }) {
  return (
    <>
      <section className="approval-detail-heading" aria-labelledby="approval-detail-title">
        <div><p className="eyebrow">Immutable approval evidence</p><h2 id="approval-detail-title">승인 요청 #{approval.id}</h2><p>Quote #{approval.quote_id} · source revision {approval.quote_revision_id}</p></div>
        <div className="approval-badge-pair"><ApprovalStatusBadge status={approval.status} /><ValidationBadge status={approval.validation_status} /><RiskBadge risk={approval.risk_level} /></div>
      </section>
      <div className="approval-summary-grid">
        <section><h3>선택 후보</h3><strong>{formatKrw(approval.candidate_total_price)}</strong><dl><div><dt>예상 이익</dt><dd>{formatKrw(approval.candidate_gross_profit)}</dd></div><div><dt>예상 마진</dt><dd>{formatPercent(approval.candidate_margin_rate)}</dd></div><div><dt>통화</dt><dd>{approval.currency}</dd></div></dl></section>
        <section><h3>근거 연결</h3><dl><div><dt>가격 점검</dt><dd>#{approval.pricing_check_id}</dd></div><div><dt>선택 후보</dt><dd>#{approval.price_candidate_id}</dd></div><div><dt>요청자</dt><dd>#{approval.requester_user_id}</dd></div><div><dt>현재 Quote</dt><dd>{QUOTE_STATUS_LABELS[approval.quote_current_status] || approval.quote_current_status}</dd></div></dl></section>
      </div>
      {approval.request_reason ? <section className="approval-reason"><h2>요청 사유</h2><p>{approval.request_reason}</p></section> : null}
      {approval.decision?.demo_self_approval_used ? <p className="approval-demo-label">데모 환경 self-approval 기록</p> : null}
      <ApprovalTimeline approval={approval} />
      <DecisionControls approval={approval} onDecide={onDecide} saving={saving} user={user} />
      <section className="approval-links"><AppLink className="button button-secondary" to={`/app/quotes/${approval.quote_id}`}>원본 견적 열기</AppLink>{approval.status === "approved" ? <AppLink className="button button-primary" to="/app/reports">리포트로 이동</AppLink> : null}</section>
    </>
  );
}

export function ApprovalInboxPage() {
  const { request, user } = useAuth();
  const location = useLocation();
  const locationApprovalId = approvalIdFromLocation(location);
  const [listState, setListState] = useState({ loading: true, error: "", items: [] });
  const [detailState, setDetailState] = useState({ loading: false, error: "", approval: null });
  const [selectedId, setSelectedId] = useState(locationApprovalId);
  const [saving, setSaving] = useState(false);
  const detailGeneration = useRef(0);

  const loadList = useCallback(async () => {
    setListState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const payload = await listApprovalRequests(request);
      setListState({ loading: false, error: "", items: payload.items });
      setSelectedId((current) => locationApprovalId || current || payload.items[0]?.id || null);
    } catch (error) {
      setListState({ loading: false, error: approvalErrorMessage(error), items: [] });
    }
  }, [locationApprovalId, request]);

  useEffect(() => { loadList(); }, [loadList]);
  useEffect(() => {
    if (locationApprovalId) setSelectedId(locationApprovalId);
  }, [locationApprovalId]);

  const loadDetail = useCallback(async () => {
    if (!selectedId) {
      setDetailState({ loading: false, error: "", approval: null });
      return;
    }
    const generation = ++detailGeneration.current;
    setDetailState({ loading: true, error: "", approval: null });
    try {
      const approval = await getApprovalRequest(request, selectedId);
      if (generation === detailGeneration.current) setDetailState({ loading: false, error: "", approval });
    } catch (error) {
      if (generation === detailGeneration.current) setDetailState({ loading: false, error: approvalErrorMessage(error), approval: null });
    }
  }, [request, selectedId]);

  useEffect(() => { loadDetail(); }, [loadDetail]);

  const selectApproval = (approvalId) => navigate(`/app/approvals?approval_id=${approvalId}`);
  const decide = async (decision, reason) => {
    if (!detailState.approval) return;
    setSaving(true);
    setDetailState((current) => ({ ...current, error: "" }));
    try {
      const updated = await decideApprovalRequest(request, detailState.approval.id, decision, {
        version: detailState.approval.version,
        reason
      });
      setDetailState({ loading: false, error: "", approval: updated });
      setListState((current) => ({
        ...current,
        items: current.items.map((item) => item.id === updated.id ? updated : item)
      }));
    } catch (error) {
      setDetailState((current) => ({ ...current, error: approvalErrorMessage(error) }));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="workspace-page approval-inbox-page" aria-labelledby="approval-inbox-title">
      <div className="page-heading-row"><div><p className="eyebrow">Human approval workflow</p><h1 data-route-heading id="approval-inbox-title" tabIndex="-1">승인</h1><p className="page-lede">저장된 Quote revision과 pricing evidence를 검토한 뒤, 별도 reviewer가 한 번만 결정을 저장합니다.</p></div></div>
      {listState.loading ? <p className="inline-state" role="status">승인 요청 목록을 불러오는 중입니다.</p> : null}
      {listState.error ? <div className="request-message request-message-error" role="alert"><p>{listState.error}</p><button className="button button-secondary" onClick={loadList} type="button">다시 시도</button></div> : null}
      {!listState.loading && !listState.error ? <section className="approval-inbox-section" aria-labelledby="approval-inbox-list-title"><div className="approval-section-heading"><div><h2 id="approval-inbox-list-title">승인함</h2><p>모든 항목은 서버에서 저장한 immutable evidence를 참조합니다.</p></div></div><ApprovalInboxList items={listState.items} onSelect={selectApproval} selectedId={selectedId} /></section> : null}
      {detailState.loading ? <p className="inline-state" role="status">승인 근거를 불러오는 중입니다.</p> : null}
      {detailState.error ? <div className="request-message request-message-error" role="alert"><p>{detailState.error}</p><button className="button button-secondary" onClick={loadDetail} type="button">다시 시도</button></div> : null}
      {detailState.approval ? <ApprovalDetail approval={detailState.approval} onDecide={decide} saving={saving} user={user} /> : null}
    </section>
  );
}
