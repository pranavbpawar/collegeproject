import React, { useState } from "react";
import "./EmployeePortal.css";

const NAV_ITEMS = [
  { path: "/employee/dashboard", label: "Dashboard",    icon: "⬡" },
  { path: "/employee/activity",  label: "Activity",     icon: "⏱" },
  { path: "/employee/chat",      label: "Chat",         icon: "💬" },
  { path: "/employee/device",    label: "Device",       icon: "🖥" },
];

export default function EmployeeLayout({ employee, logout, children }) {
  const [navOpen, setNavOpen] = useState(false);
  const current = window.location.pathname;

  const navigate = (path) => {
    window.location.href = path;
  };

  const initials = employee?.name
    ? employee.name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()
    : "?";

  return (
    <div className="ep-shell">
      {/* Sidebar */}
      <aside className={`ep-sidebar ${navOpen ? "ep-sidebar--open" : ""}`}>
        <div className="ep-sidebar__brand">
          <span className="ep-sidebar__logo">◈</span>
          <span className="ep-sidebar__name">Pragyantri</span>
        </div>

        <nav className="ep-sidebar__nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.path}
              className={`ep-nav-item ${current === item.path ? "ep-nav-item--active" : ""}`}
              onClick={() => navigate(item.path)}
            >
              <span className="ep-nav-item__icon">{item.icon}</span>
              <span className="ep-nav-item__label">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="ep-sidebar__footer">
          <div className="ep-user-pill">
            <div className="ep-avatar">{initials}</div>
            <div className="ep-user-info">
              <div className="ep-user-info__name">{employee?.name}</div>
              <div className="ep-user-info__dept">{employee?.department || "Employee"}</div>
            </div>
          </div>
          <button className="ep-logout-btn" onClick={logout} title="Sign out">
            ⎋
          </button>
        </div>
      </aside>

      {/* Mobile overlay */}
      {navOpen && (
        <div className="ep-overlay" onClick={() => setNavOpen(false)} />
      )}

      {/* Main */}
      <main className="ep-main">
        <header className="ep-topbar">
          <button className="ep-menu-btn" onClick={() => setNavOpen(!navOpen)}>
            ☰
          </button>
          <span className="ep-topbar__title">
            {NAV_ITEMS.find((n) => n.path === current)?.label || "Portal"}
          </span>
        </header>
        <div className="ep-content">{children}</div>
      </main>
    </div>
  );
}
