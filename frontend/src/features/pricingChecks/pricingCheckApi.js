export function listPricingChecks(request, quoteId) {
  return request(`/api/quotes/${quoteId}/pricing-checks?page=1&page_size=25`);
}

export function getPricingCheck(request, pricingCheckId) {
  return request(`/api/pricing-checks/${pricingCheckId}`);
}

export function createPricingCheck(request, quoteId, payload) {
  return request(`/api/quotes/${quoteId}/pricing-checks`, { method: "POST", body: payload });
}
