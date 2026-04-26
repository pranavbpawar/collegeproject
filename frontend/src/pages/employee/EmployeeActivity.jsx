import React, { useState, useEffect, useCallback } from "react";
import { useEmployeeAuth } from "../../hooks/useEmployeeAuth";
import EmployeeLayout from "./EmployeeLayout";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import "./EmployeePortal.css";

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function EmployeeActivity() {
  const { employee, isLoading: authLoading, logout, authFetch } = useEmployeeAuth();
  const [sessions, setSessions]   = useState([]);
  const [summary, setSummary]     = useState(null);
  const [loading, setLoading]     = useState(true);
  const [error,   setError]       = useState(null);

  useEffect(() => {
    if (!authLoading && !employee) window.location.href = "/employee";
  }, [authLoading, employee]);

  const fetchData = useCallback(async () => {
    try {
      const [sess, summ] = await Promise.all([
        authFetch("/api/v1/work/my-sessions?limit=50"),
        authFetch("/api/v1/work/my-summary"),
      ]);
      setSessions(sess);
      setSummary(summ);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => {
    if (employee) fetchData();
  }, [employee, fetchData]);

  // Build daily chart data from sessions (last 7 days)
  const chartData = React.useMemo(() => {
    const days = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const label = d.toLocaleDateString("en-US", { weekday: "short" });
      const dateStr = d.toISOString().slice(0, 10);
      const mins = sessions
        .filter((s) => s.clock_in?.startsWith(dateStr) && s.duration_minutes)
        .reduce((acc, s) => acc + s.duration_minutes, 0);
      days.push({ day: label, hours: parseFloat((mins / 60).toFixed(1)) });
    }
    return days;
  }, [sessions]);

  if (authLoading || loading) return (
    <div style={{ minHeight: "100vh", background: "var(--ep-bg)", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="ep-spinner" />
    </div>
  );
  if (!employee) return null;

  return (
    <EmployeeLayout employee={employee} logout={logout}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Activity</h1>
      {error && <div className="ep-error-msg">{error}</div>}

      {/* Summary stats */}
      {summary && (
        <div className="ep-grid ep-grid--3" style={{ marginBottom: 20 }}>
          {[
            { label: "Today",     value: summary.today_human },
            { label: "This Week", value: summary.week_human  },
            { label: "Active Session", value: summary.open_sessions > 0 ? "In Progress" : "None" },
          ].map((item) => (
            <div className="ep-card" key={item.label}>
              <div className="ep-card__title">{item.label}</div>
              <div className="ep-stat-num" style={{ fontSize: 24 }}>{item.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Weekly chart */}
      <div className="ep-card" style={{ marginBottom: 20 }}>
        <div className="ep-card__title">Hours This Week</div>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={chartData} barCategoryGap="30%">
            <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: "var(--ep-muted)", fontSize: 12 }} />
            <YAxis axisLine={false} tickLine={false} tick={{ fill: "var(--ep-muted)", fontSize: 12 }} unit="h" />
            <Tooltip
              contentStyle={{ background: "var(--ep-surface)", border: "1px solid var(--ep-border)", borderRadius: 8 }}
              labelStyle={{ color: "var(--ep-text)" }}
              itemStyle={{ color: "var(--ep-accent)" }}
              formatter={(v) => [`${v}h`, "Worked"]}
            />
            <Bar dataKey="hours" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, idx) => (
                <Cell key={idx} fill={entry.hours > 0 ? "var(--ep-accent)" : "var(--ep-border)"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Session log table */}
      <div className="ep-card">
        <div className="ep-card__title">Session History</div>
        {sessions.length === 0 ? (
          <p style={{ color: "var(--ep-muted)", fontSize: 13 }}>No sessions recorded yet.</p>
        ) : (
          <table className="ep-table">
            <thead>
              <tr>
                <th>Clock In</th>
                <th>Clock Out</th>
                <th>Duration</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.id}>
                  <td>{formatDate(s.clock_in)}</td>
                  <td>{s.clock_out ? formatDate(s.clock_out) : "—"}</td>
                  <td>{s.duration_human}</td>
                  <td>
                    <span className={`ep-badge ${s.clock_out ? "ep-badge--blue" : "ep-badge--green"}`}>
                      {s.clock_out ? "Completed" : "In Progress"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </EmployeeLayout>
  );
}
