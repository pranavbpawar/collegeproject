/**
 * NEF Admin Agents Dashboard
 * Real-time monitoring of all employee machines via the NEF agent.
 * Shows online/offline status, latest events, screenshot gallery,
 * and a "Create Agent Package" button to generate employee install ZIPs.
 */

import React, { useState, useEffect, useCallback } from 'react';
import SendAgentModal from './SendAgentModal';

const API_BASE = window.location.origin + '/api/v1';
const REFRESH_MS = 15000;

// ── Helpers ────────────────────────────────────────────────────────────────────

function timeSince(isoStr) {
    if (!isoStr) return 'never';
    const secs = Math.floor((Date.now() - new Date(isoStr).getTime()) / 1000);
    if (secs < 60) return `${secs}s ago`;
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
    return `${Math.floor(secs / 3600)}h ago`;
}

const btn = (extra = {}) => ({
    border: '1px solid #3b82f6', borderRadius: 8, padding: '7px 16px',
    cursor: 'pointer', fontSize: 13, transition: 'all 0.2s', ...extra,
});

// ── Create Package Modal ────────────────────────────────────────────────────────

function CreatePackageModal({ onClose }) {
    const [name, setName] = useState('');
    const [loadingDeb, setLDeb] = useState(false);
    const [loadingExe, setLExe] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const download = async (endpoint, filename, setLoading) => {
        if (!name.trim()) { setError('Please enter an employee name.'); return; }
        setLoading(true); setError(''); setSuccess('');
        try {
            const res = await fetch(`${API_BASE}/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    employee_name: name.trim(),
                    server_url: window.location.origin,
                }),
            });
            if (!res.ok) {
                const txt = await res.text();
                throw new Error(txt);
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename(name.trim().replace(/\s+/g, '-').toLowerCase());
            a.click();
            URL.revokeObjectURL(url);
            setSuccess(`✅ Downloaded! Send the file to ${name.trim()}.`);
        } catch (e) {
            setError(`Failed: ${e.message}`);
        } finally {
            setLoading(false);
        }
    };

    const card = (icon, title, sub, color) => ({
        border: `1px solid ${color}22`,
        borderRadius: 10, padding: '14px 16px', marginBottom: 12,
        background: `${color}08`,
    });

    return (
        <div style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999,
        }} onClick={onClose}>
            <div onClick={e => e.stopPropagation()} style={{
                background: '#1a1f2e', border: '1px solid #3b82f6', borderRadius: 16,
                padding: 32, width: 480, boxShadow: '0 24px 64px rgba(0,0,0,0.7)',
            }}>
                <h2 style={{ margin: '0 0 4px', color: '#e2e8f0', fontSize: 20 }}>
                    🖥️ Deploy Agent to Employee
                </h2>
                <p style={{ color: '#64748b', margin: '0 0 20px', fontSize: 13 }}>
                    Generate a one-click installer. Just send the file to the employee.
                </p>

                {/* Name input */}
                <label style={{ color: '#94a3b8', fontSize: 12, display: 'block', marginBottom: 4 }}>
                    Employee Name
                </label>
                <input
                    value={name}
                    onChange={e => { setName(e.target.value); setError(''); setSuccess(''); }}
                    placeholder="e.g. John Smith"
                    autoFocus
                    style={{
                        width: '100%', padding: '10px 12px', borderRadius: 8,
                        background: '#111827', border: '1px solid #2d3748', color: '#e2e8f0',
                        fontSize: 14, outline: 'none', boxSizing: 'border-box', marginBottom: 20,
                    }}
                />

                {/* Linux .deb card */}
                <div style={card('🐧', '', '', '#22c55e')}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <div style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 15 }}>
                                🐧 Linux Installer <span style={{ color: '#22c55e', fontSize: 11, fontWeight: 400 }}>.deb</span>
                            </div>
                            <div style={{ color: '#64748b', fontSize: 12, marginTop: 2 }}>
                                Ubuntu, Debian, Kali, Linux Mint
                            </div>
                            <code style={{ color: '#4ade80', fontSize: 11, background: '#0a0f1a', padding: '2px 8px', borderRadius: 4, marginTop: 4, display: 'inline-block' }}>
                                sudo dpkg -i nef-agent.deb
                            </code>
                        </div>
                        <button
                            onClick={() => download('agent/download-deb', n => `nef-agent-${n}.deb`, setLDeb)}
                            disabled={loadingDeb}
                            style={{
                                ...btn({ background: loadingDeb ? '#15532e' : '#16a34a', color: '#fff', borderColor: '#16a34a', padding: '8px 16px', whiteSpace: 'nowrap' }),
                            }}>
                            {loadingDeb ? '⏳ Building…' : '⬇ Download .deb'}
                        </button>
                    </div>
                </div>

                {/* Windows .exe card */}
                <div style={card('🪟', '', '', '#3b82f6')}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <div style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 15 }}>
                                🪟 Windows Installer <span style={{ color: '#60a5fa', fontSize: 11, fontWeight: 400 }}>.exe</span>
                            </div>
                            <div style={{ color: '#64748b', fontSize: 12, marginTop: 2 }}>
                                Windows 10 / 11
                            </div>
                            <code style={{ color: '#93c5fd', fontSize: 11, background: '#0a0f1a', padding: '2px 8px', borderRadius: 4, marginTop: 4, display: 'inline-block' }}>
                                Extract ZIP → double-click install.bat
                            </code>
                        </div>
                        <button
                            onClick={() => download('agent/download-exe', n => `nef-agent-${n}-windows.zip`, setLExe)}
                            disabled={loadingExe}
                            style={{
                                ...btn({ background: loadingExe ? '#1e3a5f' : '#2563eb', color: '#fff', borderColor: '#2563eb', padding: '8px 16px', whiteSpace: 'nowrap' }),
                            }}>
                            {loadingExe ? '⏳ Building…' : '⬇ Download .exe'}
                        </button>
                    </div>
                </div>

                {error && <p style={{ color: '#ef4444', fontSize: 12, margin: '8px 0 0' }}>{error}</p>}
                {success && <p style={{ color: '#22c55e', fontSize: 12, margin: '8px 0 0' }}>{success}</p>}

                <button onClick={onClose} style={{ ...btn({ width: '100%', marginTop: 16, background: 'transparent', color: '#64748b', borderColor: '#2d3748' }) }}>
                    Close
                </button>
            </div>
        </div>
    );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StatusDot({ status }) {
    return (
        <span style={{
            display: 'inline-block', width: 10, height: 10, borderRadius: '50%',
            background: status === 'online' ? '#22c55e' : '#ef4444',
            boxShadow: status === 'online' ? '0 0 6px #22c55e' : 'none',
            marginRight: 6,
        }} />
    );
}

function AgentCard({ agent, selected, onClick }) {
    return (
        <div onClick={() => onClick(agent)} style={{
            background: selected ? '#1e3a5f' : '#1a1f2e',
            border: `1px solid ${selected ? '#3b82f6' : '#2d3748'}`,
            borderRadius: 10, padding: '14px 16px', cursor: 'pointer',
            transition: 'all 0.2s', marginBottom: 10,
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <StatusDot status={agent.status} />
                    <strong style={{ color: '#e2e8f0', fontSize: 15 }}>{agent.hostname}</strong>
                    <span style={{ color: '#64748b', fontSize: 12, marginLeft: 8 }}>{agent.username || ''}</span>
                </div>
                <span style={{ color: '#94a3b8', fontSize: 12 }}>{timeSince(agent.last_seen)}</span>
            </div>
            <div style={{ color: '#64748b', fontSize: 12, marginTop: 4 }}>
                {agent.os} · {agent.ip_address}
            </div>
        </div>
    );
}

function EventFeed({ events }) {
    const typeColors = {
        processes: '#8b5cf6', active_window: '#3b82f6', idle: '#f59e0b',
        usb_devices: '#ec4899', file_activity: '#10b981', websites: '#06b6d4',
        sysinfo: '#64748b', screenshot: '#f97316',
    };
    return (
        <div style={{ maxHeight: 320, overflowY: 'auto' }}>
            {events.length === 0 && <p style={{ color: '#64748b', textAlign: 'center' }}>No events yet</p>}
            {events.map((ev, i) => (
                <div key={i} style={{
                    borderLeft: `3px solid ${typeColors[ev.event_type] || '#64748b'}`,
                    padding: '6px 12px', marginBottom: 6, background: '#111827', borderRadius: '0 6px 6px 0',
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: typeColors[ev.event_type] || '#94a3b8', fontSize: 12, fontWeight: 600 }}>
                            {ev.event_type}
                        </span>
                        <span style={{ color: '#4b5563', fontSize: 11 }}>{timeSince(ev.received_at)}</span>
                    </div>
                    <div style={{ color: '#94a3b8', fontSize: 12, marginTop: 2, wordBreak: 'break-all' }}>
                        {JSON.stringify(ev.payload).slice(0, 120)}…
                    </div>
                </div>
            ))}
        </div>
    );
}

function Screenshots({ screenshots }) {
    return (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {screenshots.length === 0 && <p style={{ color: '#64748b' }}>No screenshots yet</p>}
            {screenshots.map(ss => (
                <a key={ss.id} href={API_BASE + '/admin/screenshots/' + ss.id} target="_blank" rel="noreferrer">
                    <img
                        src={API_BASE + '/admin/screenshots/' + ss.id}
                        alt={ss.taken_at}
                        style={{ width: 160, height: 100, objectFit: 'cover', borderRadius: 6, border: '1px solid #2d3748', cursor: 'zoom-in' }}
                        title={`Taken: ${new Date(ss.taken_at).toLocaleString()}`}
                    />
                </a>
            ))}
        </div>
    );
}

function AgentDetail({ agent }) {
    const [events, setEvents] = useState([]);
    const [screenshots, setScreenshots] = useState([]);
    const [detail, setDetail] = useState(null);
    const [activeTab, setActiveTab] = useState('overview');

    useEffect(() => {
        if (!agent) return;
        const id = agent.id;
        fetch(`${API_BASE}/admin/agents/${id}`).then(r => r.json()).then(setDetail).catch(() => { });
        fetch(`${API_BASE}/admin/events?agent_id=${id}&limit=50`).then(r => r.json()).then(setEvents).catch(() => { });
        fetch(`${API_BASE}/admin/agents/${id}/screenshots?limit=20`).then(r => r.json()).then(setScreenshots).catch(() => { });
    }, [agent?.id]);

    if (!agent) return null;

    const tabs = ['overview', 'events', 'screenshots'];
    const tabStyle = (t) => ({
        padding: '8px 16px', cursor: 'pointer', background: 'none',
        border: 'none', borderBottom: `2px solid ${activeTab === t ? '#3b82f6' : 'transparent'}`,
        color: activeTab === t ? '#3b82f6' : '#94a3b8', fontWeight: activeTab === t ? 600 : 400,
    });
    const sysinfo = detail?.latest_events?.sysinfo?.payload || {};

    return (
        <div style={{ background: '#1a1f2e', borderRadius: 12, padding: 20, border: '1px solid #2d3748' }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
                <StatusDot status={agent.status} />
                <h2 style={{ color: '#e2e8f0', margin: 0, fontSize: 20 }}>{agent.hostname}</h2>
                <span style={{ color: '#64748b', marginLeft: 12, fontSize: 13 }}>
                    {agent.os} · {agent.ip_address} · {agent.mac_address}
                </span>
            </div>

            <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid #2d3748' }}>
                {tabs.map(t => <button key={t} style={tabStyle(t)} onClick={() => setActiveTab(t)}>{t}</button>)}
            </div>

            {activeTab === 'overview' && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
                    {[
                        ['CPU', sysinfo.cpu_percent != null ? `${sysinfo.cpu_percent}%` : '—'],
                        ['RAM', sysinfo.ram_percent != null ? `${sysinfo.ram_percent}%` : '—'],
                        ['Disk', sysinfo.disk_percent != null ? `${sysinfo.disk_percent}%` : '—'],
                        ['IP', agent.ip_address || '—'],
                        ['OS', agent.os || '—'],
                        ['Last seen', timeSince(agent.last_seen)],
                        ['First seen', new Date(agent.first_seen).toLocaleDateString()],
                        ['Username', agent.username || '—'],
                    ].map(([label, val]) => (
                        <div key={label} style={{ background: '#111827', borderRadius: 8, padding: '10px 14px' }}>
                            <div style={{ color: '#64748b', fontSize: 11 }}>{label}</div>
                            <div style={{ color: '#e2e8f0', fontSize: 16, fontWeight: 600 }}>{val}</div>
                        </div>
                    ))}
                </div>
            )}
            {activeTab === 'events' && <EventFeed events={events} />}
            {activeTab === 'screenshots' && <Screenshots screenshots={screenshots} />}
        </div>
    );
}

// ── Main Page ───────────────────────────────────────────────────────────────────

export default function AdminAgents() {
    const [agents, setAgents] = useState([]);
    const [selected, setSelected] = useState(null);
    const [loading, setLoading] = useState(true);
    const [lastRefresh, setLastRefresh] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [showSendModal, setShowSendModal] = useState(false);

    const fetchAgents = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/admin/agents`);
            const data = await res.json();
            setAgents(data);
            setLastRefresh(new Date());
        } catch (e) { /* keep old data */ }
        finally { setLoading(false); }
    }, []);

    useEffect(() => {
        fetchAgents();
        const iv = setInterval(fetchAgents, REFRESH_MS);
        return () => clearInterval(iv);
    }, [fetchAgents]);

    const online = agents.filter(a => a.status === 'online').length;
    const offline = agents.filter(a => a.status === 'offline').length;

    return (
        <div style={{ minHeight: '100vh', background: '#0f1117', color: '#e2e8f0', fontFamily: 'Inter, system-ui, sans-serif', padding: 24 }}>

            {showModal && <CreatePackageModal onClose={() => setShowModal(false)} />}
            {showSendModal && <SendAgentModal onClose={() => setShowSendModal(false)} />}

            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <div>
                    <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, background: 'linear-gradient(90deg,#3b82f6,#8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                        🖥 NEF Agent Monitor
                    </h1>
                    <p style={{ color: '#64748b', margin: '4px 0 0', fontSize: 13 }}>
                        Admin — real-time employee machine monitoring
                    </p>
                </div>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <span style={{ color: '#22c55e', fontSize: 13 }}>● {online} online</span>
                    <span style={{ color: '#ef4444', fontSize: 13 }}>● {offline} offline</span>
                    <button onClick={fetchAgents} style={{ ...btn({ background: '#1e3a5f', color: '#3b82f6' }) }}>
                        ↻ Refresh
                    </button>
                    <button
                        onClick={() => setShowSendModal(true)}
                        style={{ ...btn({ background: '#0f2040', borderColor: '#3b82f6', color: '#93c5fd', fontWeight: 600 }) }}
                    >
                        📧 Send Agent via Email
                    </button>
                    <button onClick={() => setShowModal(true)} style={{ ...btn({ background: '#16a34a', borderColor: '#16a34a', color: '#fff', fontWeight: 600 }) }}>
                        ➕ Create Agent Package
                    </button>
                </div>
            </div>

            {loading && <p style={{ color: '#64748b' }}>Loading agents…</p>}

            <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 20 }}>
                {/* Agent list */}
                <div>
                    <div style={{ color: '#64748b', fontSize: 12, marginBottom: 8 }}>
                        {agents.length} agents registered
                        {lastRefresh && ` · refreshed ${timeSince(lastRefresh.toISOString())}`}
                    </div>
                    {agents.map(a => (
                        <AgentCard key={a.id} agent={a} selected={selected?.id === a.id} onClick={setSelected} />
                    ))}
                    {!loading && agents.length === 0 && (
                        <div style={{ color: '#64748b', textAlign: 'center', padding: 40 }}>
                            <p style={{ fontSize: 32 }}>🖥️</p>
                            <p>No agents registered yet.</p>
                            <button onClick={() => setShowModal(true)} style={{ ...btn({ background: '#16a34a', borderColor: '#16a34a', color: '#fff', marginTop: 8 }) }}>
                                ➕ Create First Agent Package
                            </button>
                        </div>
                    )}
                </div>

                {/* Detail panel */}
                <div>
                    {selected
                        ? <AgentDetail agent={selected} />
                        : <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 400, color: '#4b5563', fontSize: 14, gap: 16 }}>
                            <p>Select an agent from the list to view details</p>
                            <button onClick={() => setShowModal(true)} style={{ ...btn({ background: '#16a34a', borderColor: '#16a34a', color: '#fff' }) }}>
                                ➕ Create Agent Package
                            </button>
                        </div>
                    }
                </div>
            </div>
        </div>
    );
}
