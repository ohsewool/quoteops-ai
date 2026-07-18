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

function approval(overrides = {}) {
  return {
    id: 900,
    quote_id: 77,
    quote_revision_id: 45,
    quote_version: 4,
    pricing_check_id: 501,
    price_candidate_id: 601,
    requester_user_id: 7,
    status: "pending",
    quote_current_status: "approval_pending",
    validation_status: "passed",
    risk_level: "low",
    currency: "KRW",
    candidate_total_price: "76923.08",
    candidate_gross_profit: "26923.08",
    candidate_margin_rate: "0.350000",
    request_reason: null,
    version: 1,
    created_at: "2026-07-17T12:15:00Z",
    updated_at: "2026-07-17T12:15:00Z",
    decision: null,
    ...overrides
  };
}

function listResponse(items) {
  return { items, page: 1, page_size: 25, total: items.length };
}

function quoteDetail() {
  return {
    id: 77,
    customer_request_id: 12,
    quote_number: "Q-20260717-TEST",
    title: "현장 전단 견적",
    customer_name: "Acme Print",
    contact_name: "Kim",
    request_product_code: "a3_flyer",
    request_quantity: 25,
    source_request_version: 2,
    status: "draft",
    currency: "KRW",
    total_amount: "0.00",
    formula_version: "quote-line-sum-v1",
    rounding_policy_version: "krw-half-up-v1",
    notes: null,
    assignee_user_id: null,
    created_by_user_id: 2,
    version: 4,
    current_revision_number: 4,
    created_at: "2026-07-17T12:00:00Z",
    updated_at: "2026-07-17T12:00:00Z",
    lines: [{ id: 701, position: 1, description: "A3 flyer run", product_code: "a3_flyer", quantity: 25, unit_price: "0.00", line_total: "0.00", options: {} }],
    current_revision: { id: 45, quote_id: 77, revision_number: 4, quote_version: 4, source_request_version: 2, status: "draft", total_amount: "0.00", currency: "KRW", line_count: 1, formula_version: "quote-line-sum-v1", rounding_policy_version: "krw-half-up-v1", created_by_user_id: 2, created_at: "2026-07-17T12:00:00Z" }
  };
}

function pricingCheck() {
  const selected = {
    id: 601,
    position: 2,
    strategy: "target_margin",
    margin_rate: "0.350000",
    is_selected: true,
    total_cost: "50000.00",
    total_price: "76923.08",
    estimated_gross_profit: "26923.08",
    estimated_margin_rate: "0.350000",
    notes: ["Calculated deterministically from the active V2 cost profile."],
    validation: { status: "warning", risk_level: "medium", minimum_margin_rate: "0.250000", checks: [] },
    lines: [{ id: 801, position: 1, product_code: "a3_flyer", quantity: 25, unit_price: "3076.92", total_price: "76923.08" }]
  };
  return {
    id: 501,
    quote_id: 77,
    quote_revision_id: 45,
    quote_version: 4,
    status: "needs_review",
    selected_strategy: "target_margin",
    selected_candidate_id: 601,
    selected_total_price: "76923.08",
    selected_gross_profit: "26923.08",
    selected_margin_rate: "0.350000",
    minimum_margin_rate: "0.250000",
    candidate_count: 1,
    validation_status: "warning",
    risk_level: "medium",
    currency: "KRW",
    formula_version: "quote-cost-margin-v1",
    validation_rule_version: "pricing-validation-v1",
    rounding_policy_version: "krw-half-up-v1",
    created_by_user_id: 2,
    created_at: "2026-07-17T12:05:00Z",
    total_cost: "50000.00",
    competitor_context: { included: true, reference_count: 1, average_unit_price: "10000.00", source_version: "competitor-reference-v1", earliest_observed_at: "2026-07-17T10:00:00Z", latest_observed_at: "2026-07-17T10:00:00Z" },
    candidates: [selected]
  };
}

describe("V2-06B approval inbox", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    global.fetch = vi.fn();
  });

  it("lets a separate manager decide once using the persisted approval version", async () => {
    const user = userEvent.setup();
    const manager = authenticate("manager", 2);
    const pending = approval();
    const decided = approval({
      status: "approved",
      quote_current_status: "approved",
      version: 2,
      updated_at: "2026-07-17T12:20:00Z",
      decision: { id: 901, decision: "approved", reviewer_user_id: 2, reason: "Evidence reviewed.", result_quote_revision_id: 46, demo_self_approval_used: false, created_at: "2026-07-17T12:20:00Z" }
    });
    let decisionPayload = null;
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(manager));
      if (path.includes("/api/approval-requests?") && options.method !== "POST") return Promise.resolve(jsonResponse(listResponse([pending])));
      if (path.endsWith("/api/approval-requests/900/approve") && options.method === "POST") {
        decisionPayload = JSON.parse(options.body);
        return Promise.resolve(jsonResponse(decided));
      }
      if (path.endsWith("/api/approval-requests/900")) return Promise.resolve(jsonResponse(pending));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/approvals?approval_id=900");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "승인" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "승인 요청 #900" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "승인" }));

    expect(await screen.findByText(/Evidence reviewed\./)).toBeInTheDocument();
    expect(decisionPayload).toEqual({ version: 1, reason: null });
    expect(screen.queryByRole("button", { name: "승인" })).not.toBeInTheDocument();
  });

  it("keeps viewers on a safe read-only approval detail", async () => {
    const viewer = authenticate("viewer", 3);
    const pending = approval();
    global.fetch.mockImplementation((url) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(viewer));
      if (path.includes("/api/approval-requests?")) return Promise.resolve(jsonResponse(listResponse([pending])));
      if (path.endsWith("/api/approval-requests/900")) return Promise.resolve(jsonResponse(pending));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/approvals?approval_id=900");

    render(<App />);

    expect(await screen.findByText(/Viewer 권한에서는 승인 근거/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "승인" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "반려" })).not.toBeInTheDocument();
    expect(screen.queryByText(/material_cost|labor_cost|overhead_cost|cost_profile_id/i)).not.toBeInTheDocument();
  });

  it("submits a warning pricing check with explicit reason and opens its approval detail", async () => {
    const user = userEvent.setup();
    const manager = authenticate("manager", 2);
    const quote = quoteDetail();
    const check = pricingCheck();
    const created = approval({
      requester_user_id: 2,
      validation_status: "warning",
      risk_level: "medium",
      request_reason: "현장 서비스 범위를 반영한 검토가 필요합니다."
    });
    let submittedPayload = null;
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(manager));
      if (path.includes("/api/quotes?") && !path.includes("pricing-checks")) return Promise.resolve(jsonResponse(listResponse([quote])));
      if (path.endsWith("/api/quotes/77")) return Promise.resolve(jsonResponse(quote));
      if (path.includes("/api/quotes/77/pricing-checks")) return Promise.resolve(jsonResponse(listResponse([check])));
      if (path.endsWith("/api/pricing-checks/501")) return Promise.resolve(jsonResponse(check));
      if (path.endsWith("/api/approval-requests") && options.method === "POST") {
        submittedPayload = JSON.parse(options.body);
        return Promise.resolve(jsonResponse(created, 201));
      }
      if (path.includes("/api/approval-requests?")) return Promise.resolve(jsonResponse(listResponse([created])));
      if (path.endsWith("/api/approval-requests/900")) return Promise.resolve(jsonResponse(created));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/pricing?quote_id=77");

    render(<App />);

    expect(await screen.findByRole("button", { name: "승인 요청 제출" })).toBeInTheDocument();
    await user.type(screen.getByLabelText(/검토 사유/), "현장 서비스 범위를 반영한 검토가 필요합니다.");
    await user.click(screen.getByRole("button", { name: "승인 요청 제출" }));

    expect(await screen.findByRole("heading", { name: "승인 요청 #900" })).toBeInTheDocument();
    expect(submittedPayload).toEqual({
      quote_id: 77,
      pricing_check_id: 501,
      price_candidate_id: 601,
      reason: "현장 서비스 범위를 반영한 검토가 필요합니다."
    });
  });
});
