/**
 * Manager Dashboard
 * Department-scoped team monitoring view.
 * Shows only employees in the manager's assigned department.
 * No agent deployment, no system config controls.
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

function scoreColor(score) {
    if (score == null)  return '#4b5563';
    if (score >= 75)    return '#22c55e';
    if (score >= 60)    return '#eab308';
    if (score >= 40)    return '#f97316';
    return '#ef4444';
}

function ScoreBadge({ score }) {
    return (
        <span style={{
            background: scoreColor(score) + '22',
            border: `1px solid ${scoreColor(score)}`,
            color: scoreColor(score),
            borderRadius: 20, padding: '2px 10px',
            fontWeight: 700, fontSize: 13,
        }}>
            {score != null ? score : '—'}
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

export default function ManagerDashboard({ onLogout }) {
    const { user, authHeaders } = useAuth();
    const [stats, setStats]     = useState(null);
    const [team, setTeam]       = useState([]);
    const [alerts, setAlerts]   = useState([]);
    const [search, setSearch]   = useState('');
    const [selected, setSelected] = useState(null);
    const [activity, setActivity] = useState([]);
    const [loading, setLoading] = useState(true);
    const [tab, setTab]         = useState('team'); // team | alerts | add

    // Add Employee form state
    const [addForm, setAddForm] = useState({ name: '', email: '', send_email: true });
    const [addMsg, setAddMsg]   = useState('');
    const [addError, setAddError] = useState('');
    const [adding, setAdding]   = useState(false);

    const fetchAll = useCallback(async () => {
        setLoading(true);
        try {
            const [statsRes, teamRes, alertsRes] = await Promise.all([
                fetch(`${API}/manager/stats`, { headers: authHeaders() }),
                fetch(`${API}/manager/team?limit=100`, { headers: authHeaders() }),
                fetch(`${API}/manager/alerts?limit=30`, { headers: authHeaders() }),
            ]);
            if (statsRes.ok)  setStats(await statsRes.json());
            if (teamRes.ok)   setTeam(await teamRes.json());
            if (alertsRes.ok) setAlerts(await alertsRes.json());
        } catch (err) {
            console.error('Manager dashboard error:', err);
        } finally {
            setLoading(false);
        }
    }, [authHeaders]);

    useEffect(() => { fetchAll(); }, [fetchAll]);

    const fetchActivity = async (empId) => {
        const res = await fetch(`${API}/manager/team/${empId}/activity?limit=15`, {
            headers: authHeaders(),
        });
        if (res.ok) setActivity(await res.json());
    };

    const handleSelect = (emp) => {
        setSelected(emp);
        fetchActivity(emp.id);
    };

    const filtered = team.filter(e =>
        !search || e.name.toLowerCase().includes(search.toLowerCase()) ||
        e.email.toLowerCase().includes(search.toLowerCase())
    );

    const tabBtn = (id, label) => (
        <button
            key={id}
            onClick={() => setTab(id)}
            style={{
                padding: '8px 18px', cursor: 'pointer', background: 'none', border: 'none',
                borderBottom: `2px solid ${tab === id ? '#3b82f6' : 'transparent'}`,
                color: tab === id ? '#3b82f6' : '#64748b',
                fontWeight: tab === id ? 700 : 400, fontSize: 13,
            }}
        >
            {label}
        </button>
    );

    return (
        <div style={{ minHeight: '100vh', background: '#0f1117', color: '#e2e8f0', fontFamily: 'Inter, system-ui, sans-serif' }}>

            {/* Header */}
            <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '16px 28px',
                background: 'linear-gradient(135deg, #0f1117, #1a2035)',
                borderBottom: '1px solid #1e2a3a',
            }}>
                <div>
                    <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: '#e2e8f0' }}>
                        📊 Manager Dashboard
                    </h1>
                    <p style={{ margin: '2px 0 0', color: '#64748b', fontSize: 13 }}>
                        {user?.department_name || 'Your Department'} · {user?.username}
                    </p>
                </div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{
                        background: '#1e3a5f', color: '#93c5fd', borderRadius: 8,
                        padding: '4px 12px', fontSize: 12, fontWeight: 600,
                    }}>
                        🏢 {user?.department_name || 'Manager'}
                    </span>
                    <button
                        onClick={() => { fetchAll(); }}
                        style={{ background: '#1a2035', border: '1px solid #2d3748', borderRadius: 8, color: '#64748b', cursor: 'pointer', padding: '6px 14px', fontSize: 12 }}
                    >
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
                        <StatCard icon="👥" label="Team Members" value={stats.total_employees} color="#3b82f6" />
                        <StatCard icon="📊" label="Avg Trust Score" value={stats.avg_trust_score} color="#8b5cf6" />
                        <StatCard icon="⚠️" label="At Risk (< 60)" value={stats.at_risk_count} color="#ef4444" />
                        <StatCard icon="✅" label="Good Standing" value={stats.good_standing_count} color="#22c55e" />
                        <StatCard icon="🖥️" label="Agents Online" value={stats.agents_online} color="#06b6d4" />
                    </div>
                )}

                {/* Tabs */}
                <div style={{ display: 'flex', borderBottom: '1px solid #2d3748', marginBottom: 20 }}>
                    {tabBtn('team', '👥 Team')}
                    {tabBtn('alerts', `⚠️ Alerts (${alerts.length})`)}
                    {tabBtn('add', '➕ Add Employee')}
                </div>

                {/* Team tab */}
                {tab === 'team' && (
                    <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 380px' : '1fr', gap: 20 }}>
                        <div>
                            {/* Search */}
                            <input
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                placeholder="🔍 Search team by name or email…"
                                style={{
                                    width: '100%', padding: '10px 14px', borderRadius: 9,
                                    background: '#111827', border: '1px solid #2d3748',
                                    color: '#e2e8f0', fontSize: 14, outline: 'none',
                                    marginBottom: 14, boxSizing: 'border-box',
                                }}
                            />

                            {loading && <p style={{ color: '#4b5563' }}>Loading team…</p>}

                            {/* Employee table */}
                            {filtered.map(emp => (
                                <div
                                    key={emp.id}
                                    onClick={() => handleSelect(emp)}
                                    style={{
                                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                        padding: '12px 16px', borderRadius: 10, cursor: 'pointer', marginBottom: 8,
                                        background: selected?.id === emp.id ? '#1e3a5f' : '#111827',
                                        border: `1px solid ${selected?.id === emp.id ? '#3b82f6' : '#2d3748'}`,
                                        transition: 'all 0.15s',
                                    }}
                                >
                                    <div>
                                        <div style={{ fontWeight: 600, color: '#e2e8f0', fontSize: 14 }}>{emp.name}</div>
                                        <div style={{ color: '#64748b', fontSize: 12 }}>{emp.email}</div>
                                    </div>
                                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                                        <ScoreBadge score={emp.trust_score} />
                                        {emp.agent_installed
                                            ? <span style={{ color: '#22c55e', fontSize: 11 }}>✅ Agent</span>
                                            : <span style={{ color: '#f59e0b', fontSize: 11 }}>⚠️ No Agent</span>
                                        }
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Activity panel */}
                        {selected && (
                            <div style={{ background: '#1a1f2e', border: '1px solid #2d3748', borderRadius: 12, padding: 20 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                                    <div>
                                        <h3 style={{ margin: 0, color: '#e2e8f0', fontSize: 15 }}>{selected.name}</h3>
                                        <p style={{ color: '#64748b', margin: '2px 0 0', fontSize: 12 }}>{selected.email}</p>
                                    </div>
                                    <button
                                        onClick={() => { setSelected(null); setActivity([]); }}
                                        style={{ background: 'none', border: '1px solid #2d3748', borderRadius: 6, color: '#64748b', cursor: 'pointer', padding: '2px 8px' }}
                                    >×</button>
                                </div>

                                <div style={{ color: '#64748b', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
                                    Recent Activity
                                </div>
                                {activity.length === 0
                                    ? <p style={{ color: '#374151', fontSize: 13 }}>No recent activity data.</p>
                                    : activity.map((ae, i) => (
                                        <div key={i} style={{
                                            background: '#111827', border: '1px solid #2d3748',
                                            borderRadius: 8, padding: '8px 12px', marginBottom: 6,
                                        }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                                <span style={{ color: '#93c5fd', fontSize: 12, fontWeight: 600 }}>
                                                    {ae.event_type}
                                                </span>
                                                <span style={{ color: '#4b5563', fontSize: 11 }}>
                                                    {timeSince(ae.received_at)}
                                                </span>
                                            </div>
                                            {ae.payload && (
                                                <div style={{ color: '#94a3b8', fontSize: 11, marginTop: 2, wordBreak: 'break-all' }}>
                                                    {JSON.stringify(ae.payload).slice(0, 80)}…
                                                </div>
                                            )}
                                        </div>
                                    ))
                                }
                            </div>
                        )}
                    </div>
                )}

                {/* Alerts tab */}
                {tab === 'alerts' && (
                    <div>
                        {alerts.length === 0
                            ? <div style={{ color: '#4b5563', textAlign: 'center', padding: '48px 0' }}>
                                <div style={{ fontSize: 40 }}>✅</div>
                                <p style={{ marginTop: 8 }}>No alerts — all team members are in good standing.</p>
                            </div>
                            : alerts.map(a => (
                                <div key={a.employee_id} style={{
                                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                    padding: '12px 16px', borderRadius: 10, marginBottom: 8,
                                    background: a.severity === 'critical' ? '#1a0a0a' : a.severity === 'warning' ? '#1a1500' : '#111827',
                                    border: `1px solid ${a.severity === 'critical' ? '#7f1d1d' : a.severity === 'warning' ? '#78350f' : '#2d3748'}`,
                                }}>
                                    <div>
                                        <div style={{ fontWeight: 600, color: '#e2e8f0', fontSize: 14 }}>{a.employee_name}</div>
                                        <div style={{ color: '#64748b', fontSize: 12 }}>{timeSince(a.score_time)}</div>
                                    </div>
                                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                                        <ScoreBadge score={a.total_score} />
                                        <span style={{
                                            fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
                                            color: a.severity === 'critical' ? '#ef4444' : a.severity === 'warning' ? '#f59e0b' : '#94a3b8',
                                        }}>
                                            {a.severity}
                                        </span>
                                    </div>
                                </div>
                            ))
                        }
                    </div>
                )}

                {/* Add Employee tab */}
                {tab === 'add' && (
                    <div style={{ background: '#1a1f2e', border: '1px solid #2d3748', borderRadius: 12, padding: '24px 32px', maxWidth: 500, margin: '0 auto' }}>
                        <h2 style={{ marginTop: 0, marginBottom: 20, fontSize: 18 }}>Onboard New Team Member</h2>
                        
                        {addMsg && <div style={{ background: '#064e3b', color: '#34d399', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: 14 }}>{addMsg}</div>}
                        {addError && <div style={{ background: '#7f1d1d', color: '#fca5a5', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: 14 }}>{addError}</div>}
                        
                        <form onSubmit={async (e) => {
                            e.preventDefault();
                            setAdding(true); setAddError(''); setAddMsg('');
                            try {
                                const payload = {
                                    ...addForm,
                                    department: user?.department_name || 'Unassigned',
                                };
                                const res = await fetch(`${API}/user/create-employee`, {
                                    method: 'POST',
                                    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
                                    body: JSON.stringify(payload)
                                });
                                if (!res.ok) {
                                    const d = await res.json().catch(()=>({}));
                                    throw new Error(d.detail || 'Failed to create employee');
                                }
                                setAddMsg(`✅ ${addForm.name} added successfully! Email instructions sent.`);
                                setAddForm({ name: '', email: '', send_email: true });
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
                                <label style={{ display: 'block', fontSize: 13, color: '#94a3b8', marginBottom: 6 }}>Department</label>
                                <input disabled value={user?.department_name || 'Retrieving...'} style={{ width: '100%', padding: '10px 12px', background: '#0f1117', border: '1px solid #374151', color: '#64748b', borderRadius: 6, boxSizing: 'border-box', opacity: 0.7 }} />
                                <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>Managers can only add employees to their assigned department.</div>
                            </div>
                            
                            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginBottom: 24, padding: '12px', background: '#0f1117', border: '1px solid #1e293b', borderRadius: 8 }}>
                                <input type="checkbox" checked={addForm.send_email} onChange={e=>setAddForm({...addForm, send_email: e.target.checked})} />
                                <div>
                                    <div style={{ fontSize: 14, color: '#e2e8f0', fontWeight: 600 }}>Send Setup Email</div>
                                    <div style={{ fontSize: 12, color: '#64748b' }}>Automatically emails the employee with the NEF Agent download link and onboarding instructions.</div>
                                </div>
                            </label>

                            <button disabled={adding} type="submit" style={{ width: '100%', padding: '12px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 700, cursor: adding ? 'wait' : 'pointer' }}>
                                {adding ? 'Creating...' : 'Create Employee'}
                            </button>
                        </form>
                    </div>
                )}
            </div>
        </div>
    );
}
