/**
 * SendAgentModal
 * Admin UI to search employees and send the NEF Agent installer via email.
 * Calls:
 *   GET  /api/v1/admin/employees/search?q=...  — find employees
 *   POST /api/v1/admin/send-agent              — trigger email delivery
 *   GET  /api/v1/admin/send-logs               — audit history
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = window.location.origin + '/api/v1';

// ── Helpers ────────────────────────────────────────────────────────────────────

function getAuthToken() {
    return (
        localStorage.getItem('tbaps_token') ||
        localStorage.getItem('token') ||
        sessionStorage.getItem('tbaps_token') ||
        ''
    );
}

function authHeaders() {
    const token = getAuthToken();
    return token
        ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
        : { 'Content-Type': 'application/json' };
}

function timeSince(isoStr) {
    if (!isoStr) return '—';
    const secs = Math.floor((Date.now() - new Date(isoStr).getTime()) / 1000);
    if (secs < 60)   return `${secs}s ago`;
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
    if (secs < 86400)return `${Math.floor(secs / 3600)}h ago`;
    return `${Math.floor(secs / 86400)}d ago`;
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function AgentBadge({ installed }) {
    return (
        <span style={{
            display: 'inline-block',
            background: installed ? '#14532d' : '#1c1917',
            color: installed ? '#4ade80' : '#f59e0b',
            border: `1px solid ${installed ? '#16a34a' : '#92400e'}`,
            borderRadius: 12, padding: '2px 10px', fontSize: 11, fontWeight: 600,
        }}>
            {installed ? '✅ Agent Installed' : '⚠️ Not Installed'}
        </span>
    );
}

function EmployeeRow({ emp, selected, onSelect }) {
    const isSelected = selected?.id === emp.id;
    return (
        <div
            onClick={() => onSelect(isSelected ? null : emp)}
            style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '12px 16px', borderRadius: 10, cursor: 'pointer',
                background: isSelected ? '#1e3a5f' : '#111827',
                border: `1px solid ${isSelected ? '#3b82f6' : '#2d3748'}`,
                marginBottom: 8, transition: 'all 0.18s',
            }}
        >
            <div>
                <div style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 14 }}>{emp.name}</div>
                <div style={{ color: '#64748b', fontSize: 12, marginTop: 2 }}>
                    {emp.email}
                    {emp.department && (
                        <span style={{ marginLeft: 8, color: '#475569' }}>· {emp.department}</span>
                    )}
                </div>
            </div>
            <AgentBadge installed={emp.agent_installed} />
        </div>
    );
}

function AuditLog({ logs }) {
    if (!logs.length) {
        return (
            <p style={{ color: '#4b5563', fontSize: 13, textAlign: 'center', padding: '12px 0' }}>
                No sends recorded yet.
            </p>
        );
    }
    return (
        <div style={{ maxHeight: 220, overflowY: 'auto' }}>
            {logs.map(log => (
                <div key={log.id} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '8px 12px', borderRadius: 8, background: '#0f1117',
                    border: `1px solid ${log.status === 'sent' ? '#14532d' : '#450a0a'}`,
                    marginBottom: 6,
                }}>
                    <div>
                        <span style={{
                            color: log.status === 'sent' ? '#4ade80' : '#f87171',
                            fontSize: 11, fontWeight: 700, marginRight: 8,
                        }}>
                            {log.status === 'sent' ? '✅ SENT' : '❌ FAILED'}
                        </span>
                        <span style={{ color: '#94a3b8', fontSize: 13 }}>
                            {log.employee_name || log.employee_email}
                        </span>
                        {log.status === 'failed' && log.error_detail && (
                            <div style={{ color: '#ef4444', fontSize: 11, marginTop: 2 }}>
                                {log.error_detail.slice(0, 80)}
                            </div>
                        )}
                    </div>
                    <span style={{ color: '#4b5563', fontSize: 11, whiteSpace: 'nowrap', marginLeft: 8 }}>
                        {timeSince(log.sent_at)}
                    </span>
                </div>
            ))}
        </div>
    );
}

// ── Main Modal ─────────────────────────────────────────────────────────────────

export default function SendAgentModal({ onClose }) {
    const [query, setQuery]           = useState('');
    const [results, setResults]       = useState([]);
    const [selected, setSelected]     = useState(null);
    const [searching, setSearching]   = useState(false);
    const [sending, setSending]       = useState(false);
    const [toastMsg, setToastMsg]     = useState('');
    const [toastType, setToastType]   = useState('success'); // 'success' | 'error'
    const [logs, setLogs]             = useState([]);
    const [logsLoading, setLogsLoading] = useState(true);
    const [activeTab, setActiveTab]   = useState('search'); // 'search' | 'history'
    const debounceRef = useRef(null);

    // ── Fetch audit logs on open ───────────────────────────────────────────────
    const fetchLogs = useCallback(async () => {
        setLogsLoading(true);
        try {
            const res = await fetch(`${API_BASE}/admin/send-logs?limit=20`, {
                headers: authHeaders(),
            });
            if (res.ok) setLogs(await res.json());
        } catch { /* ignore */ }
        finally { setLogsLoading(false); }
    }, []);

    useEffect(() => { fetchLogs(); }, [fetchLogs]);

    // ── Debounced search ───────────────────────────────────────────────────────
    useEffect(() => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        if (query.trim().length < 2) {
            setResults([]);
            setSearching(false);
            return;
        }
        setSearching(true);
        debounceRef.current = setTimeout(async () => {
            try {
                const res = await fetch(
                    `${API_BASE}/admin/employees/search?q=${encodeURIComponent(query.trim())}&limit=20`,
                    { headers: authHeaders() },
                );
                if (res.ok) setResults(await res.json());
                else        setResults([]);
            } catch {
                setResults([]);
            } finally {
                setSearching(false);
            }
        }, 300);
        return () => clearTimeout(debounceRef.current);
    }, [query]);

    // ── Send action ────────────────────────────────────────────────────────────
    const handleSend = async () => {
        if (!selected) return;
        setSending(true);
        setToastMsg('');
        try {
            const res = await fetch(`${API_BASE}/admin/send-agent`, {
                method: 'POST',
                headers: authHeaders(),
                body: JSON.stringify({ employee_id: selected.id }),
            });
            const data = await res.json();
            if (res.ok && data.ok) {
                setToastType('success');
                setToastMsg(`✅ Agent email sent to ${selected.email}`);
                setSelected(null);
                setQuery('');
                setResults([]);
                await fetchLogs();
                setActiveTab('history');
            } else {
                throw new Error(data.detail || data.message || 'Send failed');
            }
        } catch (err) {
            setToastType('error');
            setToastMsg(`❌ ${err.message}`);
        } finally {
            setSending(false);
        }
    };

    // ── Styles ─────────────────────────────────────────────────────────────────
    const tabStyle = t => ({
        padding: '8px 20px', cursor: 'pointer', background: 'none', border: 'none',
        borderBottom: `2px solid ${activeTab === t ? '#3b82f6' : 'transparent'}`,
        color: activeTab === t ? '#3b82f6' : '#64748b',
        fontWeight: activeTab === t ? 700 : 400,
        fontSize: 13, transition: 'all 0.15s',
    });

    return (
        <div
            style={{
                position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                zIndex: 1000, backdropFilter: 'blur(4px)',
            }}
            onClick={onClose}
        >
            <div
                onClick={e => e.stopPropagation()}
                style={{
                    background: '#1a1f2e',
                    border: '1px solid #3b82f6',
                    borderRadius: 18,
                    padding: 0,
                    width: 520,
                    maxHeight: '90vh',
                    overflowY: 'auto',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.8), 0 0 0 1px #3b82f620',
                    display: 'flex',
                    flexDirection: 'column',
                }}
            >
                {/* ── Header ── */}
                <div style={{
                    background: 'linear-gradient(135deg,#1e3a5f,#0f2040)',
                    padding: '24px 28px 20px',
                    borderRadius: '18px 18px 0 0',
                    borderBottom: '1px solid #2d3748',
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                            <h2 style={{ margin: '0 0 4px', color: '#e2e8f0', fontSize: 20, fontWeight: 700 }}>
                                📧 Send NEF Agent via Email
                            </h2>
                            <p style={{ color: '#64748b', margin: 0, fontSize: 13 }}>
                                Search an employee and deliver the installer link securely.
                            </p>
                        </div>
                        <button
                            onClick={onClose}
                            style={{
                                background: 'none', border: '1px solid #2d3748', borderRadius: 8,
                                color: '#64748b', cursor: 'pointer', fontSize: 18,
                                padding: '2px 10px', lineHeight: 1.4,
                            }}
                        >
                            ×
                        </button>
                    </div>
                </div>

                {/* ── Tabs ── */}
                <div style={{
                    display: 'flex', borderBottom: '1px solid #2d3748',
                    background: '#151922', padding: '0 8px',
                }}>
                    <button style={tabStyle('search')} onClick={() => setActiveTab('search')}>
                        🔍 Search Employee
                    </button>
                    <button style={tabStyle('history')} onClick={() => setActiveTab('history')}>
                        📋 Audit Log
                    </button>
                </div>

                {/* ── Body ── */}
                <div style={{ padding: '24px 28px', flex: 1 }}>

                    {/* Toast */}
                    {toastMsg && (
                        <div style={{
                            background: toastType === 'success' ? '#14532d' : '#450a0a',
                            border: `1px solid ${toastType === 'success' ? '#16a34a' : '#b91c1c'}`,
                            borderRadius: 10, padding: '10px 16px', marginBottom: 16,
                            color: toastType === 'success' ? '#4ade80' : '#f87171',
                            fontSize: 13, fontWeight: 600,
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        }}>
                            {toastMsg}
                            <span
                                onClick={() => setToastMsg('')}
                                style={{ cursor: 'pointer', opacity: 0.6, fontSize: 16 }}
                            >×</span>
                        </div>
                    )}

                    {/* ── Search tab ── */}
                    {activeTab === 'search' && (
                        <>
                            {/* Search input */}
                            <div style={{ position: 'relative', marginBottom: 16 }}>
                                <span style={{
                                    position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
                                    color: '#4b5563', fontSize: 15,
                                }}>🔍</span>
                                <input
                                    autoFocus
                                    value={query}
                                    onChange={e => {
                                        setQuery(e.target.value);
                                        setSelected(null);
                                    }}
                                    placeholder="Search by name, email, or employee ID…"
                                    style={{
                                        width: '100%', padding: '11px 12px 11px 38px',
                                        borderRadius: 10, background: '#111827',
                                        border: '1px solid #2d3748', color: '#e2e8f0',
                                        fontSize: 14, outline: 'none', boxSizing: 'border-box',
                                        transition: 'border-color 0.15s',
                                    }}
                                    onFocus={e => (e.target.style.borderColor = '#3b82f6')}
                                    onBlur={e => (e.target.style.borderColor = '#2d3748')}
                                />
                                {searching && (
                                    <span style={{
                                        position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                                        color: '#3b82f6', fontSize: 12,
                                    }}>Searching…</span>
                                )}
                            </div>

                            {/* Results */}
                            {query.trim().length >= 2 && !searching && results.length === 0 && (
                                <p style={{ color: '#4b5563', fontSize: 13, textAlign: 'center', padding: '16px 0' }}>
                                    No employees found for "{query}"
                                </p>
                            )}

                            {results.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                    <div style={{ color: '#64748b', fontSize: 11, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
                                        {results.length} result{results.length !== 1 ? 's' : ''} — click to select
                                    </div>
                                    {results.map(emp => (
                                        <EmployeeRow
                                            key={emp.id}
                                            emp={emp}
                                            selected={selected}
                                            onSelect={setSelected}
                                        />
                                    ))}
                                </div>
                            )}

                            {query.trim().length < 2 && !results.length && (
                                <div style={{
                                    textAlign: 'center', padding: '32px 0',
                                    color: '#374151',
                                }}>
                                    <div style={{ fontSize: 40, marginBottom: 8 }}>👤</div>
                                    <p style={{ fontSize: 13, margin: 0 }}>
                                        Type at least 2 characters to search
                                    </p>
                                </div>
                            )}

                            {/* Selected preview + send button */}
                            {selected && (
                                <div style={{
                                    background: '#0f1117',
                                    border: '1px solid #3b82f6',
                                    borderRadius: 12,
                                    padding: '16px 20px',
                                    marginTop: 4,
                                }}>
                                    <div style={{ color: '#94a3b8', fontSize: 11, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
                                        Selected Employee
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                                        <div>
                                            <div style={{ color: '#e2e8f0', fontWeight: 700, fontSize: 15 }}>{selected.name}</div>
                                            <div style={{ color: '#64748b', fontSize: 13 }}>{selected.email}</div>
                                        </div>
                                        <AgentBadge installed={selected.agent_installed} />
                                    </div>

                                    <div style={{
                                        background: '#1a1a0e',
                                        border: '1px solid #78350f',
                                        borderRadius: 8, padding: '10px 14px',
                                        marginBottom: 14,
                                    }}>
                                        <p style={{ color: '#d97706', fontSize: 12, margin: 0, lineHeight: 1.6 }}>
                                            ✉️ An email with <strong>secure download links</strong> for the Linux (.deb)
                                            and Windows (.exe) NEF Agent will be sent to <strong>{selected.email}</strong>.
                                            This action will be audit-logged.
                                        </p>
                                    </div>

                                    <button
                                        onClick={handleSend}
                                        disabled={sending}
                                        style={{
                                            width: '100%', padding: '12px 0',
                                            background: sending
                                                ? '#1e3a5f'
                                                : 'linear-gradient(135deg,#2563eb,#3b82f6)',
                                            color: '#fff', border: 'none', borderRadius: 10,
                                            fontSize: 14, fontWeight: 700, cursor: sending ? 'not-allowed' : 'pointer',
                                            transition: 'all 0.2s',
                                            boxShadow: sending ? 'none' : '0 4px 16px rgba(59,130,246,0.35)',
                                        }}
                                    >
                                        {sending ? '⏳ Sending…' : '📧 Send NEF Agent Email'}
                                    </button>
                                </div>
                            )}
                        </>
                    )}

                    {/* ── Audit log tab ── */}
                    {activeTab === 'history' && (
                        <>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                                <span style={{ color: '#64748b', fontSize: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
                                    Recent Agent Sends
                                </span>
                                <button
                                    onClick={fetchLogs}
                                    style={{
                                        background: 'none', border: '1px solid #2d3748', borderRadius: 6,
                                        color: '#64748b', cursor: 'pointer', fontSize: 12, padding: '4px 10px',
                                    }}
                                >
                                    ↻ Refresh
                                </button>
                            </div>
                            {logsLoading
                                ? <p style={{ color: '#4b5563', fontSize: 13, textAlign: 'center' }}>Loading…</p>
                                : <AuditLog logs={logs} />
                            }
                        </>
                    )}
                </div>

                {/* ── Footer ── */}
                <div style={{
                    borderTop: '1px solid #2d3748', padding: '16px 28px',
                    background: '#111827', borderRadius: '0 0 18px 18px',
                    display: 'flex', justifyContent: 'flex-end',
                }}>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'transparent', border: '1px solid #2d3748',
                            borderRadius: 8, color: '#64748b', cursor: 'pointer',
                            fontSize: 13, padding: '8px 20px',
                        }}
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}
