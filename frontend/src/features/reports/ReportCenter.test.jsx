import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../../App.jsx";
import { authStorageKey } from "../../app/auth/AuthProvider.jsx";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" }
  });
}

function setRoute(path) {
  window.history.replaceState({}, "", path);
}

function authenticate(role = "viewer", id = 3) {
  window.sessionStorage.setItem(authStorageKey, JSON.stringify({ accessToken: `${role}-token`, expiresAt: "2099-01-01T00:00:00Z" }));
  return { id, username: role, display_name: role === "manager" ? "Manager" : "Viewer", role, active: true };
}

function approval() {
  return {
    id: 801,
    quote_id: 77,
    quote_revision_id: 45,
    quote_version: 4,
    pricing_check_id: 501,
    price_candidate_id: 601,
    requester_user_id: 7,
    status: "approved",
    quote_current_status: "approved",
    validation_status: "passed",
    risk_level: "low",
    currency: "KRW",
    candidate_total_price: "76923.08",
    candidate_gross_profit: "26923.08",
    candidate_margin_rate: "0.35",
    request_reason: null,
    version: 2,
    created_at: "2026-07-18T12:15:00Z",
    updated_at: "2026-07-18T12:20:00Z",
    decision: { id: 901, decision: "approved", reviewer_user_id: 2, reason: "Reviewed.", result_quote_revision_id: 46, demo_self_approval_used: false, created_at: "2026-07-18T12:20:00Z" }
  };
}

function report(overrides = {}) {
  return {
    id: 900,
    report_type: "approved_quote",
    title: "고객 공유용 승인 견적",
    quote_id: 77,
    source_quote_revision_id: 46,
    source_quote_revision_number: 5,
    source_quote_status: "approved",
    source_quote_number: "Q-20260718-TEST",
    approval_request_id: 801,
    approval_decision_id: 901,
    predecessor_report_id: null,
    created_by_user_id: 2,
    currency: "KRW",
    quote_total_amount: "0.00",
    candidate_total_cost: "50000.00",
    candidate_total_price: "76923.08",
    candidate_gross_profit: "26923.08",
    candidate_margin_rate: "0.35",
    validation_status: "passed",
    risk_level: "low",
    lines: [{ position: 1, description: "A3 flyer run", product_code: "a3_flyer", quantity: 25, unit_price: "3076.92", total_price: "76923.08" }],
    summary_text: "Approved Quote Q-20260718-TEST revision 5 is grounded in saved evidence.",
    content_sha256: "f".repeat(64),
    created_at: "2026-07-18T12:25:00Z",
    regeneration_history: [{ id: 900, title: "고객 공유용 승인 견적", predecessor_report_id: null, created_by_user_id: 2, created_at: "2026-07-18T12:25:00Z" }],
    ...overrides
  };
}

function approvalList(items) {
  return { items, page: 1, page_size: 25, total: items.length };
}

describe("V2-07B report center", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    global.fetch = vi.fn();
  });

  it("lets a manager create a report from an approved source and preview it in a sandbox", async () => {
    const user = userEvent.setup();
    const manager = authenticate("manager", 2);
    const source = approval();
    const created = report();
    let createPayload = null;
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(manager));
      if (path.includes("/api/approval-requests?")) return Promise.resolve(jsonResponse(approvalList([source])));
      if (path.endsWith("/api/html-reports") && options.method === "POST") {
        createPayload = JSON.parse(options.body);
        return Promise.resolve(jsonResponse(created, 201));
      }
      if (path.endsWith("/api/html-reports/900/content")) return Promise.resolve(new Response("<html><body>safe preview</body></html>", { headers: { "content-type": "text/html" } }));
      if (path.endsWith("/api/html-reports/900")) return Promise.resolve(jsonResponse(created));
      if (path.endsWith("/api/html-reports")) return Promise.resolve(jsonResponse([]));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/reports");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "리포트" })).toBeInTheDocument();
    await user.type(await screen.findByLabelText("문서 제목"), "고객 공유용 승인 견적");
    await user.click(screen.getByRole("button", { name: "문서 생성" }));

    expect(await screen.findByRole("heading", { name: "고객 공유용 승인 견적" })).toBeInTheDocument();
    expect(createPayload).toEqual({ approval_request_id: 801, title: "고객 공유용 승인 견적" });
    const preview = await screen.findByTitle("보고서 미리보기");
    expect(preview).toHaveAttribute("sandbox", "");
    expect(preview).toHaveAttribute("srcdoc", expect.stringContaining("safe preview"));
  });

  it("creates a new immutable artifact when a manager regenerates a report", async () => {
    const user = userEvent.setup();
    const manager = authenticate("manager", 2);
    const source = approval();
    const original = report();
    const regenerated = report({
      id: 901,
      title: "고객 공유용 승인 견적 (재생성)",
      predecessor_report_id: 900,
      regeneration_history: [
        ...originalHistory(original),
        { id: 901, title: "고객 공유용 승인 견적 (재생성)", predecessor_report_id: 900, created_by_user_id: 2, created_at: "2026-07-18T12:30:00Z" }
      ]
    });
    let regenerationPayload = null;
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(manager));
      if (path.includes("/api/approval-requests?")) return Promise.resolve(jsonResponse(approvalList([source])));
      if (path.endsWith("/api/html-reports") && options.method === "POST") {
        regenerationPayload = JSON.parse(options.body);
        return Promise.resolve(jsonResponse(regenerated, 201));
      }
      if (path.endsWith("/api/html-reports/901/content")) return Promise.resolve(new Response("<html><body>regenerated</body></html>", { headers: { "content-type": "text/html" } }));
      if (path.endsWith("/api/html-reports/901")) return Promise.resolve(jsonResponse(regenerated));
      if (path.endsWith("/api/html-reports/900/content")) return Promise.resolve(new Response("<html><body>original</body></html>", { headers: { "content-type": "text/html" } }));
      if (path.endsWith("/api/html-reports/900")) return Promise.resolve(jsonResponse(original));
      if (path.endsWith("/api/html-reports")) return Promise.resolve(jsonResponse([original]));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/reports?report_id=900");

    render(<App />);

    expect(await screen.findByRole("button", { name: "재생성" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "재생성" }));

    expect(await screen.findByRole("heading", { name: "고객 공유용 승인 견적 (재생성)" })).toBeInTheDocument();
    expect(regenerationPayload).toEqual({ approval_request_id: 801, predecessor_report_id: 900, title: "고객 공유용 승인 견적 (재생성)" });
    expect(screen.getByText(/이전 #900/)).toBeInTheDocument();
  });

  it("keeps viewer report access read-only and omits raw cost component labels", async () => {
    const viewer = authenticate("viewer", 3);
    const existing = report();
    global.fetch.mockImplementation((url) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(viewer));
      if (path.endsWith("/api/html-reports/900/content")) return Promise.resolve(new Response("<html><body>safe preview</body></html>", { headers: { "content-type": "text/html" } }));
      if (path.endsWith("/api/html-reports/900")) return Promise.resolve(jsonResponse(existing));
      if (path.endsWith("/api/html-reports")) return Promise.resolve(jsonResponse([existing]));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/reports?report_id=900");

    render(<App />);

    expect(await screen.findByText(/Viewer 권한에서는 승인된 문서/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "문서 생성" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "재생성" })).not.toBeInTheDocument();
    expect(screen.queryByText(/material_cost|labor_cost|overhead_cost|cost_profile_id/i)).not.toBeInTheDocument();
  });
});

function originalHistory(sourceReport) {
  return sourceReport.regeneration_history;
}
