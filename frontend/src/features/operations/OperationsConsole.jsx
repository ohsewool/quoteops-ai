import { useCallback, useEffect, useState } from "react";

import { ApiClientError } from "../../app/api/client.js";
import { useAuth } from "../../app/auth/AuthProvider.jsx";
import {
  exportCompetitorReferencesCsv,
  getOperationsDiagnostics,
  importCompetitorReferencesCsv,
  listAuditEvents
} from "./operationsApi.js";

function operationsErrorMessage(error) {
  if (!(error instanceof ApiClientError)) return "Operations data could not be loaded.";
  if (error.code === "permission_denied") return "Your role cannot use this operations action.";
  if (error.code === "csv_import_invalid") return "The CSV schema or one of its rows is invalid. No rows were imported.";
  if (error.code === "operations_unavailable") return "Diagnostics are currently unavailable.";
  return "The operations action could not be completed.";
}

function formatDateTime(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function downloadCsv(csvText) {
  const blob = new Blob([csvText], { type: "text/csv;charset=utf-8" });
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "competitor-references-v1.csv";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export function OperationsConsole() {
  const { request, requestText } = useAuth();
  const [diagnostics, setDiagnostics] = useState(null);
  const [auditPage, setAuditPage] = useState({ items: [], total: 0 });
  const [filters, setFilters] = useState({ action: "", entity_type: "" });
  const [csvText, setCsvText] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [importState, setImportState] = useState("idle");
  const [importMessage, setImportMessage] = useState("");

  const loadAudit = useCallback(async (nextFilters = filters) => {
    const page = await listAuditEvents(request, { ...nextFilters, page: 1, page_size: 25 });
    setAuditPage(page);
  }, [filters, request]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextDiagnostics] = await Promise.all([
        getOperationsDiagnostics(request),
        loadAudit()
      ]);
      setDiagnostics(nextDiagnostics);
    } catch (loadError) {
      setError(operationsErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [loadAudit, request]);

  useEffect(() => {
    load();
  }, [load]);

  const submitAuditFilters = async (event) => {
    event.preventDefault();
    setError("");
    try {
      await loadAudit(filters);
    } catch (loadError) {
      setError(operationsErrorMessage(loadError));
    }
  };

  const importCsv = async (event) => {
    event.preventDefault();
    setImportState("saving");
    setImportMessage("");
    try {
      const result = await importCompetitorReferencesCsv(request, csvText);
      setImportState("ready");
      setImportMessage(`${result.imported_count} competitor reference rows were imported atomically.`);
      await loadAudit();
    } catch (importError) {
      setImportState("error");
      setImportMessage(operationsErrorMessage(importError));
    }
  };

  const exportCsv = async () => {
    setImportMessage("");
    try {
      downloadCsv(await exportCompetitorReferencesCsv(requestText));
      setImportState("ready");
      setImportMessage("Competitor-reference CSV export is ready.");
    } catch (exportError) {
      setImportState("error");
      setImportMessage(operationsErrorMessage(exportError));
    }
  };

  return (
    <section className="workspace-page operations-console" aria-labelledby="operations-title">
      <p className="eyebrow">Admin operations</p>
      <h1 data-route-heading id="operations-title" tabIndex="-1">Operations</h1>
      <p className="page-lede">Safe diagnostics, audit search, and the isolated competitor-reference CSV adapter. Secrets, connection strings, and raw cost exports are never shown here.</p>
      {loading ? <p className="inline-state" aria-live="polite">Loading operations state.</p> : null}
      {error ? <p className="form-error" role="alert">{error}</p> : null}

      {diagnostics ? (
        <section className="operations-section" aria-labelledby="operations-diagnostics-title">
          <div className="pricing-section-heading"><div><h2 id="operations-diagnostics-title">Safe diagnostics</h2><p>Configuration state only. No credential or database connection data is returned.</p></div></div>
          <dl className="status-list">
            <div><dt>Environment</dt><dd>{diagnostics.environment}</dd></div>
            <div><dt>Database readiness</dt><dd>{diagnostics.database_ready ? "ready" : "unavailable"}</dd></div>
            <div><dt>Schema revision</dt><dd>{diagnostics.alembic_revision || "not available"}</dd></div>
            <div><dt>Audit events</dt><dd>{diagnostics.audit_event_count.toLocaleString("ko-KR")}</dd></div>
            <div><dt>Demo mode</dt><dd>{diagnostics.demo_enabled ? "enabled" : "disabled"}</dd></div>
          </dl>
        </section>
      ) : null}

      <section className="operations-section" aria-labelledby="operations-csv-title">
        <div className="pricing-section-heading"><div><h2 id="operations-csv-title">Competitor-reference CSV</h2><p>Schema version: competitor-reference-csv-v1. Every row is validated before any row is persisted.</p></div></div>
        <form className="operations-csv-form" noValidate onSubmit={importCsv}>
          <label htmlFor="competitor-reference-csv">CSV input<textarea id="competitor-reference-csv" maxLength="200000" onChange={(event) => setCsvText(event.target.value)} placeholder="product_id,competitor_id,quantity,price_basis,reference_price,observed_at,source_note" rows="7" value={csvText} /></label>
          <div className="request-form-actions">
            <button className="button button-primary" disabled={importState === "saving" || !csvText.trim()} type="submit">{importState === "saving" ? "Importing" : "Import CSV"}</button>
            <button className="button button-secondary" onClick={exportCsv} type="button">Export CSV</button>
          </div>
        </form>
        {importMessage ? <p className={importState === "error" ? "form-error" : "inline-state"} role={importState === "error" ? "alert" : undefined}>{importMessage}</p> : null}
      </section>

      <section className="operations-section" aria-labelledby="operations-audit-title">
        <div className="pricing-section-heading"><div><h2 id="operations-audit-title">Audit search</h2><p>Searches safe event metadata only; it does not query or reveal stored secrets.</p></div></div>
        <form className="operations-audit-filters" onSubmit={submitAuditFilters}>
          <label htmlFor="audit-action-filter">Action<input id="audit-action-filter" maxLength="128" onChange={(event) => setFilters((current) => ({ ...current, action: event.target.value }))} value={filters.action} /></label>
          <label htmlFor="audit-entity-filter">Entity type<input id="audit-entity-filter" maxLength="64" onChange={(event) => setFilters((current) => ({ ...current, entity_type: event.target.value }))} value={filters.entity_type} /></label>
          <button className="button button-secondary" type="submit">Search audit</button>
        </form>
        <p className="read-only-note">{auditPage.total.toLocaleString("ko-KR")} matching events</p>
        {auditPage.items.length ? (
          <div className="request-table-wrap">
            <table className="request-table operations-audit-table">
              <thead><tr><th scope="col">Time</th><th scope="col">Action</th><th scope="col">Entity</th><th scope="col">Actor</th></tr></thead>
              <tbody>{auditPage.items.map((event) => <tr key={event.id}><td>{formatDateTime(event.created_at)}</td><td>{event.action}</td><td>{event.entity_type} #{event.entity_id}</td><td>{event.actor_username}</td></tr>)}</tbody>
            </table>
          </div>
        ) : <p className="empty-note">No audit events match the current filters.</p>}
      </section>
    </section>
  );
}
