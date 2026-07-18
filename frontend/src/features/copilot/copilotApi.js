export function createCopilotOutput(request, quoteId, payload) {
  return request(`/api/quotes/${quoteId}/copilot-outputs`, { method: "POST", body: payload });
}

export function getCopilotOutput(request, outputId) {
  return request(`/api/copilot-outputs/${outputId}`);
}
