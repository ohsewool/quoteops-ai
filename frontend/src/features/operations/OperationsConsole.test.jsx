import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, authStorageKey } from "../../app/auth/AuthProvider.jsx";
import { OperationsConsole } from "./OperationsConsole.jsx";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

describe("V2-09A operations console", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.sessionStorage.setItem(authStorageKey, JSON.stringify({ accessToken: "admin-token", expiresAt: "2099-01-01T00:00:00Z" }));
    global.fetch = vi.fn();
  });

  it("uses only the versioned competitor-reference adapter and safe diagnostics", async () => {
    const user = userEvent.setup();
    const admin = { id: 1, username: "admin", display_name: "Admin", role: "admin", active: true };
    let importPayload = null;
    global.fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/api/auth/me")) return Promise.resolve(jsonResponse(admin));
      if (path.includes("/api/operations/diagnostics")) return Promise.resolve(jsonResponse({ environment: "local", database_configured: true, docs_enabled: true, openapi_enabled: true, demo_enabled: true, cors_origin_count: 1, database_ready: true, alembic_revision: "0009_operations_demo_domain", audit_event_count: 4 }));
      if (path.includes("/api/operations/audit-events")) return Promise.resolve(jsonResponse({ items: [{ id: 4, action: "quote.created", entity_type: "quote", entity_id: "12", actor_username: "admin", created_at: "2026-07-18T10:00:00Z" }], page: 1, page_size: 25, total: 1 }));
      if (path.endsWith("/api/operations/competitor-references/import") && options.method === "POST") {
        importPayload = JSON.parse(options.body);
        return Promise.resolve(jsonResponse({ schema_version: "competitor-reference-csv-v1", imported_count: 1, product_ids: [1], competitor_ids: [2] }));
      }
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });

    render(<AuthProvider><OperationsConsole /></AuthProvider>);

    expect(await screen.findByRole("heading", { name: "Operations" })).toBeInTheDocument();
    expect(screen.getByText("Safe diagnostics")).toBeInTheDocument();
    expect(screen.queryByText(/database_url/i)).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("CSV input"), "product_id,competitor_id,quantity,price_basis,reference_price,observed_at,source_note\n1,2,25,unit_price,3000.00,2026-07-18T10:00:00+00:00,source");
    await user.click(screen.getByRole("button", { name: "Import CSV" }));

    expect(importPayload).toEqual({
      schema_version: "competitor-reference-csv-v1",
      csv_text: "product_id,competitor_id,quantity,price_basis,reference_price,observed_at,source_note\n1,2,25,unit_price,3000.00,2026-07-18T10:00:00+00:00,source"
    });
    expect(await screen.findByText("1 competitor reference rows were imported atomically.")).toBeInTheDocument();
  });
});
