/**
 * HR Dashboard
 * Cross-department behavioral and compliance monitoring.
 * Full employee list, anomaly reports, trust trends, compliance logs.
 * No agent deploy controls, no system config.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';

const API = window.location.origin + '/api/v1';

function timeSince(iso) {
    if (!iso) return '—';
    const s = Math.floor((Date.now() - new Date(iso)) / 1000);
    if (s < 60)    return `${s}s ago`;
    if (s < 3600)  return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return `${Math.floor(s / 86400)}d ago`;
}

function scoreColor(s) {
    if (s == null)  return '#4b5563';
    if (s >= 75)    return '#22c55e';
    if (s >= 60)    return '#eab308';
    if (s >= 40)    return '#f97316';
    return '#ef4444';
}

function SeverityPill({ severity }) {
    const colors = {
        critical: { bg: '#450a0a', color: '#f87171', border: '#7f1d1d' },
        warning:  { bg: '#1c1500', color: '#fbbf24', border: '#78350f' },
        info:     { bg: '#111827', color: '#94a3b8', border: '#2d3748' },
    };
    const c = colors[severity] || colors.info;
    return (
        <span style={{
            background: c.bg, color: c.color, border: `1px solid ${c.border}`,
            borderRadius: 12, padding: '2px 10px', fontSize: 11, fontWeight: 700,
        }}>
            {severity?.toUpperCase()}
        </span>
    );
}

function StatCard({ icon, label, value, color }) {
    return (
        <div style={{
            background: '#1a1f2e', border: `1px solid ${color}33`,
            borderRadius: 12, padding: '20px 24px', flex: 1,
            boxShadow: `0 0 20px ${color}11`,
        }}>
            <div style={{ fontSize: 28, marginBottom: 6 }}>{icon}</div>
            <div style={{ color, fontSize: 28, fontWeight: 800 }}>{value ?? '—'}</div>
            <div style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>{label}</div>
        </div>
    );
}

export default function HRDashboard({ onLogout }) {
    const { user, authHeaders } = useAuth();
    const [stats, setStats]       = useState(null);
    const [employees, setEmployees] = useState([]);
    const [anomalies, setAnomalies] = useState([]);
    const [behavioral, setBehavioral] = useState([]);
    const [compliance, setCompliance] = useState([]);
    const [loading, setLoading]   = useState(true);
    const [tab, setTab]           = useState('employees');
    const [search, setSearch]     = useState('');
    const [deptFilter, setDeptFilter] = useState('');
    const [departments, setDepartments] = useState([]);

    // Add Employee form state
    const [addForm, setAddForm] = useState({ name: '', email: '', department: '', send_email: true });
    const [addMsg, setAddMsg]   = useState('');
    const [addError, setAddError] = useState('');
    const [adding, setAdding]   = useState(false);

    const fetchAll = useCallback(async () => {
        setLoading(true);
        const headers = authHeaders();
        try {
            const [statsRes, empRes, anomalyRes, bRes, cRes, deptRes] = await Promise.all([
                fetch(`${API}/hr/stats`,                        { headers }),
                fetch(`${API}/hr/employees?limit=200`,          { headers }),
                fetch(`${API}/hr/anomalies?limit=50`,           { headers }),
                fetch(`${API}/hr/behavioral?limit=100`,         { headers }),
                fetch(`${API}/hr/compliance-logs?limit=50`,     { headers }),
                fetch(`${API}/user/departments`,                { headers }),
            ]);
            if (statsRes.ok)   setStats(await statsRes.json());
            if (empRes.ok)     setEmployees(await empRes.json());
            if (deptRes.ok)    setDepartments((await deptRes.json()).map(d => d.name));
            if (anomalyRes.ok) setAnomalies(await anomalyRes.json());
            if (bRes.ok)       setBehavioral(await bRes.json());
            if (cRes.ok)       setCompliance(await cRes.json());
        } catch (err) {
            console.error('HR dashboard error:', err);
        } finally {
            setLoading(false);
        }
    }, [authHeaders]);

    useEffect(() => { fetchAll(); }, [fetchAll]);

    const tabBtn = (id, label) => (
        <button
            key={id}
            onClick={() => setTab(id)}
            style={{
                padding: '8px 18px', cursor: 'pointer', background: 'none', border: 'none',
                borderBottom: `2px solid ${tab === id ? '#8b5cf6' : 'transparent'}`,
                color: tab === id ? '#8b5cf6' : '#64748b',
                fontWeight: tab === id ? 700 : 400, fontSize: 13,
            }}
        >
            {label}
        </button>
    );

    const filteredEmployees = employees.filter(e => {
        const q = search.toLowerCase();
        const matchQuery = !search || e.name.toLowerCase().includes(q) || e.email.toLowerCase().includes(q);
        const matchDept  = !deptFilter || e.department === deptFilter;
        return matchQuery && matchDept;
    });

    return (
        <div style={{ minHeight: '100vh', background: '#0f1117', color: '#e2e8f0', fontFamily: 'Inter, system-ui, sans-serif' }}>

            {/* Header */}
            <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '16px 28px',
                background: 'linear-gradient(135deg, #0f1117, #1a1030)',
                borderBottom: '1px solid #2d1a4a',
            }}>
                <div>
                    <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>
                        🧑‍💼 HR Dashboard
                    </h1>
                    <p style={{ margin: '2px 0 0', color: '#64748b', fontSize: 13 }}>
                        Behavioral & Compliance Monitoring · {user?.username}
                    </p>
                </div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{
                        background: '#2e1065', color: '#c4b5fd', borderRadius: 8,
                        padding: '4px 12px', fontSize: 12, fontWeight: 600,
                    }}>
                        🧑‍💼 HR
                    </span>
                    <button onClick={() => fetchAll()} style={{ background: '#1a1030', border: '1px solid #3b2060', borderRadius: 8, color: '#64748b', cursor: 'pointer', padding: '6px 14px', fontSize: 12 }}>
                        ↻ Refresh
                    </button>
                    <button onClick={onLogout} style={{ background: 'transparent', border: '1px solid #374151', borderRadius: 8, color: '#64748b', cursor: 'pointer', fontSize: 12, padding: '6px 14px' }}>
                        ⎋ Logout
                    </button>
                </div>
            </div>

            <div style={{ padding: '24px 28px' }}>

                {/* Stats */}
                {stats && (
                    <div style={{ display: 'flex', gap: 16, marginBottom: 28, flexWrap: 'wrap' }}>
                        <StatCard icon="👥" label="Total Employees" value={stats.total_employees}      color="#8b5cf6" />
                        <StatCard icon="🏢" label="Departments"      value={stats.total_departments}   color="#06b6d4" />
                        <StatCard icon="📊" label="Org Trust Score"  value={stats.org_avg_trust_score} color="#3b82f6" />
                        <StatCard icon="⚠️" label="At Risk (< 60)"   value={stats.at_risk_count}       color="#ef4444" />
                        <StatCard icon="✅" label="Good Standing"     value={stats.good_standing_count} color="#22c55e" />
                    </div>
                )}

                {/* Tabs */}
                <div style={{ display: 'flex', borderBottom: '1px solid #2d3748', marginBottom: 20 }}>
                    {tabBtn('employees', '👥 All Employees')}
                    {tabBtn('behavioral', '🧠 Behavioral')}
                    {tabBtn('anomalies', `⚠️ Anomalies (${anomalies.length})`)}
                    {tabBtn('compliance', '📋 Compliance Logs')}
                    {tabBtn('add', '➕ Add Employee')}
                </div>

                {/* ── Employees tab ── */}
                {tab === 'employees' && (
                    <div>
                        <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
                            <input
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                placeholder="🔍 Search name or email…"
                                style={{
                                    flex: 1, padding: '10px 14px', borderRadius: 9,
                                    background: '#111827', border: '1px solid #2d3748',
                                    color: '#e2e8f0', fontSize: 14, outline: 'none',
                                }}
                            />
                            <select
                                value={deptFilter}
                                onChange={e => setDeptFilter(e.target.value)}
                                style={{
                                    padding: '10px 14px', borderRadius: 9, background: '#111827',
                                    border: '1px solid #2d3748', color: '#94a3b8', fontSize: 13, outline: 'none',
                                }}
                            >
                                <option value="">All Departments</option>
                                {departments.map(d => <option key={d} value={d}>{d}</option>)}
                            </select>
                        </div>

                        <div style={{ color: '#4b5563', fontSize: 12, marginBottom: 10 }}>
                            {filteredEmployees.length} employees
                        </div>

                        {loading && <p style={{ color: '#4b5563' }}>Loading…</p>}

                        {filteredEmployees.map(emp => (
                            <div key={emp.id} style={{
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                padding: '12px 16px', borderRadius: 10, marginBottom: 6,
                                background: '#111827', border: '1px solid #2d3748',
                            }}>
                                <div>
                                    <div style={{ fontWeight: 600, color: '#e2e8f0', fontSize: 14 }}>{emp.name}</div>
                                    <div style={{ color: '#64748b', fontSize: 12 }}>
                                        {emp.email}
                                        {emp.department && <span style={{ marginLeft: 8, color: '#4b5563' }}>· {emp.department}</span>}
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                                    <span style={{
                                        background: scoreColor(emp.trust_score) + '22',
                                        border: `1px solid ${scoreColor(emp.trust_score)}`,
                                        color: scoreColor(emp.trust_score),
                                        borderRadius: 20, padding: '2px 10px', fontWeight: 700, fontSize: 13,
                                    }}>
                                        {emp.trust_score ?? '—'}
                                    </span>
                                    <span style={{
                                        background: emp.status === 'active' ? '#14532d' : '#1c1917',
                                        color: emp.status === 'active' ? '#4ade80' : '#94a3b8',
                                        border: `1px solid ${emp.status === 'active' ? '#16a34a' : '#374151'}`,
                                        borderRadius: 12, padding: '2px 8px', fontSize: 11, fontWeight: 600,
                                    }}>
                                        {emp.status}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* ── Behavioral tab ── */}
                {tab === 'behavioral' && (
                    <div>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                                <thead>
                                    <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #2d3748' }}>
                                        <th style={{ padding: '8px 12px' }}>Employee</th>
                                        <th style={{ padding: '8px 12px' }}>Department</th>
                                        <th style={{ padding: '8px 12px', textAlign: 'center' }}>Active</th>
                                        <th style={{ padding: '8px 12px', textAlign: 'center' }}>Idle</th>
                                        <th style={{ padding: '8px 12px', textAlign: 'center' }}>USB</th>
                                        <th style={{ padding: '8px 12px', textAlign: 'center' }}>Files</th>
                                        <th style={{ padding: '8px 12px', textAlign: 'center' }}>Sites</th>
                                        <th style={{ padding: '8px 12px' }}>Last Seen</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {behavioral.map(b => (
                                        <tr key={b.employee_id} style={{ borderBottom: '1px solid #1e2a3a' }}>
                                            <td style={{ padding: '10px 12px', color: '#e2e8f0', fontWeight: 600 }}>{b.employee_name}</td>
                                            <td style={{ padding: '10px 12px', color: '#64748b' }}>{b.department}</td>
                                            <td style={{ padding: '10px 12px', textAlign: 'center', color: '#22c55e' }}>{b.active_events}</td>
                                            <td style={{ padding: '10px 12px', textAlign: 'center', color: '#f59e0b' }}>{b.idle_events}</td>
                                            <td style={{ padding: '10px 12px', textAlign: 'center', color: b.usb_events > 0 ? '#f97316' : '#4b5563' }}>{b.usb_events}</td>
                                            <td style={{ padding: '10px 12px', textAlign: 'center', color: '#94a3b8' }}>{b.file_events}</td>
                                            <td style={{ padding: '10px 12px', textAlign: 'center', color: '#94a3b8' }}>{b.website_events}</td>
                                            <td style={{ padding: '10px 12px', color: '#4b5563', fontSize: 11 }}>{timeSince(b.last_seen)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {behavioral.length === 0 && !loading && (
                                <p style={{ color: '#4b5563', textAlign: 'center', marginTop: 32 }}>No behavioral data in the last 7 days.</p>
                            )}
                        </div>
                    </div>
                )}

                {/* ── Anomalies tab ── */}
                {tab === 'anomalies' && (
                    <div>
                        {anomalies.length === 0 ? (
                            <div style={{ textAlign: 'center', padding: '48px 0', color: '#4b5563' }}>
                                <div style={{ fontSize: 40 }}>✅</div>
                                <p>No anomalies detected across the organisation.</p>
                            </div>
                        ) : anomalies.map(a => (
                            <div key={a.employee_id} style={{
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap',
                                padding: '12px 16px', borderRadius: 10, marginBottom: 8,
                                background: '#111827', border: '1px solid #2d3748',
                            }}>
                                <div>
                                    <div style={{ fontWeight: 600, color: '#e2e8f0', fontSize: 14 }}>{a.employee_name}</div>
                                    <div style={{ color: '#64748b', fontSize: 12 }}>
                                        {a.email} · {a.department} · {timeSince(a.score_time)}
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 4 }}>
                                    <span style={{
                                        background: scoreColor(a.total_score) + '22',
                                        border: `1px solid ${scoreColor(a.total_score)}`,
                                        color: scoreColor(a.total_score),
                                        borderRadius: 20, padding: '2px 10px', fontWeight: 700, fontSize: 13,
                                    }}>
                                        {a.total_score}
                                    </span>
                                    <SeverityPill severity={a.severity} />
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* ── Compliance Logs tab ── */}
                {tab === 'compliance' && (
                    <div>
                        <div style={{ color: '#64748b', fontSize: 12, marginBottom: 12 }}>
                            Agent email distribution audit trail — last {compliance.length} records
                        </div>
                        {compliance.map(log => (
                            <div key={log.id} style={{
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                padding: '10px 16px', borderRadius: 10, marginBottom: 6,
                                background: '#111827',
                                border: `1px solid ${log.status === 'sent' ? '#14532d' : '#450a0a'}`,
                            }}>
                                <div>
                                    <span style={{
                                        color: log.status === 'sent' ? '#4ade80' : '#f87171',
                                        fontWeight: 700, fontSize: 12, marginRight: 8,
                                    }}>
                                        {log.status === 'sent' ? '✅' : '❌'} {log.status.toUpperCase()}
                                    </span>
                                    <span style={{ color: '#e2e8f0', fontSize: 13 }}>
                                        {log.employee_name || log.employee_email}
                                    </span>
                                </div>
                                <span style={{ color: '#4b5563', fontSize: 11 }}>{timeSince(log.sent_at)}</span>
                            </div>
                        ))}
                        {compliance.length === 0 && <p style={{ color: '#4b5563', textAlign: 'center' }}>No compliance records yet.</p>}
                    </div>
                )}

                {/* ── Add Employee tab ── */}
                {tab === 'add' && (
                    <div style={{ background: '#1a1f2e', border: '1px solid #2d3748', borderRadius: 12, padding: '24px 32px', maxWidth: 500, margin: '0 auto' }}>
                        <h2 style={{ marginTop: 0, marginBottom: 20, fontSize: 18 }}>Onboard New Employee</h2>
                        
                        {addMsg && <div style={{ background: '#064e3b', color: '#34d399', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: 14 }}>{addMsg}</div>}
                        {addError && <div style={{ background: '#7f1d1d', color: '#fca5a5', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: 14 }}>{addError}</div>}
                        
                        <form onSubmit={async (e) => {
                            e.preventDefault();
                            if (!addForm.department) { setAddError('Please select a department'); return; }
                            setAdding(true); setAddError(''); setAddMsg('');
                            try {
                                const res = await fetch(`${API}/user/create-employee`, {
                                    method: 'POST',
                                    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
                                    body: JSON.stringify(addForm)
                                });
                                if (!res.ok) {
                                    const d = await res.json().catch(()=>({}));
                                    throw new Error(d.detail || 'Failed to create employee');
                                }
                                setAddMsg(`✅ ${addForm.name} added successfully! Email instructions sent.`);
                                setAddForm({ name: '', email: '', department: '', send_email: true });
                                fetchAll();
                            } catch (err) {
                                setAddError(err.message);
                            } finally {
                                setAdding(false);
                            }
                        }}>
                            <div style={{ marginBottom: 16 }}>
                                <label style={{ display: 'block', fontSize: 13, color: '#94a3b8', marginBottom: 6 }}>Full Name</label>
                                <input required type="text" value={addForm.name} onChange={e=>setAddForm({...addForm, name: e.target.value})}
                                    style={{ width: '100%', padding: '10px 12px', background: '#0f1117', border: '1px solid #374151', color: '#fff', borderRadius: 6, boxSizing: 'border-box' }} />
                            </div>
                            <div style={{ marginBottom: 16 }}>
                                <label style={{ display: 'block', fontSize: 13, color: '#94a3b8', marginBottom: 6 }}>Email Address</label>
                                <input required type="email" value={addForm.email} onChange={e=>setAddForm({...addForm, email: e.target.value})}
                                    style={{ width: '100%', padding: '10px 12px', background: '#0f1117', border: '1px solid #374151', color: '#fff', borderRadius: 6, boxSizing: 'border-box' }} />
                            </div>
                            <div style={{ marginBottom: 16 }}>
                                <label style={{ display: 'block', fontSize: 13, color: '#94a3b8', marginBottom: 6 }}>Assign Department</label>
                                <select required value={addForm.department} onChange={e=>setAddForm({...addForm, department: e.target.value})}
                                    style={{ width: '100%', padding: '10px 12px', background: '#0f1117', border: '1px solid #374151', color: addForm.department ? '#fff' : '#64748b', borderRadius: 6, boxSizing: 'border-box' }}>
                                    <option value="" disabled>Select a department...</option>
                                    {departments.map(d => <option key={d} value={d}>{d}</option>)}
                                </select>
                                <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>HR can assign employees to any department across the organisation.</div>
                            </div>
                            
                            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginBottom: 24, padding: '12px', background: '#0f1117', border: '1px solid #1e293b', borderRadius: 8 }}>
                                <input type="checkbox" checked={addForm.send_email} onChange={e=>setAddForm({...addForm, send_email: e.target.checked})} />
                                <div>
                                    <div style={{ fontSize: 14, color: '#e2e8f0', fontWeight: 600 }}>Send Setup Email</div>
                                    <div style={{ fontSize: 12, color: '#64748b' }}>Automatically emails the employee with the NEF Agent download link and onboarding instructions.</div>
                                </div>
                            </label>

                            <button disabled={adding} type="submit" style={{ width: '100%', padding: '12px', background: '#8b5cf6', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 700, cursor: adding ? 'wait' : 'pointer' }}>
                                {adding ? 'Creating...' : 'Create Employee'}
                            </button>
                        </form>
                    </div>
                )}
            </div>
        </div>
    );
}
