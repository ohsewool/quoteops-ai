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

function authenticate(role = "viewer") {
  window.sessionStorage.setItem(authStorageKey, JSON.stringify({ accessToken: `${role}-token`, expiresAt: "2099-01-01T00:00:00Z" }));
  return { id: role === "manager" ? 2 : 3, username: role, display_name: role === "manager" ? "Manager" : "Viewer", role, active: true };
}

function quoteDetail(overrides = {}) {
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
    current_revision: {
      id: 45,
      quote_id: 77,
      revision_number: 4,
      quote_version: 4,
      source_request_version: 2,
      status: "draft",
      total_amount: "0.00",
      currency: "KRW",
      line_count: 1,
      formula_version: "quote-line-sum-v1",
      rounding_policy_version: "krw-half-up-v1",
      created_by_user_id: 2,
      created_at: "2026-07-17T12:00:00Z"
    },
    ...overrides
  };
}

function summary(overrides = {}) {
  return {
    id: 501,
    quote_id: 77,
    quote_revision_id: 45,
    quote_version: 4,
    status: "ready",
    selected_strategy: "target_margin",
    selected_candidate_id: 601,
    selected_total_price: "76923.08",
    selected_gross_profit: "26923.08",
    selected_margin_rate: "0.350000",
    minimum_margin_rate: "0.350000",
    candidate_count: 3,
    validation_status: "passed",
    risk_level: "low",
    currency: "KRW",
    formula_version: "quote-cost-margin-v1",
    validation_rule_version: "pricing-validation-v1",
    rounding_policy_version: "krw-half-up-v1",
    created_by_user_id: 2,
    created_at: "2026-07-17T12:05:00Z",
    ...overrides
  };
}

function pricingCheck(overrides = {}) {
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
    validation: {
      status: "passed",
      risk_level: "low",
      minimum_margin_rate: "0.350000",
      checks: [
        { code: "price_above_cost", severity: "error", passed: true, message: "Candidate price must be greater than total cost." },
        { code: "minimum_margin", severity: "error", passed: true, message: "Candidate margin must meet the active cost profile minimum." },
        { code: "market_floor", severity: "warning", passed: true, message: "Market floor was evaluated." },
        { code: "market_ceiling", severity: "warning", passed: true, message: "Market ceiling was evaluated." }
      ]
    },
    lines: [{ id: 801, position: 1, product_code: "a3_flyer", quantity: 25, unit_price: "3076.92", total_price: "76923.08" }]
  };
  const low = { ...selected, id: 600, position: 1, strategy: "low_margin", margin_rate: "0.250000", is_selected: false, total_price: "66666.67", estimated_gross_profit: "16666.67", estimated_margin_rate: "0.250000", validation: { ...selected.validation, status: "failed", risk_level: "high" } };
  const premium = { ...selected, id: 602, position: 3, strategy: "premium_margin", margin_rate: "0.450000", is_selected: false, total_price: "90909.09", estimated_gross_profit: "40909.09", estimated_margin_rate: "0.450000" };
  return {
    ...summary(),
    total_cost: "50000.00",
    competitor_context: {
      included: true,
      reference_count: 2,
      average_unit_price: "3000.00",
      source_version: "competitor-reference-v1",
      earliest_observed_at: "2026-07-10T00:00:00Z",
      latest_observed_at: "2026-07-17T00:00:00Z"
    },
    candidates: [low, selected, premium],
    ...overrides
  };
}

function listResponse(items) {
  return { items, page: 1, page_size: 25, total: items.length };
}

describe("V2-05B pricing check workspace", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    global.fetch = vi.fn();
  });

  it("renders a viewer-safe persisted pricing snapshot without a creation action", async () => {
    const viewer = authenticate("viewer");
    const quote = quoteDetail();
    const check = pricingCheck();
    global.fetch.mockImplementation((url) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(viewer));
      if (path.includes("/api/quotes?") && !path.includes("pricing-checks")) return Promise.resolve(jsonResponse(listResponse([quote])));
      if (path.includes("/api/quotes/77/pricing-checks")) return Promise.resolve(jsonResponse(listResponse([summary()])));
      if (path.includes("/api/pricing-checks/501")) return Promise.resolve(jsonResponse(check));
      if (path.endsWith("/api/quotes/77")) return Promise.resolve(jsonResponse(quote));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/pricing?quote_id=77");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "가격 검토" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "가격 점검 #501" })).toBeInTheDocument();
    expect(screen.getByText("후보 비교")).toBeInTheDocument();
    expect(screen.getByText("선택 후보 검증")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "가격 점검 생성" })).not.toBeInTheDocument();
    expect(screen.getByText(/Viewer 권한에서는 저장된 가격 점검 결과/)).toBeInTheDocument();
    expect(screen.queryByText(/material_cost|labor_cost|overhead_cost|cost_profile_id/i)).not.toBeInTheDocument();
  });

  it("sends the stored quote revision and selected deterministic options when a manager creates a check", async () => {
    const user = userEvent.setup();
    const manager = authenticate("manager");
    const quote = quoteDetail();
    const created = pricingCheck({ ...summary({ id: 502, selected_candidate_id: 701, created_at: "2026-07-17T12:06:00Z" }), id: 502, selected_candidate_id: 701 });
    let createdRequest = null;
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(manager));
      if (path.includes("/api/quotes?") && !path.includes("pricing-checks")) return Promise.resolve(jsonResponse(listResponse([quote])));
      if (path.endsWith("/api/quotes/77/pricing-checks") && options.method === "POST") {
        createdRequest = JSON.parse(options.body);
        return Promise.resolve(jsonResponse(created, 201));
      }
      if (path.includes("/api/quotes/77/pricing-checks")) return Promise.resolve(jsonResponse(listResponse([])));
      if (path.includes("/api/pricing-checks/502")) return Promise.resolve(jsonResponse(created));
      if (path.endsWith("/api/quotes/77")) return Promise.resolve(jsonResponse(quote));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/pricing?quote_id=77");

    render(<App />);

    expect(await screen.findByRole("button", { name: "가격 점검 생성" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("선택 전략"), "premium_margin");
    await user.click(screen.getByLabelText("경쟁사 참고 포함"));
    await user.click(screen.getByRole("button", { name: "가격 점검 생성" }));

    expect(await screen.findByRole("heading", { name: "가격 점검 #502" })).toBeInTheDocument();
    expect(createdRequest).toEqual({
      quote_version: 4,
      quote_revision_id: 45,
      selected_strategy: "premium_margin",
      include_competitor_context: false
    });
  });

  it("offers a real saved quote selector when the pricing route has no quote query", async () => {
    const manager = authenticate("manager");
    const quote = quoteDetail();
    global.fetch.mockImplementation((url) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(manager));
      if (path.includes("/api/quotes?")) return Promise.resolve(jsonResponse(listResponse([quote])));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/pricing");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "가격 검토" })).toBeInTheDocument();
    expect(await screen.findByRole("option", { name: /Q-20260717-TEST/ })).toBeInTheDocument();
    expect(screen.getByText("가격 검토할 견적을 선택하세요.")).toBeInTheDocument();
  });
});
