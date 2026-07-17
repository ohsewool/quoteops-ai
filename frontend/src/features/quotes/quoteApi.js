export function listQuotes(request, { customer = "", status = "" } = {}) {
  const params = new URLSearchParams({ page: "1", page_size: "25" });
  if (customer) params.set("customer", customer);
  if (status) params.set("status", status);
  return request(`/api/quotes?${params.toString()}`);
}

export function getQuote(request, quoteId) {
  return request(`/api/quotes/${quoteId}`);
}

export function getQuoteRevisions(request, quoteId) {
  return request(`/api/quotes/${quoteId}/revisions?page=1&page_size=25`);
}

export function createQuoteFromCustomerRequest(request, customerRequestId, payload) {
  return request(`/api/customer-quote-requests/${customerRequestId}/quotes`, { method: "POST", body: payload });
}

export function updateQuote(request, quoteId, payload) {
  return request(`/api/quotes/${quoteId}`, { method: "PATCH", body: payload });
}

export function replaceQuoteLines(request, quoteId, payload) {
  return request(`/api/quotes/${quoteId}/lines`, { method: "PUT", body: payload });
}
