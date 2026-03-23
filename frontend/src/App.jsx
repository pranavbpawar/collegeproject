/**
 * TBAPS — Main Application
 * Role-aware routing: dispatches to Admin, Manager, or HR dashboard based on JWT role.
 * Wrapped with AuthProvider so all child components can use useAuth().
 */

import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import AdminAgents from './pages/AdminAgents';
import ManagerDashboard from './pages/ManagerDashboard';
import HRDashboard from './pages/HRDashboard';
import PeopleManagement from './pages/PeopleManagement';

// Existing Admin components
import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import './App.css';

import StatCard         from './components/StatCard';
import EmployeeList     from './components/EmployeeList';
import DetailPanel      from './components/DetailPanel';
import AlertsPanel      from './components/AlertsPanel';
import FilterBar        from './components/FilterBar';
import LoadingSpinner   from './components/LoadingSpinner';
import ErrorBoundary    from './components/ErrorBoundary';

import { useEmployeeData } from './hooks/useEmployeeData';
import { useFilters }      from './hooks/useFilters';
import { getScoreColor, getScoreStatus, calculateStats } from './utils/scoreUtils';

const API_BASE_URL       = '/api/v1';
const REFRESH_INTERVAL   = 60000;

// ── Admin employee-trust dashboard (unchanged logic) ──────────────────────────

function TrustDashboard() {
    const [selectedEmployee, setSelectedEmployee] = useState(null);
    const [showAlerts, setShowAlerts]             = useState(true);
    const [sortConfig, setSortConfig]             = useState({ key: 'trust_score', direction: 'desc' });

    const { employees, loading, error, refetch } = useEmployeeData(API_BASE_URL, REFRESH_INTERVAL);
    const { filters, setFilters, filteredData }  = useFilters(employees);
    const stats              = calculateStats(employees);
    const filteredEmployees  = filteredData;

    const handleSelectEmployee = (emp) => setSelectedEmployee(emp);
    const handleSort = (key) => setSortConfig(prev => ({
        key,
        direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));

    const sortedEmployees = React.useMemo(() => {
        const sorted = [...filteredEmployees];
        sorted.sort((a, b) => {
            const aVal = a[sortConfig.key];
            const bVal = b[sortConfig.key];
            if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
            if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
            return 0;
        });
        return sorted;
    }, [filteredEmployees, sortConfig]);

    if (error) {
        return (
            <div className="dashboard error-state">
                <div className="error-message">
                    <h2>⚠️ Error Loading Dashboard</h2>
                    <p>{error}</p>
                    <button onClick={refetch} className="btn-primary">Retry</button>
                </div>
            </div>
        );
    }

    return (
        <ErrorBoundary>
            <div className="dashboard">
                <header className="header">
                    <div className="header-content">
                        <div className="header-title">
                            <h1>TBAPS — Employee Trust Monitor</h1>
                            <p className="subtitle">Real-Time Trust & Productivity Tracking</p>
                        </div>
                        <div className="header-actions">
                            <button onClick={refetch} className="btn-icon" title="Refresh data" disabled={loading}>
                                🔄 Refresh
                            </button>
                            <button onClick={() => setShowAlerts(!showAlerts)} className="btn-icon">
                                {showAlerts ? '🔔' : '🔕'} Alerts
                            </button>
                        </div>
                    </div>
                    {loading && <div className="loading-bar" />}
                </header>

                <section className="stats-overview">
                    <StatCard label="Average Trust Score" value={stats.avgScore}     type="info"    icon="📊" trend={stats.avgTrend} />
                    <StatCard label="At Risk"             value={stats.atRisk}       type="warning" icon="⚠️" subtitle="Score < 60" />
                    <StatCard label="Good Standing"       value={stats.goodStanding} type="success" icon="✅" subtitle="Score > 75" />
                    <StatCard label="Total Monitored"     value={stats.total}        type="info"    icon="👥" />
                </section>

                {showAlerts && <AlertsPanel employees={employees} />}

                <FilterBar filters={filters} setFilters={setFilters} employees={employees} />

                <div className="main-content">
                    <section className="employee-list-section">
                        {loading && employees.length === 0
                            ? <LoadingSpinner />
                            : <EmployeeList
                                employees={sortedEmployees}
                                onSelectEmployee={handleSelectEmployee}
                                selectedEmployee={selectedEmployee}
                                sortConfig={sortConfig}
                                onSort={handleSort}
                              />
                        }
                    </section>
                    {selectedEmployee && (
                        <DetailPanel employee={selectedEmployee} onClose={() => setSelectedEmployee(null)} />
                    )}
                </div>

                <footer className="footer">
                    <p>Last updated: {new Date().toLocaleString()}</p>
                    <p>Monitoring {employees.length} employees</p>
                </footer>
            </div>
        </ErrorBoundary>
    );
}


// ── Admin shell — full nav with all tabs ──────────────────────────────────────

function AdminShell({ onLogout }) {
    const { user, token } = useAuth();
    const [tab, setTab]   = useState('dashboard');

    const tabBtn = (id, label) => (
        <button
            key={id}
            onClick={() => setTab(id)}
            style={{
                padding: '8px 20px', cursor: 'pointer', fontWeight: tab === id ? 700 : 400,
                background: tab === id ? '#1e3a5f' : 'transparent',
                border: `1px solid ${tab === id ? '#3b82f6' : '#2d3748'}`,
                borderRadius: 8, color: tab === id ? '#3b82f6' : '#94a3b8',
                fontSize: 13, transition: 'all 0.2s',
            }}
        >
            {label}
        </button>
    );

    return (
        <>
            {/* Nav */}
            <div style={{
                display: 'flex', gap: 10, padding: '12px 24px',
                background: '#0f1117', borderBottom: '1px solid #1e2a3a', alignItems: 'center',
            }}>
                {tabBtn('dashboard', '📊 Trust Monitor')}
                {tabBtn('people',    '👥 People')}
                {tabBtn('agents',    '🖥️ NEF Agents')}
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{
                        background: '#1e3a5f', color: '#3b82f6', borderRadius: 8,
                        padding: '4px 12px', fontSize: 12, fontWeight: 600,
                    }}>
                        🛡️ Admin · {user?.username}
                    </span>
                    <button onClick={onLogout} style={{
                        padding: '6px 14px', border: '1px solid #374151', borderRadius: 8,
                        background: 'transparent', color: '#64748b', cursor: 'pointer', fontSize: 12,
                    }}>
                        ⎋ Logout
                    </button>
                </div>
            </div>

            {tab === 'dashboard' && <TrustDashboard />}
            {tab === 'people'    && <PeopleManagement token={token} />}
            {tab === 'agents'    && <AdminAgents token={token} onUnauthorized={onLogout} />}
        </>
    );
}


// ── Role Router — dispatches to correct shell ─────────────────────────────────

function RoleRouter() {
    const { user, token, logout } = useAuth();

    if (!token || !user) return null; // guarded by App

    switch (user.role) {
        case 'admin':
            return <AdminShell onLogout={logout} />;
        case 'manager':
            return <ManagerDashboard onLogout={logout} />;
        case 'hr':
            return <HRDashboard onLogout={logout} />;
        default:
            return (
                <div style={{ minHeight: '100vh', background: '#0f1117', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ef4444', fontFamily: 'Inter, sans-serif' }}>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 48 }}>⛔</div>
                        <h2 style={{ color: '#e2e8f0' }}>Unknown Role: {user.role}</h2>
                        <p style={{ color: '#64748b' }}>Contact your administrator.</p>
                        <button onClick={logout} style={{ marginTop: 16, padding: '10px 24px', background: '#1e3a5f', border: '1px solid #3b82f6', borderRadius: 8, color: '#3b82f6', cursor: 'pointer' }}>
                            ⎋ Logout
                        </button>
                    </div>
                </div>
            );
    }
}


// ── Root App — wrapped with AuthProvider ──────────────────────────────────────

function AppInner() {
    const { token, user, login } = useAuth();

    const handleLogin = (newToken, userData) => {
        login(newToken, userData);
    };

    if (!token || !user) {
        return <Login onLogin={handleLogin} />;
    }

    return <RoleRouter />;
}

export default function App() {
    return (
        <AuthProvider>
            <AppInner />
        </AuthProvider>
    );
}
