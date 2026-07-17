export function listCustomerRequests(request, { search = "", status = "" } = {}) {
  const params = new URLSearchParams({ page: "1", page_size: "25" });
  if (search) params.set("search", search);
  if (status) params.set("status", status);
  return request(`/api/customer-requests?${params.toString()}`);
}

export function getCustomerRequest(request, customerRequestId) {
  return request(`/api/customer-requests/${customerRequestId}`);
}

export function getCustomerRequestAuditEvents(request, customerRequestId) {
  return request(`/api/customer-requests/${customerRequestId}/audit-events`);
}

export function createCustomerRequest(request, payload) {
  return request("/api/customer-requests", { method: "POST", body: payload });
}

export function updateCustomerRequest(request, customerRequestId, payload) {
  return request(`/api/customer-requests/${customerRequestId}`, { method: "PATCH", body: payload });
}

export function transitionCustomerRequest(request, customerRequestId, payload) {
  return request(`/api/customer-requests/${customerRequestId}/transitions`, { method: "POST", body: payload });
}
