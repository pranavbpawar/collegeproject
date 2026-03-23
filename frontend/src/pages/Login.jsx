/**
 * TBAPS — Unified Login
 * Authenticates against /api/v1/auth/login for ALL roles (Admin, Manager, HR).
 * On success, stores token + user profile via AuthContext.
 */

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

const API_BASE = window.location.origin + '/api/v1';

const ROLE_HINTS = {
    admin:   { icon: '🛡️', color: '#3b82f6', label: 'Admin' },
    manager: { icon: '📊', color: '#22c55e', label: 'Manager' },
    hr:      { icon: '🧑‍💼', color: '#8b5cf6', label: 'HR' },
};

export default function Login({ onLogin }) {
    const { login } = useAuth();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading]   = useState(false);
    const [error, setError]       = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!username || !password) { setError('Enter username and password.'); return; }
        setLoading(true);
        setError('');

        try {
            const formBody = new URLSearchParams({ username, password });

            // Try unified login first (Manager / HR)
            let res = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formBody,
            });

            // Fallback to admin login
            if (!res.ok) {
                res = await fetch(`${API_BASE}/auth/admin/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: new URLSearchParams({ username, password }),
                });
            }

            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.detail || 'Invalid username or password');
            }

            const data = await res.json();
            const { access_token, role } = data;
            const userData = { username, role: role || 'admin' };
            login(access_token, userData);
            onLogin(access_token, userData);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    const inputStyle = {
        width: '100%', padding: '12px 14px', borderRadius: 8,
        background: '#111827', border: '1px solid #2d3748', color: '#e2e8f0',
        fontSize: 15, outline: 'none', boxSizing: 'border-box',
        transition: 'border-color 0.2s',
    };

    return (
        <div style={{
            minHeight: '100vh', background: '#0f1117',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: 'Inter, system-ui, sans-serif',
        }}>
            <div style={{
                background: '#1a1f2e', border: '1px solid #2d3748', borderRadius: 20,
                padding: '44px 40px', width: 400,
                boxShadow: '0 32px 80px rgba(0,0,0,0.6)',
            }}>
                {/* Header */}
                <div style={{ textAlign: 'center', marginBottom: 36 }}>
                    <div style={{ fontSize: 44, marginBottom: 12 }}>🛡️</div>
                    <h1 style={{
                        margin: 0, fontSize: 24, fontWeight: 800,
                        background: 'linear-gradient(90deg,#3b82f6,#8b5cf6)',
                        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                    }}>
                        TBAPS
                    </h1>
                    <p style={{ color: '#64748b', margin: '6px 0 0', fontSize: 13 }}>
                        Zero-Trust Employee Monitoring System
                    </p>
                </div>

                {/* Role hints */}
                <div style={{ display: 'flex', gap: 6, justifyContent: 'center', marginBottom: 28 }}>
                    {Object.entries(ROLE_HINTS).map(([role, info]) => (
                        <div key={role} style={{
                            background: info.color + '18',
                            border: `1px solid ${info.color}44`,
                            borderRadius: 8, padding: '4px 10px',
                            color: info.color, fontSize: 11, fontWeight: 600,
                        }}>
                            {info.icon} {info.label}
                        </div>
                    ))}
                </div>

                <form onSubmit={handleSubmit}>
                    <label style={{ color: '#94a3b8', fontSize: 12, display: 'block', marginBottom: 4 }}>
                        Username
                    </label>
                    <input
                        type="text"
                        value={username}
                        onChange={e => setUsername(e.target.value)}
                        placeholder="admin / manager / hr"
                        autoFocus
                        style={{ ...inputStyle, marginBottom: 16 }}
                        onFocus={e => (e.target.style.borderColor = '#3b82f6')}
                        onBlur={e => (e.target.style.borderColor = '#2d3748')}
                    />

                    <label style={{ color: '#94a3b8', fontSize: 12, display: 'block', marginBottom: 4 }}>
                        Password
                    </label>
                    <input
                        type="password"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        placeholder="••••••••"
                        style={{ ...inputStyle, marginBottom: 24 }}
                        onFocus={e => (e.target.style.borderColor = '#3b82f6')}
                        onBlur={e => (e.target.style.borderColor = '#2d3748')}
                    />

                    {error && (
                        <div style={{
                            background: '#2d1515', border: '1px solid #7f1d1d',
                            borderRadius: 8, padding: '10px 14px', color: '#fca5a5',
                            fontSize: 13, marginBottom: 16,
                        }}>
                            ⚠️ {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            width: '100%', padding: '13px', borderRadius: 10,
                            background: loading
                                ? '#1e3a5f'
                                : 'linear-gradient(135deg, #2563eb, #7c3aed)',
                            border: 'none', color: '#fff', fontSize: 15,
                            fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
                            transition: 'all 0.2s',
                            boxShadow: loading ? 'none' : '0 4px 20px rgba(59,130,246,0.4)',
                        }}
                    >
                        {loading ? '⏳ Signing in…' : '→ Sign In'}
                    </button>
                </form>

                <p style={{ color: '#374151', fontSize: 11, textAlign: 'center', marginTop: 24, lineHeight: 1.6 }}>
                    Default admin: <strong style={{ color: '#4b5563' }}>admin / Admin@1234</strong><br />
                    Change password after first login.
                </p>
            </div>
        </div>
    );
}
