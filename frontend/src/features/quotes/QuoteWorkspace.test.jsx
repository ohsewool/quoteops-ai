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

function line(overrides = {}) {
  return {
    id: 701,
    position: 1,
    description: "A3 flyer run",
    product_code: "a3_flyer",
    quantity: 2,
    unit_price: "100.00",
    line_total: "200.00",
    options: {},
    ...overrides
  };
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
    request_quantity: 100,
    source_request_version: 2,
    status: "draft",
    currency: "KRW",
    total_amount: "200.00",
    formula_version: "quote-line-sum-v1",
    rounding_policy_version: "krw-half-up-v1",
    notes: null,
    assignee_user_id: null,
    created_by_user_id: 2,
    version: 1,
    current_revision_number: 1,
    created_at: "2026-07-17T12:00:00Z",
    updated_at: "2026-07-17T12:00:00Z",
    lines: [line()],
    current_revision: {
      id: 1,
      quote_id: 77,
      revision_number: 1,
      quote_version: 1,
      source_request_version: 2,
      status: "draft",
      total_amount: "200.00",
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

function revisionPage(quote, revisions = []) {
  return { items: revisions, page: 1, page_size: 25, total: revisions.length };
}

describe("V2-04C quote workspace", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    global.fetch = vi.fn();
  });

  it("shows an authenticated viewer an actual empty quote state without a write action", async () => {
    const viewer = authenticate("viewer");
    global.fetch.mockImplementation((url) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(viewer));
      if (path.includes("/api/quotes?")) return Promise.resolve(jsonResponse({ items: [], page: 1, page_size: 25, total: 0 }));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/quotes");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "견적" })).toBeInTheDocument();
    expect(await screen.findByText("저장된 견적이 없습니다.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "요청에서 견적 만들기" })).not.toBeInTheDocument();
    expect(screen.getByText(/Viewer 권한에서는 견적과 revision을 조회할 수 있지만/)).toBeInTheDocument();
  });

  it("keeps a viewer on a read-only persisted quote detail", async () => {
    const viewer = authenticate("viewer");
    const quote = quoteDetail();
    global.fetch.mockImplementation((url) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(viewer));
      if (path.includes("/api/quotes/77/revisions")) return Promise.resolve(jsonResponse(revisionPage(quote, [quote.current_revision])));
      if (path.endsWith("/api/quotes/77")) return Promise.resolve(jsonResponse(quote));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/quotes/77");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "현장 전단 견적" })).toBeInTheDocument();
    expect(screen.getByText("A3 flyer run")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "라인 수정" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "견적 정보 수정" })).not.toBeInTheDocument();
  });

  it("sends the persisted version and exact money string when a manager replaces quote lines", async () => {
    const user = userEvent.setup();
    const manager = authenticate("manager");
    const initial = quoteDetail();
    const updatedLine = line({ description: "Revised flyer run", quantity: 5, unit_price: "50.10", line_total: "250.50" });
    const updatedRevision = { ...initial.current_revision, id: 2, revision_number: 2, quote_version: 2, total_amount: "250.50", line_count: 1 };
    const updated = quoteDetail({ version: 2, current_revision_number: 2, total_amount: "250.50", lines: [updatedLine], current_revision: updatedRevision, updated_at: "2026-07-17T13:00:00Z" });
    let saved = false;
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(manager));
      if (path.endsWith("/api/quotes/77/lines") && options.method === "PUT") {
        saved = true;
        return Promise.resolve(jsonResponse(updated));
      }
      if (path.includes("/api/quotes/77/revisions")) return Promise.resolve(jsonResponse(revisionPage(saved ? updated : initial, saved ? [updatedRevision, initial.current_revision] : [initial.current_revision])));
      if (path.endsWith("/api/quotes/77")) return Promise.resolve(jsonResponse(saved ? updated : initial));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/quotes/77");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "현장 전단 견적" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "라인 수정" }));
    await user.clear(screen.getByLabelText("라인 1 설명"));
    await user.type(screen.getByLabelText("라인 1 설명"), "Revised flyer run");
    await user.clear(screen.getByLabelText("라인 1 수량"));
    await user.type(screen.getByLabelText("라인 1 수량"), "5");
    await user.clear(screen.getByLabelText("라인 1 단가"));
    await user.type(screen.getByLabelText("라인 1 단가"), "50.10");
    await user.click(screen.getByRole("button", { name: "라인 저장" }));

    expect((await screen.findAllByText("250.50 KRW")).length).toBeGreaterThan(0);
    expect(await screen.findByText("revision 2")).toBeInTheDocument();
    const putCall = global.fetch.mock.calls.find(([url, options]) => String(url).endsWith("/api/quotes/77/lines") && options.method === "PUT");
    expect(JSON.parse(putCall[1].body)).toEqual({
      version: 1,
      lines: [{ description: "Revised flyer run", product_code: "a3_flyer", quantity: 5, unit_price: "50.10", options: {} }]
    });
  });

  it("sends the persisted version when a manager updates draft metadata", async () => {
    const user = userEvent.setup();
    const manager = authenticate("manager");
    const initial = quoteDetail({ notes: "Initial note" });
    const updatedRevision = { ...initial.current_revision, id: 2, revision_number: 2, quote_version: 2 };
    const updated = quoteDetail({ title: "수정된 현장 견적", notes: "Updated note", version: 2, current_revision_number: 2, current_revision: updatedRevision });
    let saved = false;
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(manager));
      if (path.endsWith("/api/quotes/77") && options.method === "PATCH") {
        saved = true;
        return Promise.resolve(jsonResponse(updated));
      }
      if (path.includes("/api/quotes/77/revisions")) return Promise.resolve(jsonResponse(revisionPage(saved ? updated : initial, saved ? [updatedRevision, initial.current_revision] : [initial.current_revision])));
      if (path.endsWith("/api/quotes/77")) return Promise.resolve(jsonResponse(saved ? updated : initial));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/quotes/77");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "현장 전단 견적" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "견적 정보 수정" }));
    await user.clear(screen.getByLabelText("견적 제목"));
    await user.type(screen.getByLabelText("견적 제목"), "수정된 현장 견적");
    await user.clear(screen.getByLabelText("메모"));
    await user.type(screen.getByLabelText("메모"), "Updated note");
    await user.click(screen.getByRole("button", { name: "정보 저장" }));

    expect(await screen.findByRole("heading", { name: "수정된 현장 견적" })).toBeInTheDocument();
    const patchCall = global.fetch.mock.calls.find(([url, options]) => String(url).endsWith("/api/quotes/77") && options.method === "PATCH");
    expect(JSON.parse(patchCall[1].body)).toEqual({ version: 1, title: "수정된 현장 견적", notes: "Updated note" });
  });

  it("keeps edited quote lines visible after a stale-version response", async () => {
    const user = userEvent.setup();
    const manager = authenticate("manager");
    const quote = quoteDetail();
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(manager));
      if (path.endsWith("/api/quotes/77/lines") && options.method === "PUT") return Promise.resolve(jsonResponse({ detail: "Quote changed", code: "stale_quote" }, 409));
      if (path.includes("/api/quotes/77/revisions")) return Promise.resolve(jsonResponse(revisionPage(quote, [quote.current_revision])));
      if (path.endsWith("/api/quotes/77")) return Promise.resolve(jsonResponse(quote));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/quotes/77");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "현장 전단 견적" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "라인 수정" }));
    await user.clear(screen.getByLabelText("라인 1 설명"));
    await user.type(screen.getByLabelText("라인 1 설명"), "My unsaved edit");
    await user.click(screen.getByRole("button", { name: "라인 저장" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("다른 변경이 먼저 저장되었습니다");
    expect(screen.getByLabelText("라인 1 설명")).toHaveValue("My unsaved edit");
  });
});
