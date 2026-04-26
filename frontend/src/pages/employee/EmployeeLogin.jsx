import React, { useState } from "react";
import { useEmployeeAuth } from "../../hooks/useEmployeeAuth";
import "./EmployeePortal.css";

export default function EmployeeLogin() {
  const { login, isLoading } = useEmployeeAuth();
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [error,    setError]    = useState(null);
  const [loading,  setLoading]  = useState(false);

  // Auto-login via ?token= is handled inside useEmployeeAuth on mount.
  // If that succeeded, redirect to dashboard.
  React.useEffect(() => {
    if (!isLoading) {
      const stored = localStorage.getItem("employee_token");
      if (stored) window.location.href = "/employee/dashboard";
    }
  }, [isLoading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      window.location.href = "/employee/dashboard";
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="ep-login-page">
        <div className="ep-spinner" />
      </div>
    );
  }

  return (
    <div className="ep-login-page">
      <div className="ep-login-box">
        <div className="ep-login-logo">
          <div className="ep-login-logo-icon">◈</div>
          <div className="ep-login-logo-text">Pragyantri</div>
          <p style={{ color: "var(--ep-muted)", fontSize: 13, marginTop: 6 }}>
            Employee Portal
          </p>
        </div>

        {error && <div className="ep-error-msg">⚠ {error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="ep-form-group">
            <label className="ep-form-label">Work Email</label>
            <input
              className="ep-input"
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </div>
          <div className="ep-form-group">
            <label className="ep-form-label">Password</label>
            <input
              className="ep-input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>
          <button
            className="ep-btn ep-btn--primary"
            type="submit"
            disabled={loading}
            style={{ width: "100%", marginTop: 8, justifyContent: "center" }}
          >
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <p style={{ color: "var(--ep-muted)", fontSize: 12, textAlign: "center", marginTop: 20 }}>
          Your credentials were set by your administrator.<br />
          Contact HR if you need assistance.
        </p>
      </div>
    </div>
  );
}
