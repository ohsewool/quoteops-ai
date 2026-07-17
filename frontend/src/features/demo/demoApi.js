export function listDemoRuns(request) {
  return request("/api/demo/runs");
}

export function startDemoRun(request) {
  return request("/api/demo/runs", { method: "POST", body: {} });
}

export function advanceDemoRun(request, demoRunId, version) {
  return request(`/api/demo/runs/${demoRunId}/advance`, { method: "POST", body: { version } });
}

export function resetDemoRun(request, demoRunId, version) {
  return request(`/api/demo/runs/${demoRunId}/reset`, { method: "POST", body: { version } });
}
