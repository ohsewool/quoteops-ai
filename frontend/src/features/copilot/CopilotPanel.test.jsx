import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, authStorageKey } from "../../app/auth/AuthProvider.jsx";
import { CopilotPanel } from "./CopilotPanel.jsx";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

function authenticate(role) {
  window.sessionStorage.setItem(authStorageKey, JSON.stringify({ accessToken: `${role}-token`, expiresAt: "2099-01-01T00:00:00Z" }));
  return { id: role === "manager" ? 2 : 3, username: role, display_name: role, role, active: true };
}

function renderPanel() {
  return render(
    <AuthProvider>
      <CopilotPanel
        quoteId={77}
        title="Pricing evidence copilot"
        actions={[{
          id: "candidate-explanation",
          label: "Generate candidate explanation",
          payload: { purpose: "candidate_explanation", quote_revision_id: 45, pricing_check_id: 501, price_candidate_id: 601 }
        }]}
      />
    </AuthProvider>
  );
}

describe("Grounded Copilot panel", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    global.fetch = vi.fn();
  });

  it("sends immutable source IDs for a manager and renders the returned grounded output", async () => {
    const user = userEvent.setup();
    const manager = authenticate("manager");
    let submitted = null;
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(manager));
      if (path.endsWith("/api/quotes/77/copilot-outputs") && options.method === "POST") {
        submitted = JSON.parse(options.body);
        return Promise.resolve(jsonResponse({
          id: 1,
          generated_text: "The selected candidate passed the saved validation evidence.",
          deterministic_fallback: true,
          provider_name: "disabled",
          source_artifacts: [{ artifact_type: "pricing_check", artifact_id: 501 }],
          triggered_rules: [{ code: "minimum_margin", passed: true }]
        }, 201));
      }
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });

    renderPanel();
    await user.click(await screen.findByRole("button", { name: "Generate candidate explanation" }));

    expect(submitted).toEqual({ purpose: "candidate_explanation", quote_revision_id: 45, pricing_check_id: 501, price_candidate_id: 601 });
    expect(await screen.findByText("The selected candidate passed the saved validation evidence.")).toBeInTheDocument();
    expect(screen.getByText("Deterministic fallback")).toBeInTheDocument();
    expect(screen.getByText("pricing_check #501")).toBeInTheDocument();
  });

  it("keeps the generation controls unavailable to a viewer", async () => {
    const viewer = authenticate("viewer");
    global.fetch.mockImplementation((url) => {
      if (String(url).includes("/api/auth/me")) return Promise.resolve(jsonResponse(viewer));
      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });

    renderPanel();

    expect(await screen.findByText(/Viewer access can read saved evidence/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Generate candidate explanation" })).not.toBeInTheDocument();
  });
});
