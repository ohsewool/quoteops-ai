import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { ApiClientError, authApi, request, requestText } from "../api/client.js";

const SESSION_KEY = "quoteops-ai-v2.session";
const AuthContext = createContext(null);

function loadSession() {
  try {
    const value = window.sessionStorage.getItem(SESSION_KEY);
    return value ? JSON.parse(value) : null;
  } catch {
    window.sessionStorage.removeItem(SESSION_KEY);
    return null;
  }
}

function saveSession(session) {
  window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function AuthProvider({ children, client = authApi }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [state, setState] = useState("restoring");

  const clearSession = useCallback(() => {
    window.sessionStorage.removeItem(SESSION_KEY);
    setUser(null);
    setToken(null);
    setState("anonymous");
  }, []);

  useEffect(() => {
    let active = true;
    const stored = loadSession();
    if (!stored?.accessToken) {
      setState("anonymous");
      return () => {
        active = false;
      };
    }

    client.currentUser(stored.accessToken)
      .then((currentUser) => {
        if (!active) return;
        setUser(currentUser);
        setToken(stored.accessToken);
        setState("authenticated");
      })
      .catch(() => {
        if (!active) return;
        clearSession();
      });

    return () => {
      active = false;
    };
  }, [clearSession, client]);

  const login = useCallback(async ({ username, password }) => {
    setState("authenticating");
    try {
      const response = await client.login({ username, password });
      const currentUser = await client.currentUser(response.access_token);
      const session = { accessToken: response.access_token, expiresAt: response.expires_at };
      saveSession(session);
      setUser(currentUser);
      setToken(response.access_token);
      setState("authenticated");
      return currentUser;
    } catch (error) {
      clearSession();
      throw error;
    }
  }, [clearSession, client]);

  const authorizedRequest = useCallback(async (path, options = {}) => {
    try {
      return await request(path, { ...options, token });
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 401) {
        clearSession();
      }
      throw error;
    }
  }, [clearSession, token]);

  const authorizedTextRequest = useCallback(async (path, options = {}) => {
    try {
      return await requestText(path, { ...options, token });
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 401) {
        clearSession();
      }
      throw error;
    }
  }, [clearSession, token]);

  const value = useMemo(() => ({
    user,
    token,
    state,
    isAuthenticated: state === "authenticated",
    login,
    logout: clearSession,
    request: authorizedRequest,
    requestText: authorizedTextRequest
  }), [authorizedRequest, authorizedTextRequest, clearSession, login, state, token, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}

export const authStorageKey = SESSION_KEY;
