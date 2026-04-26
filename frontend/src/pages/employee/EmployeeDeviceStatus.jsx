import React, { useState, useEffect, useCallback } from "react";
import { useEmployeeAuth } from "../../hooks/useEmployeeAuth";
import EmployeeLayout from "./EmployeeLayout";
import "./EmployeePortal.css";

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <button
      onClick={copy}
      style={{
        position: "absolute", top: 10, right: 10,
        background: "rgba(255,255,255,0.08)", border: "none", borderRadius: 6,
        color: "var(--ep-muted)", cursor: "pointer", padding: "4px 8px", fontSize: 12,
      }}
    >
      {copied ? "✓ Copied" : "Copy"}
    </button>
  );
}

export default function EmployeeDeviceStatus() {
  const { employee, isLoading: authLoading, logout, authFetch } = useEmployeeAuth();
  const [status,  setStatus]  = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  useEffect(() => {
    if (!authLoading && !employee) window.location.href = "/employee";
  }, [authLoading, employee]);

  const fetchStatus = useCallback(async () => {
    try {
      const st = await authFetch("/api/v1/employee/status");
      setStatus(st);
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
      const id = setInterval(fetchStatus, 15_000);
      return () => clearInterval(id);
    }
  }, [employee, fetchStatus]);

  if (authLoading || loading) return (
    <div style={{ minHeight: "100vh", background: "var(--ep-bg)", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="ep-spinner" />
    </div>
  );
  if (!employee) return null;

  const kbtConnected  = status?.kbt_connected;
  const lastSeen      = status?.kbt_last_seen ? new Date(status.kbt_last_seen).toLocaleString() : null;
  const deviceId      = status?.kbt_device_id;
  const activated     = status?.activation_status === "activated";
  const serverUrl     = import.meta.env.VITE_BACKEND_URL || window.location.origin;
  const linuxCmd      = `curl -s "${serverUrl}/api/v1/install/install.sh?employee_id=${employee.id}" | bash`;
  const winCmd        = `iwr -useb "${serverUrl}/api/v1/install/install.ps1?employee_id=${employee.id}" | iex`;

  return (
    <EmployeeLayout employee={employee} logout={logout}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Device Status</h1>
      {error && <div className="ep-error-msg" style={{ marginBottom: 12 }}>⚠ {error}</div>}

      {/* KBT Status Card */}
      <div className="ep-card" style={{ marginBottom: 16 }}>
        <div className="ep-card__title">KBT Agent</div>
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className={`ep-dot ${kbtConnected ? "ep-dot--green" : activated ? "ep-dot--yellow" : "ep-dot--red"}`} />
            <span style={{ fontWeight: 700, fontSize: 18 }}>
              {kbtConnected ? "Connected" : activated ? "Disconnected" : "Not Activated"}
            </span>
          </div>
          <span className={`ep-badge ${kbtConnected ? "ep-badge--green" : activated ? "ep-badge--yellow" : "ep-badge--red"}`}>
            {kbtConnected ? "● Live" : activated ? "○ Offline" : "○ Pending"}
          </span>
        </div>

        <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {[
            { label: "Activation", value: activated ? "Activated" : "Pending" },
            { label: "Device ID",  value: deviceId || "Unknown" },
            { label: "Last Seen",  value: lastSeen || "Never" },
            { label: "Employee ID", value: employee.id },
          ].map((item) => (
            <div key={item.label}>
              <div style={{ fontSize: 11, color: "var(--ep-muted)", marginBottom: 2 }}>{item.label}</div>
              <div style={{ fontSize: 13, fontFamily: item.label === "Employee ID" || item.label === "Device ID" ? "monospace" : undefined }}>
                {item.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Install instructions (always shown so employees can reinstall) */}
      <div className="ep-card" style={{ marginBottom: 16 }}>
        <div className="ep-card__title">
          {kbtConnected ? "Reinstall KBT" : "Install KBT Agent"}
        </div>
        <p style={{ color: "var(--ep-muted)", fontSize: 13, marginBottom: 16 }}>
          {kbtConnected
            ? "To reinstall or move to a new device, run one of the commands below."
            : "Run one command below to install and start the KBT agent on your computer."}
        </p>

        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: "var(--ep-muted)", marginBottom: 6, fontWeight: 600 }}>
            🐧 Linux / macOS
          </div>
          <div className="ep-code" style={{ position: "relative" }}>
            {linuxCmd}
            <CopyButton text={linuxCmd} />
          </div>
        </div>

        <div>
          <div style={{ fontSize: 12, color: "var(--ep-muted)", marginBottom: 6, fontWeight: 600 }}>
            🪟 Windows (PowerShell)
          </div>
          <div className="ep-code" style={{ position: "relative" }}>
            {winCmd}
            <CopyButton text={winCmd} />
          </div>
        </div>
      </div>

      {/* Troubleshooting */}
      <div className="ep-card">
        <div className="ep-card__title">Troubleshooting</div>
        <ul style={{ color: "var(--ep-muted)", fontSize: 13, paddingLeft: 16, lineHeight: 2 }}>
          <li>If the install command fails, contact your IT administrator.</li>
          <li>If KBT shows Disconnected, try restarting it: <code style={{ background: "var(--ep-bg)", padding: "1px 6px", borderRadius: 4, color: "var(--ep-accent2)" }}>systemctl --user restart kbt</code></li>
          <li>On Windows: search for <strong>TBAPS-KBT</strong> in Task Scheduler and click "Run".</li>
          <li>The status updates every 15 seconds while this page is open.</li>
        </ul>
      </div>
    </EmployeeLayout>
  );
}
