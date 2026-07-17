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

function requestItem(overrides = {}) {
  return {
    id: 12,
    customer_name: "Acme Print",
    contact_name: "Kim",
    product_code: "a3_flyer",
    quantity: 100,
    due_date: "2026-08-20",
    notes: "Actual customer request note.",
    status: "new",
    assignee_user_id: null,
    created_by_user_id: 2,
    version: 1,
    reviewed_at: null,
    created_at: "2026-07-17T10:00:00Z",
    updated_at: "2026-07-17T10:00:00Z",
    ready_for_quote_conversion: false,
    allowed_transitions: ["reviewing", "cancelled"],
    ...overrides
  };
}

describe("V2-03B customer-request workspace", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    global.fetch = vi.fn();
  });

  it("shows an authenticated viewer the actual empty request state without a write action", async () => {
    const viewer = authenticate("viewer");
    global.fetch
      .mockResolvedValueOnce(jsonResponse(viewer))
      .mockResolvedValueOnce(jsonResponse({ items: [], page: 1, page_size: 25, total: 0 }));
    setRoute("/app/requests");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "고객 요청" })).toBeInTheDocument();
    expect(await screen.findByText("저장된 고객 요청이 없습니다.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "새 고객 요청" })).not.toBeInTheDocument();
    expect(screen.getByText(/Viewer 권한에서는 고객 요청을 조회할 수 있지만/)).toBeInTheDocument();
  });

  it("creates a manager request through the API and opens the persisted detail route", async () => {
    const user = userEvent.setup();
    const manager = authenticate("manager");
    const created = requestItem({ id: 15, customer_name: "Build Co", quantity: 50 });
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(manager));
      if (path.endsWith("/api/customer-requests") && options.method === "POST") return Promise.resolve(jsonResponse(created, 201));
      if (path.endsWith("/api/customer-requests/15")) return Promise.resolve(jsonResponse(created));
      if (path.endsWith("/api/customer-requests/15/audit-events")) return Promise.resolve(jsonResponse({ items: [] }));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/requests/new");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "새 고객 요청" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("고객명"), "Build Co");
    await user.type(screen.getByLabelText("수량"), "50");
    await user.click(screen.getByRole("button", { name: "고객 요청 만들기" }));

    expect(await screen.findByRole("heading", { name: "Build Co" })).toBeInTheDocument();
    const postCall = global.fetch.mock.calls.find(([url, options]) => url.endsWith("/api/customer-requests") && options.method === "POST");
    expect(JSON.parse(postCall[1].body)).toMatchObject({ customer_name: "Build Co", product_code: "a3_flyer", quantity: 50 });
    expect(window.location.pathname).toBe("/app/requests/15");
  });

  it("shows quote conversion as a V2-04 dependency and only sends an allowed transition", async () => {
    const user = userEvent.setup();
    const manager = authenticate("manager");
    const reviewing = requestItem({ status: "reviewing", version: 2, reviewed_at: "2026-07-17T12:00:00Z", ready_for_quote_conversion: true, allowed_transitions: ["cancelled"] });
    const cancelled = requestItem({ status: "cancelled", version: 3, ready_for_quote_conversion: false, allowed_transitions: [] });
    let transitioned = false;
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(manager));
      if (path.endsWith("/api/customer-requests/12/transitions") && options.method === "POST") {
        transitioned = true;
        return Promise.resolve(jsonResponse(cancelled));
      }
      if (path.endsWith("/api/customer-requests/12")) return Promise.resolve(jsonResponse(transitioned ? cancelled : reviewing));
      if (path.endsWith("/api/customer-requests/12/audit-events")) return Promise.resolve(jsonResponse({ items: [] }));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/requests/12");

    render(<App />);

    expect(await screen.findByText(/견적 생성은 V2-04에서 영속 Quote와 함께 수행됩니다/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /견적/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "요청 취소" }));

    expect(await screen.findByText("취소됨")).toBeInTheDocument();
    const transitionCall = global.fetch.mock.calls.find(([url, options]) => url.endsWith("/transitions") && options.method === "POST");
    expect(JSON.parse(transitionCall[1].body)).toEqual({ version: 2, target_status: "cancelled" });
  });

  it("sends the current version when a manager saves an edit", async () => {
    const user = userEvent.setup();
    const manager = authenticate("manager");
    const initial = requestItem({ id: 13, customer_name: "Original Co" });
    const updated = requestItem({ id: 13, customer_name: "Updated Co", version: 2 });
    let saved = false;
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(manager));
      if (path.endsWith("/api/customer-requests/13") && options.method === "PATCH") {
        saved = true;
        return Promise.resolve(jsonResponse(updated));
      }
      if (path.endsWith("/api/customer-requests/13")) return Promise.resolve(jsonResponse(saved ? updated : initial));
      if (path.endsWith("/api/customer-requests/13/audit-events")) return Promise.resolve(jsonResponse({ items: [] }));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/requests/13");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Original Co" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "요청 수정" }));
    await user.clear(screen.getByLabelText("고객명"));
    await user.type(screen.getByLabelText("고객명"), "Updated Co");
    await user.click(screen.getByRole("button", { name: "변경 저장" }));

    expect(await screen.findByRole("heading", { name: "Updated Co" })).toBeInTheDocument();
    const patchCall = global.fetch.mock.calls.find(([url, options]) => url.endsWith("/api/customer-requests/13") && options.method === "PATCH");
    expect(JSON.parse(patchCall[1].body)).toMatchObject({ customer_name: "Updated Co", version: 1 });
  });
});
