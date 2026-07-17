import { useCallback, useEffect, useRef, useState } from "react";

import { ApiClientError } from "../../app/api/client.js";
import { useAuth } from "../../app/auth/AuthProvider.jsx";
import { navigate, useLocation } from "../../app/router.jsx";
import { listApprovalRequests } from "../approvals/approvalApi.js";
import { createHtmlReport, getHtmlReport, getHtmlReportContent, listHtmlReports } from "./reportApi.js";

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

function reportIdFromLocation(location) {
  const value = new URLSearchParams(location.split("?")[1] || "").get("report_id");
  const reportId = Number(value);
  return Number.isInteger(reportId) && reportId > 0 ? reportId : null;
}

function reportErrorMessage(error) {
  if (!(error instanceof ApiClientError)) return "리포트를 처리하지 못했습니다. 잠시 후 다시 시도하세요.";
  if (error.code === "report_source_not_approved") return "승인된 Quote revision에서만 문서를 생성할 수 있습니다.";
  if (error.code === "report_predecessor_mismatch" || error.code === "report_snapshot_mismatch") return "재생성 근거가 최신 상태와 일치하지 않습니다. 문서를 새로고침하세요.";
  if (error.code === "permission_denied") return "이 작업을 수행할 권한이 없습니다.";
  if (error.code === "html_report_not_found") return "리포트를 찾을 수 없습니다.";
  if (error.code === "network_unavailable") return "서버에 연결할 수 없습니다. 연결 상태를 확인하세요.";
  return "리포트를 처리하지 못했습니다. 잠시 후 다시 시도하세요.";
}

function ReportList({ items, onSelect, selectedId }) {
  if (!items.length) return <p className="empty-note">아직 생성된 문서가 없습니다.</p>;
  return (
    <ol className="report-list">
      {items.map((item) => (
        <li key={item.id}>
          <button aria-pressed={selectedId === item.id} onClick={() => onSelect(item.id)} type="button">
            <span><strong>{item.title}</strong><small>{item.source_quote_number} · revision {item.source_quote_revision_number} · {formatDateTime(item.created_at)}</small></span>
            <span>{item.predecessor_report_id ? `재생성 #${item.predecessor_report_id}` : "원본"}</span>
          </button>
        </li>
      ))}
    </ol>
  );
}

function ReportCreatePanel({ approvals, busy, onCreate }) {
  const [approvalId, setApprovalId] = useState("");
  const [title, setTitle] = useState("");
  const [localError, setLocalError] = useState("");

  useEffect(() => {
    if (!approvalId && approvals[0]) setApprovalId(String(approvals[0].id));
  }, [approvalId, approvals]);

  const submit = (event) => {
    event.preventDefault();
    const normalizedTitle = title.trim();
    if (!approvalId || !normalizedTitle) {
      setLocalError("승인된 Quote와 문서 제목을 선택하세요.");
      return;
    }
    setLocalError("");
    onCreate({ approval_request_id: Number(approvalId), title: normalizedTitle });
  };

  return (
    <section className="report-create-panel" aria-labelledby="report-create-title">
      <div><h2 id="report-create-title">문서 생성</h2><p>승인된 Quote revision과 결정 evidence만으로 read-only HTML artifact를 만듭니다.</p></div>
      {approvals.length ? <form onSubmit={submit}>
        <label htmlFor="report-approval-source">승인된 Quote<select id="report-approval-source" onChange={(event) => setApprovalId(event.target.value)} value={approvalId}>{approvals.map((approval) => <option key={approval.id} value={approval.id}>Quote #{approval.quote_id} · revision {approval.quote_revision_id} · {formatKrw(approval.candidate_total_price)}</option>)}</select></label>
        <label htmlFor="report-title">문서 제목<input id="report-title" maxLength="200" onChange={(event) => setTitle(event.target.value)} placeholder="고객 공유용 승인 견적" value={title} /></label>
        {localError ? <p className="form-error" role="alert">{localError}</p> : null}
        <button className="button button-primary" disabled={busy} type="submit">문서 생성</button>
      </form> : <p className="read-only-note">생성할 수 있는 승인 완료 Quote가 없습니다.</p>}
    </section>
  );
}

function ReportDetail({ content, contentError, contentLoading, onRegenerate, regenerating, report, user }) {
  const regenerationSuffix = " (재생성)";
  const nextTitle = report.title.length > 200 - regenerationSuffix.length
    ? `${report.title.slice(0, 200 - regenerationSuffix.length)}${regenerationSuffix}`
    : `${report.title}${regenerationSuffix}`;
  return (
    <>
      <section className="report-detail-heading" aria-labelledby="report-detail-title">
        <div><p className="eyebrow">Immutable approved-Quote artifact</p><h2 id="report-detail-title">{report.title}</h2><p>{report.source_quote_number} · source revision {report.source_quote_revision_number} · 생성 {formatDateTime(report.created_at)}</p></div>
        <span className="status-badge quote-status-approved">승인됨</span>
      </section>
      <div className="report-summary-grid">
        <section><h3>승인 가격 요약</h3><strong>{formatKrw(report.candidate_total_price)}</strong><dl><div><dt>집계 원가</dt><dd>{formatKrw(report.candidate_total_cost)}</dd></div><div><dt>예상 이익</dt><dd>{formatKrw(report.candidate_gross_profit)}</dd></div><div><dt>예상 마진</dt><dd>{formatPercent(report.candidate_margin_rate)}</dd></div></dl></section>
        <section><h3>근거 연결</h3><dl><div><dt>승인 요청</dt><dd>#{report.approval_request_id}</dd></div><div><dt>승인 결정</dt><dd>#{report.approval_decision_id}</dd></div><div><dt>Validation / risk</dt><dd>{report.validation_status} / {report.risk_level}</dd></div><div><dt>이전 artifact</dt><dd>{report.predecessor_report_id ? `#${report.predecessor_report_id}` : "원본"}</dd></div></dl></section>
      </div>
      <section className="report-preview" aria-labelledby="report-preview-title"><div><h2 id="report-preview-title">문서 미리보기</h2><p>승인된 견적 근거를 문서 형식으로 검토합니다.</p></div>{contentLoading ? <p className="inline-state" role="status">미리보기를 불러오는 중입니다.</p> : null}{contentError ? <p className="form-error" role="alert">{contentError}</p> : null}{content ? <iframe sandbox="" srcDoc={content} title="보고서 미리보기" /> : null}</section>
      <section className="report-lines" aria-labelledby="report-lines-title"><h2 id="report-lines-title">승인 가격 line</h2><div className="table-scroll"><table><thead><tr><th>설명</th><th>상품</th><th>수량</th><th>단가</th><th>총액</th></tr></thead><tbody>{report.lines.map((line) => <tr key={line.position}><td>{line.description}</td><td>{line.product_code}</td><td>{line.quantity}</td><td>{formatKrw(line.unit_price)}</td><td>{formatKrw(line.total_price)}</td></tr>)}</tbody></table></div></section>
      <section className="report-history" aria-labelledby="report-history-title"><h2 id="report-history-title">재생성 이력</h2><ol>{report.regeneration_history.map((item) => <li key={item.id}><strong>#{item.id} · {item.title}</strong><span>{item.predecessor_report_id ? `이전 #${item.predecessor_report_id}` : "원본"} · {formatDateTime(item.created_at)}</span></li>)}</ol></section>
      {canManage(user.role) ? <section className="report-regenerate"><div><h2>문서 재생성</h2><p>현재 artifact는 바꾸지 않고, 동일한 승인 snapshot을 가진 새 artifact를 추가합니다.</p></div><button className="button button-secondary" disabled={regenerating} onClick={() => onRegenerate({ approval_request_id: report.approval_request_id, predecessor_report_id: report.id, title: nextTitle })} type="button">재생성</button></section> : <p className="read-only-note">Viewer 권한에서는 승인된 문서와 lineage를 조회할 수 있습니다.</p>}
    </>
  );
}

export function ReportCenterPage() {
  const { request, requestText, user } = useAuth();
  const location = useLocation();
  const locationReportId = reportIdFromLocation(location);
  const [listState, setListState] = useState({ loading: true, error: "", items: [] });
  const [approvalState, setApprovalState] = useState({ loading: canManage(user.role), error: "", items: [] });
  const [detailState, setDetailState] = useState({ loading: false, error: "", report: null });
  const [contentState, setContentState] = useState({ loading: false, error: "", content: "" });
  const [selectedId, setSelectedId] = useState(locationReportId);
  const [saving, setSaving] = useState(false);
  const detailGeneration = useRef(0);

  const loadList = useCallback(async () => {
    setListState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const items = await listHtmlReports(request);
      setListState({ loading: false, error: "", items });
      setSelectedId((current) => locationReportId || current || items[0]?.id || null);
    } catch (error) {
      setListState({ loading: false, error: reportErrorMessage(error), items: [] });
    }
  }, [locationReportId, request]);

  const loadApprovals = useCallback(async () => {
    if (!canManage(user.role)) return;
    setApprovalState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const payload = await listApprovalRequests(request, { status: "approved" });
      setApprovalState({ loading: false, error: "", items: payload.items });
    } catch (error) {
      setApprovalState({ loading: false, error: reportErrorMessage(error), items: [] });
    }
  }, [request, user.role]);

  useEffect(() => { loadList(); }, [loadList]);
  useEffect(() => { loadApprovals(); }, [loadApprovals]);
  useEffect(() => { if (locationReportId) setSelectedId(locationReportId); }, [locationReportId]);

  const loadDetail = useCallback(async () => {
    if (!selectedId) {
      setDetailState({ loading: false, error: "", report: null });
      setContentState({ loading: false, error: "", content: "" });
      return;
    }
    const generation = ++detailGeneration.current;
    setDetailState({ loading: true, error: "", report: null });
    setContentState({ loading: true, error: "", content: "" });
    try {
      const report = await getHtmlReport(request, selectedId);
      if (generation !== detailGeneration.current) return;
      setDetailState({ loading: false, error: "", report });
      try {
        const content = await getHtmlReportContent(requestText, selectedId);
        if (generation === detailGeneration.current) setContentState({ loading: false, error: "", content });
      } catch (error) {
        if (generation === detailGeneration.current) setContentState({ loading: false, error: reportErrorMessage(error), content: "" });
      }
    } catch (error) {
      if (generation === detailGeneration.current) {
        setDetailState({ loading: false, error: reportErrorMessage(error), report: null });
        setContentState({ loading: false, error: "", content: "" });
      }
    }
  }, [request, requestText, selectedId]);

  useEffect(() => { loadDetail(); }, [loadDetail]);

  const selectReport = (reportId) => navigate(`/app/reports?report_id=${reportId}`);
  const create = async (payload) => {
    setSaving(true);
    setDetailState((current) => ({ ...current, error: "" }));
    try {
      const report = await createHtmlReport(request, payload);
      setListState((current) => ({ ...current, items: [report, ...current.items.filter((item) => item.id !== report.id)] }));
      await loadApprovals();
      navigate(`/app/reports?report_id=${report.id}`);
    } catch (error) {
      setDetailState((current) => ({ ...current, error: reportErrorMessage(error) }));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="workspace-page report-center-page" aria-labelledby="report-center-title">
      <div className="page-heading-row"><div><p className="eyebrow">Approved Quote artifacts</p><h1 data-route-heading id="report-center-title" tabIndex="-1">리포트</h1><p className="page-lede">승인된 Quote revision의 결정론적 pricing snapshot을 read-only HTML 문서로 보관하고 확인합니다.</p></div></div>
      {canManage(user.role) ? <>{approvalState.loading ? <p className="inline-state" role="status">승인된 Quote를 불러오는 중입니다.</p> : null}{approvalState.error ? <div className="request-message request-message-error" role="alert"><p>{approvalState.error}</p><button className="button button-secondary" onClick={loadApprovals} type="button">다시 시도</button></div> : null}{!approvalState.loading && !approvalState.error ? <ReportCreatePanel approvals={approvalState.items} busy={saving} onCreate={create} /> : null}</> : null}
      {listState.loading ? <p className="inline-state" role="status">문서 목록을 불러오는 중입니다.</p> : null}
      {listState.error ? <div className="request-message request-message-error" role="alert"><p>{listState.error}</p><button className="button button-secondary" onClick={loadList} type="button">다시 시도</button></div> : null}
      {!listState.loading && !listState.error ? <section className="report-list-section" aria-labelledby="report-list-title"><div><h2 id="report-list-title">문서 목록</h2><p>각 artifact는 생성 당시의 승인 source와 content hash를 유지합니다.</p></div><ReportList items={listState.items} onSelect={selectReport} selectedId={selectedId} /></section> : null}
      {detailState.loading ? <p className="inline-state" role="status">문서 근거를 불러오는 중입니다.</p> : null}
      {detailState.error ? <div className="request-message request-message-error" role="alert"><p>{detailState.error}</p><button className="button button-secondary" onClick={loadDetail} type="button">다시 시도</button></div> : null}
      {detailState.report ? <ReportDetail content={contentState.content} contentError={contentState.error} contentLoading={contentState.loading} onRegenerate={create} regenerating={saving} report={detailState.report} user={user} /> : null}
    </section>
  );
}
