export function listHtmlReports(request) {
  return request("/api/html-reports");
}

export function getHtmlReport(request, reportId) {
  return request(`/api/html-reports/${reportId}`);
}

export function createHtmlReport(request, payload) {
  return request("/api/html-reports", { method: "POST", body: payload });
}

export function getHtmlReportContent(requestText, reportId) {
  return requestText(`/api/html-reports/${reportId}/content`);
}
