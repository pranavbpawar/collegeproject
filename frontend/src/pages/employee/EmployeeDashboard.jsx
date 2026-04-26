import React, { useState, useEffect, useCallback } from "react";
import { useEmployeeAuth } from "../../hooks/useEmployeeAuth";
import EmployeeLayout from "./EmployeeLayout";
import "./EmployeePortal.css";

// Live timer for open session
function LiveTimer({ startIso }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = new Date(startIso).getTime();
    const tick = () => setElapsed(Math.floor((Date.now() - start) / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [startIso]);

  const h = Math.floor(elapsed / 3600);
  const m = Math.floor((elapsed % 3600) / 60);
  const s = elapsed % 60;
  return (
    <span style={{ fontFamily: "monospace", fontSize: 26, fontWeight: 700, color: "var(--ep-accent2)" }}>
      {String(h).padStart(2, "0")}:{String(m).padStart(2, "0")}:{String(s).padStart(2, "0")}
    </span>
  );
}

export default function EmployeeDashboard() {
  const { employee, isLoading: authLoading, logout, authFetch } = useEmployeeAuth();
  const [status, setStatus]       = useState(null);
  const [sessions, setSessions]   = useState(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);
  const [sessionMsg, setSessionMsg] = useState(null);
  const [sessionLoading, setSessionLoading] = useState(false);

  // Redirect if not logged in
  useEffect(() => {
    if (!authLoading && !employee) {
      window.location.href = "/employee";
    }
  }, [authLoading, employee]);

  const fetchStatus = useCallback(async () => {
    try {
      const [st, sess] = await Promise.all([
        authFetch("/api/v1/employee/status"),
        authFetch("/api/v1/work/my-sessions?limit=1"),
      ]);
      setStatus(st);
      setSessions(sess);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => {
    if (employee) {
      fetchStatus();
      const id = setInterval(fetchStatus, 30_000); // Refresh every 30s
      return () => clearInterval(id);
    }
  }, [employee, fetchStatus]);

  const handleClockIn = async () => {
    setSessionLoading(true);
    setSessionMsg(null);
    try {
      await authFetch("/api/v1/work/clock-in", {
        method: "POST",
        body: JSON.stringify({ notes: "" }),
      });
      setSessionMsg({ type: "success", text: "Clocked in successfully!" });
      await fetchStatus();
    } catch (e) {
      setSessionMsg({ type: "error", text: e.message });
    } finally {
      setSessionLoading(false);
    }
  };

  const handleClockOut = async () => {
    setSessionLoading(true);
    setSessionMsg(null);
    try {
      const res = await authFetch("/api/v1/work/clock-out", {
        method: "POST",
        body: JSON.stringify({ notes: "" }),
      });
      setSessionMsg({ type: "success", text: res.message || "Clocked out." });
      await fetchStatus();
    } catch (e) {
      setSessionMsg({ type: "error", text: e.message });
    } finally {
      setSessionLoading(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--ep-bg)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div className="ep-spinner" />
      </div>
    );
  }
  if (!employee) return null;

  const openSession = sessions?.find((s) => !s.clock_out);
  const kbtConnected = status?.kbt_connected;
  const trustScore = status?.trust_score;

  return (
    <EmployeeLayout employee={employee} logout={logout}>
      {/* Greeting */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
          Welcome back, {employee.name?.split(" ")[0]} 👋
        </h1>
        <p style={{ color: "var(--ep-muted)", fontSize: 13 }}>
          {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
        </p>
      </div>

      {error && <div className="ep-error-msg" style={{ marginBottom: 16 }}>⚠ {error}</div>}

      {/* Status row */}
      <div className="ep-grid ep-grid--4" style={{ marginBottom: 20 }}>
        {/* KBT Status */}
        <div className="ep-card">
          <div className="ep-card__title">KBT Status</div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className={`ep-dot ${kbtConnected ? "ep-dot--green" : "ep-dot--yellow"}`} />
            <span style={{ fontWeight: 600, fontSize: 15 }}>
              {kbtConnected ? "Connected" : "Disconnected"}
            </span>
          </div>
          {status?.kbt_last_seen && (
            <div style={{ color: "var(--ep-muted)", fontSize: 11, marginTop: 6 }}>
              Last seen {new Date(status.kbt_last_seen).toLocaleTimeString()}
            </div>
          )}
          {!kbtConnected && (
            <a href="/employee/device" style={{ color: "var(--ep-accent)", fontSize: 12, marginTop: 6, display: "block" }}>
              → Setup KBT
            </a>
          )}
        </div>

        {/* Today hours */}
        <div className="ep-card">
          <div className="ep-card__title">Today</div>
          <div className="ep-stat-num">{status?.today_human || "0h 0m"}</div>
          <div className="ep-stat-label">Hours worked</div>
        </div>

        {/* Week hours */}
        <div className="ep-card">
          <div className="ep-card__title">This Week</div>
          <div className="ep-stat-num">{status?.week_human || "0h 0m"}</div>
          <div className="ep-stat-label">Hours worked</div>
        </div>

        {/* Trust Score */}
        <div className="ep-card">
          <div className="ep-card__title">Trust Score</div>
          {trustScore != null ? (
            <>
              <div className="ep-stat-num" style={{
                color: trustScore >= 75 ? "var(--ep-accent2)" : trustScore >= 50 ? "var(--ep-warn)" : "var(--ep-danger)"
              }}>
                {Math.round(trustScore)}
              </div>
              <div className="ep-stat-label">out of 100</div>
            </>
          ) : (
            <div style={{ color: "var(--ep-muted)", fontSize: 13 }}>Not yet calculated</div>
          )}
        </div>
      </div>

      {/* Work session card */}
      <div className="ep-card" style={{ marginBottom: 20 }}>
        <div className="ep-card__title">Work Session</div>
        {sessionMsg && (
          <div
            className={sessionMsg.type === "success" ? "ep-badge ep-badge--green" : "ep-error-msg"}
            style={{ marginBottom: 12, display: "inline-flex" }}
          >
            {sessionMsg.text}
          </div>
        )}
        {openSession ? (
          <div style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
            <div>
              <div style={{ color: "var(--ep-muted)", fontSize: 12, marginBottom: 4 }}>Elapsed time</div>
              <LiveTimer startIso={openSession.clock_in} />
            </div>
            <div style={{ flex: 1 }} />
            <button
              className="ep-btn"
              style={{ background: "rgba(248,81,73,0.12)", color: "var(--ep-danger)", border: "1px solid rgba(248,81,73,0.3)" }}
              onClick={handleClockOut}
              disabled={sessionLoading}
            >
              {sessionLoading ? "…" : "⏹ Clock Out"}
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ color: "var(--ep-muted)", fontSize: 13 }}>You are not clocked in.</span>
            <button className="ep-btn ep-btn--primary" onClick={handleClockIn} disabled={sessionLoading}>
              {sessionLoading ? "…" : "▶ Clock In"}
            </button>
          </div>
        )}
      </div>

      {/* Quick links */}
      <div className="ep-grid ep-grid--3">
        {[
          { href: "/employee/activity", icon: "⏱", label: "Activity Log", desc: "Session history & weekly hours" },
          { href: "/employee/chat",     icon: "💬", label: "Chat",         desc: "Message your manager or HR" },
          { href: "/employee/device",   icon: "🖥", label: "Device Status", desc: "KBT install & connection" },
        ].map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="ep-card"
            style={{ textDecoration: "none", cursor: "pointer", transition: "border-color 0.15s" }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = "var(--ep-accent)"}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = "var(--ep-border)"}
          >
            <div style={{ fontSize: 24, marginBottom: 8 }}>{item.icon}</div>
            <div style={{ fontWeight: 600, color: "var(--ep-text)", marginBottom: 4 }}>{item.label}</div>
            <div style={{ fontSize: 12, color: "var(--ep-muted)" }}>{item.desc}</div>
          </a>
        ))}
      </div>
    </EmployeeLayout>
  );
}
