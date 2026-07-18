export function getOperationsDiagnostics(request) {
  return request("/api/operations/diagnostics");
}

export function listAuditEvents(request, filters = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && String(value).trim()) params.set(key, String(value).trim());
  }
  const query = params.toString();
  return request(`/api/operations/audit-events${query ? `?${query}` : ""}`);
}

export function importCompetitorReferencesCsv(request, csvText) {
  return request("/api/operations/competitor-references/import", {
    method: "POST",
    body: { schema_version: "competitor-reference-csv-v1", csv_text: csvText }
  });
}

export function exportCompetitorReferencesCsv(requestText) {
  return requestText("/api/operations/competitor-references/export");
}
