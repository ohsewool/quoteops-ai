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

  it("restores a valid session before exposing the protected workspace", async () => {
    window.sessionStorage.setItem(authStorageKey, JSON.stringify({ accessToken: "session-token", expiresAt: "2099-01-01T00:00:00Z" }));
    global.fetch.mockResolvedValueOnce(jsonResponse({ id: 7, username: "viewer", display_name: "Viewer", role: "viewer", active: true }));
    setRoute("/app");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Viewer님의 업무 공간" })).toBeInTheDocument();
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
});
