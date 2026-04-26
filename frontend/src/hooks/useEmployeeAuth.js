/**
 * useEmployeeAuth — Authentication hook for the Employee Portal
 *
 * Handles:
 *  1. Email/password login via POST /api/v1/employee/login
 *  2. Auto-login via ?token= URL param → POST /api/v1/kbt/portal-token/exchange
 *  3. Persistent session via localStorage (key: employee_token)
 *  4. Logout (clears token + redirects to /employee)
 */

import { useState, useEffect, useCallback } from "react";

const TOKEN_KEY = "employee_token";
const API_BASE  = import.meta.env.VITE_BACKEND_URL || "";

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export function useEmployeeAuth() {
  const [employee, setEmployee]   = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError]         = useState(null);

  /** Persist token + fetch /employee/me to populate `employee` */
  const _applyToken = useCallback(async (token) => {
    localStorage.setItem(TOKEN_KEY, token);
    try {
      const me = await apiFetch("/api/v1/employee/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setEmployee({ ...me, token });
      setError(null);
    } catch (e) {
      localStorage.removeItem(TOKEN_KEY);
      setEmployee(null);
      throw e;
    }
  }, []);

  /** On mount: check for ?token= param (KBT auto-login) or existing stored token */
  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      try {
        // 1. Check for portal token in URL param
        const params      = new URLSearchParams(window.location.search);
        const portalToken = params.get("token");
        if (portalToken) {
          // Exchange single-use portal token for a session JWT
          const data = await apiFetch("/api/v1/kbt/portal-token/exchange", {
            method: "POST",
            body: JSON.stringify({ portal_token: portalToken }),
          });
          // Clean token from URL without page reload
          window.history.replaceState({}, "", window.location.pathname);
          await _applyToken(data.access_token);
          setIsLoading(false);
          return;
        }

        // 2. Check for existing stored token
        const stored = localStorage.getItem(TOKEN_KEY);
        if (stored) {
          await _applyToken(stored);
        }
      } catch (e) {
        setError(e.message);
        localStorage.removeItem(TOKEN_KEY);
        setEmployee(null);
      } finally {
        setIsLoading(false);
      }
    };
    init();
  }, [_applyToken]);

  /** Email + password login */
  const login = useCallback(async (email, password) => {
    setError(null);
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const res = await fetch(`${API_BASE}/api/v1/employee/login`, {
      method:  "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body:    formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || "Login failed");
    }
    const data = await res.json();
    await _applyToken(data.access_token);
  }, [_applyToken]);

  /** Logout */
  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setEmployee(null);
    window.location.href = "/employee";
  }, []);

  /** Authenticated fetch wrapper */
  const authFetch = useCallback((path, options = {}) => {
    const token = localStorage.getItem(TOKEN_KEY);
    return apiFetch(path, {
      ...options,
      headers: {
        Authorization: token ? `Bearer ${token}` : "",
        ...options.headers,
      },
    });
  }, []);

  return { employee, isLoading, error, login, logout, authFetch };
}
