const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || "";
const API_BASE_URL = rawBaseUrl.replace(/\/$/, "");

export class ApiClientError extends Error {
  constructor(message, { code, status, fieldErrors = [] } = {}) {
    super(message);
    this.name = "ApiClientError";
    this.code = code || "request_failed";
    this.status = status || 0;
    this.fieldErrors = fieldErrors;
  }
}

async function parseJson(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  return response.json();
}

export async function request(path, { method = "GET", body, token, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal
    });
  } catch {
    throw new ApiClientError("Unable to reach QuoteOps AI.", {
      code: "network_unavailable"
    });
  }

  const payload = await parseJson(response);
  if (!response.ok) {
    throw new ApiClientError(payload?.detail || "The request could not be completed.", {
      code: payload?.code,
      status: response.status,
      fieldErrors: payload?.field_errors || []
    });
  }
  return payload;
}

export const authApi = {
  login(credentials) {
    return request("/api/auth/login", { method: "POST", body: credentials });
  },
  currentUser(token) {
    return request("/api/auth/me", { token });
  }
};
