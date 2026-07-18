import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.jsx";
import { authStorageKey } from "./app/auth/AuthProvider.jsx";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" }
  });
}

function setRoute(path) {
  window.history.replaceState({}, "", path);
}

describe("V2-02A public landing and session behavior", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    setRoute("/");
    global.fetch = vi.fn();
  });

  it("explains the real product workflow without fabricating business data", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "QuoteOps AI" })).toBeInTheDocument();
    expect(screen.getByText("초기 지원 제품: A3 Flyer, Product / Brand Sticker")).toBeInTheDocument();
    expect(screen.getByText("AI가 가격이나 승인 상태를 바꾸지 않습니다.")).toBeInTheDocument();
    expect(screen.queryByText(/customer total/i)).not.toBeInTheDocument();
  });

  it("redirects an anonymous protected-route visit to login", async () => {
    setRoute("/app");
    render(<App />);

    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    expect(screen.getByRole("heading", { name: "업무 공간 로그인" })).toBeInTheDocument();
  });

  it("shows a safe login failure without echoing the password", async () => {
    const user = userEvent.setup();
    global.fetch.mockResolvedValueOnce(jsonResponse({ detail: "Invalid username or password", code: "invalid_credentials" }, 401));
    setRoute("/login");
    render(<App />);

    await user.type(screen.getByLabelText("아이디"), "viewer");
    await user.type(screen.getByLabelText("비밀번호"), "private-value");
    await user.click(screen.getByRole("button", { name: "로그인" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("아이디 또는 비밀번호를 확인하세요.");
    expect(screen.queryByText("private-value")).not.toBeInTheDocument();
  });

  it("keeps a successful login transition authenticated through protected navigation", async () => {
    const user = userEvent.setup();
    global.fetch.mockImplementation((url) => {
      const path = String(url);
      if (path.includes("/api/auth/login")) {
        return Promise.resolve(jsonResponse({ access_token: "new-session-token", expires_at: "2099-01-01T00:00:00Z" }));
      }
      if (path.includes("/api/auth/me")) {
        return Promise.resolve(jsonResponse({ id: 2, username: "manager", display_name: "Manager", role: "manager", active: true }));
      }
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/login?next=%2Fapp");
    render(<App />);

    await user.type(document.querySelector("#username"), "manager");
    await user.type(document.querySelector("#password"), "test-password");
    await user.click(document.querySelector("button[type=submit]"));

    await waitFor(() => expect(document.querySelector("#dashboard-title")).not.toBeNull());
    expect(window.location.pathname).toBe("/app");
    expect(window.location.search).toBe("");
    expect(window.sessionStorage.getItem(authStorageKey)).toContain("new-session-token");
  });

  it("restores a valid session before exposing the protected workspace", async () => {
    window.sessionStorage.setItem(authStorageKey, JSON.stringify({ accessToken: "session-token", expiresAt: "2099-01-01T00:00:00Z" }));
    global.fetch.mockResolvedValueOnce(jsonResponse({ id: 7, username: "viewer", display_name: "Viewer", role: "viewer", active: true }));
    setRoute("/app");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "대시보드" })).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining("/api/auth/me"), expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer session-token" }) }));
  });

  it("clears an expired session and redirects safely", async () => {
    window.sessionStorage.setItem(authStorageKey, JSON.stringify({ accessToken: "expired-token", expiresAt: "2000-01-01T00:00:00Z" }));
    global.fetch.mockResolvedValueOnce(jsonResponse({ detail: "Authentication is invalid", code: "invalid_access_token" }, 401));
    setRoute("/app");
    render(<App />);

    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    expect(window.sessionStorage.getItem(authStorageKey)).toBeNull();
  });

  it("shows role-aware navigation and keeps admin operations hidden from viewers", async () => {
    window.sessionStorage.setItem(authStorageKey, JSON.stringify({ accessToken: "viewer-token", expiresAt: "2099-01-01T00:00:00Z" }));
    global.fetch.mockResolvedValueOnce(jsonResponse({ id: 7, username: "viewer", display_name: "Viewer", role: "viewer", active: true }));
    setRoute("/app/dashboard");
    render(<App />);

    expect(await screen.findByRole("navigation", { name: "업무 공간 탐색" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /고객 요청/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /운영/ })).not.toBeInTheDocument();
    expect(screen.getByText("본문으로 건너뛰기")).toBeInTheDocument();
  });

  it("loads safe operations status only for an admin deep link", async () => {
    window.sessionStorage.setItem(authStorageKey, JSON.stringify({ accessToken: "admin-token", expiresAt: "2099-01-01T00:00:00Z" }));
    global.fetch.mockImplementation((url) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse({ id: 1, username: "admin", display_name: "Admin", role: "admin", active: true }));
      if (path.includes("/api/operations/diagnostics")) return Promise.resolve(jsonResponse({ environment: "local", database_configured: true, docs_enabled: true, openapi_enabled: true, demo_enabled: false, cors_origin_count: 1, database_ready: true, alembic_revision: "0009_operations_demo_domain", audit_event_count: 3 }));
      if (path.includes("/api/operations/audit-events")) return Promise.resolve(jsonResponse({ items: [], page: 1, page_size: 25, total: 0 }));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/operations");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Operations" })).toBeInTheDocument();
    expect(await screen.findByText("ready")).toBeInTheDocument();
    expect(screen.queryByText(/postgresql\+psycopg/i)).not.toBeInTheDocument();
  });

  it("opens the actual API-backed quote workspace for a stable deep link", async () => {
    window.sessionStorage.setItem(authStorageKey, JSON.stringify({ accessToken: "manager-token", expiresAt: "2099-01-01T00:00:00Z" }));
    global.fetch.mockImplementation((url) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse({ id: 2, username: "manager", display_name: "Manager", role: "manager", active: true }));
      if (path.includes("/api/quotes?")) return Promise.resolve(jsonResponse({ items: [], page: 1, page_size: 25, total: 0 }));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });
    setRoute("/app/quotes");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "견적" })).toBeInTheDocument();
    expect(await screen.findByText("저장된 견적이 없습니다.")).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining("/api/quotes?"), expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer manager-token" }) }));
  });
});
