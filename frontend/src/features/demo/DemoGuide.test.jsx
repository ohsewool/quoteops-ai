import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, authStorageKey } from "../../app/auth/AuthProvider.jsx";
import { DemoGuide } from "./DemoGuide.jsx";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

function demoRun(overrides = {}) {
  return {
    id: 18,
    status: "ready",
    current_step: 0,
    version: 1,
    product_codes: ["a3_flyer", "brand_sticker"],
    artifacts: { created_product_ids: [1, 2], reused_product_ids: [], created_cost_profile_ids: [1, 2], customer_request_ids: [10, 11] },
    guide: { index: 0, total_steps: 6, key: "review_requests", title: "Review the two demo requests", description: "Open seeded requests.", deep_link: "/app/requests" },
    created_at: "2026-07-18T10:00:00Z",
    updated_at: "2026-07-18T10:00:00Z",
    ...overrides
  };
}

describe("V2-09B guided demo", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.sessionStorage.setItem(authStorageKey, JSON.stringify({ accessToken: "admin-token", expiresAt: "2099-01-01T00:00:00Z" }));
    global.fetch = vi.fn();
  });

  it("starts only through an explicit admin action and advances persisted guide state", async () => {
    const user = userEvent.setup();
    const admin = { id: 1, username: "admin", display_name: "Admin", role: "admin", active: true };
    let started = false;
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(admin));
      if (path.endsWith("/api/demo/runs") && options.method === "GET") return Promise.resolve(jsonResponse({ items: [] }));
      if (path.endsWith("/api/demo/runs") && options.method === "POST") {
        started = true;
        return Promise.resolve(jsonResponse(demoRun(), 201));
      }
      if (path.endsWith("/api/demo/runs/18/advance") && options.method === "POST") return Promise.resolve(jsonResponse(demoRun({ status: "in_progress", current_step: 1, version: 2, guide: { index: 1, total_steps: 6, key: "create_quote", title: "Create a persisted quote", description: "Use the Quote workspace.", deep_link: "/app/quotes" } })));
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });

    render(<AuthProvider><DemoGuide /></AuthProvider>);

    await user.click(await screen.findByRole("button", { name: "Start two-product demo" }));
    expect(started).toBe(true);
    expect(await screen.findByText("Step 1 of 6")).toBeInTheDocument();
    expect(screen.getByText("MVP products: a3_flyer, brand_sticker")).toBeInTheDocument();
    expect(screen.getByText("Demo requests")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Mark step complete" }));
    expect(await screen.findByText("Step 2 of 6")).toBeInTheDocument();
  });
});
