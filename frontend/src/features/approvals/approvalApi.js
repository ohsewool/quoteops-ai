export function listApprovalRequests(request, { status } = {}) {
  const params = new URLSearchParams({ page: "1", page_size: "25" });
  if (status) params.set("status_filter", status);
  return request(`/api/approval-requests?${params}`);
}

export function getApprovalRequest(request, approvalRequestId) {
  return request(`/api/approval-requests/${approvalRequestId}`);
}

export function createApprovalRequest(request, payload) {
  return request("/api/approval-requests", { method: "POST", body: payload });
}

export function decideApprovalRequest(request, approvalRequestId, decision, payload) {
  return request(`/api/approval-requests/${approvalRequestId}/${decision}`, { method: "POST", body: payload });
}
