/**
 * PeopleManagement — Unified Admin Dashboard Page
 * Manages Employees, Managers, and HR in a single interface.
 * Supports role-aware creation with flexible email control.
 */

import React, { useState, useEffect, useMemo } from 'react';

const ROLE_COLORS = {
    employee: { bg: '#0f4c2a', color: '#34d399', label: 'Employee' },
    manager:  { bg: '#1e3a5f', color: '#60a5fa', label: 'Manager'  },
    hr:       { bg: '#3b1f63', color: '#a78bfa', label: 'HR'       },
};

export default function PeopleManagement({ token }) {
    const [people, setPeople]           = useState([]);
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading]         = useState(true);
    const [message, setMessage]         = useState('');
    const [error, setError]             = useState('');
    const [submitting, setSubmitting]   = useState(false);

    // Filters
    const [filterRole, setFilterRole]   = useState('');
    const [filterDept, setFilterDept]   = useState('');

    // Form state
    const [form, setForm] = useState({
        name: '', email: '', role: 'employee', department: '',
        password: '', send_email: true, email_type: '',
    });

    const fetchPeople = async () => {
        try {
            const res = await fetch('/api/v1/admin/people', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) setPeople(await res.json());
        } catch (e) { console.error(e); }
    };

    const fetchDepartments = async () => {
        try {
            const res = await fetch('/api/v1/admin/departments', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) setDepartments(await res.json());
        } catch (e) { console.error(e); }
    };

    useEffect(() => {
        Promise.all([fetchPeople(), fetchDepartments()]).finally(() => setLoading(false));
    }, [token]);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
    };

    // Auto-set email_type when role changes
    const handleRoleChange = (e) => {
        const role = e.target.value;
        setForm(f => ({
            ...f,
            role,
            email_type: role === 'employee' ? 'employee_setup' : 'staff_notification',
        }));
    };

    const generatePassword = () => {
        const chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$';
        const pw = Array.from({ length: 12 }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
        setForm(f => ({ ...f, password: pw }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMessage(''); setError('');
        if (!form.name || !form.email || !form.department) {
            setError('Please fill all required fields.'); return;
        }
        if (form.role !== 'employee' && form.password.length < 8) {
            setError('Password must be at least 8 characters for Managers and HR.'); return;
        }
        setSubmitting(true);
        try {
            const payload = {
                name: form.name, email: form.email, role: form.role,
                department: form.department,
                password: form.password || undefined,
                send_email: form.send_email,
                email_type: form.email_type || undefined,
            };
            const res = await fetch('/api/v1/admin/create-user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Creation failed');
            setMessage('✅ ' + data.message);
            setForm({ name: '', email: '', role: 'employee', department: '', password: '', send_email: true, email_type: 'employee_setup' });
            fetchPeople();
            setTimeout(() => setMessage(''), 7000);
        } catch (err) {
            setError('❌ ' + err.message);
        } finally {
            setSubmitting(false);
        }
    };

    const handleDeactivate = async (person) => {
        // All roles use DELETE — employees go to /admin/employees/{id}, managers/HR to /admin/users/{id}
        const endpoint = person.role === 'employee'
            ? `/api/v1/admin/employees/${person.id}`
            : `/api/v1/admin/users/${person.id}`;

        const res = await fetch(endpoint, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (res.ok) {
            setMessage(`✅ ${person.name} has been successfully removed.`);
            setTimeout(() => setMessage(''), 5000);
            fetchPeople();
        } else {
            const d = await res.json();
            alert(d.detail || 'Action failed');
        }
    };

    // Apply filters
    const filtered = useMemo(() => people.filter(p => {
        if (filterRole && p.role !== filterRole) return false;
        if (filterDept && p.department?.toLowerCase() !== filterDept.toLowerCase()) return false;
        return true;
    }), [people, filterRole, filterDept]);

    const inp = {
        width: '100%', padding: '9px 13px', borderRadius: 7,
        background: '#0f172a', border: '1px solid #334155',
        color: '#e2e8f0', fontSize: 13, outline: 'none', boxSizing: 'border-box',
    };

    return (
        <div style={{ padding: 24, maxWidth: 1280, margin: '0 auto', color: '#e2e8f0', fontFamily: 'Inter, sans-serif' }}>
            <h2 style={{ fontSize: 26, marginBottom: 4, fontWeight: 700 }}>👥 People Management</h2>
            <p style={{ color: '#94a3b8', marginBottom: 28, fontSize: 14 }}>
                Unified view for creating and managing all Employees, Managers, and HR staff.
            </p>

            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'flex-start' }}>

                {/* ── Creation Form ── */}
                <div style={{ flex: '1 1 320px', background: '#1e293b', border: '1px solid #334155', borderRadius: 16, padding: 24 }}>
                    <h3 style={{ margin: '0 0 18px', fontSize: 16 }}>+ Add Person</h3>

                    {message && <div style={{ background: '#064e3b', color: '#34d399', padding: 12, borderRadius: 8, marginBottom: 14, fontSize: 13 }}>{message}</div>}
                    {error   && <div style={{ background: '#7f1d1d', color: '#fca5a5', padding: 12, borderRadius: 8, marginBottom: 14, fontSize: 13 }}>{error}</div>}

                    <form onSubmit={handleSubmit}>
                        <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Full Name *</label>
                        <input name="name" value={form.name} onChange={handleChange} placeholder="John Doe" style={{ ...inp, marginBottom: 12 }} />

                        <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Email *</label>
                        <input name="email" type="email" value={form.email} onChange={handleChange} placeholder="john@company.com" style={{ ...inp, marginBottom: 12 }} />

                        <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
                            <div style={{ flex: 1 }}>
                                <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Role *</label>
                                <select name="role" value={form.role} onChange={handleRoleChange} style={inp}>
                                    <option value="employee">Employee</option>
                                    <option value="manager">Manager</option>
                                    <option value="hr">HR</option>
                                </select>
                            </div>
                            <div style={{ flex: 1 }}>
                                <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Department *</label>
                                <select name="department" value={form.department} onChange={handleChange} style={inp}>
                                    <option value="">-- Select --</option>
                                    {departments.map(d => <option key={d.id} value={d.name}>{d.name}</option>)}
                                </select>
                            </div>
                        </div>

                        {form.role !== 'employee' && (
                            <>
                                <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Password *</label>
                                <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
                                    <input name="password" type="text" value={form.password} onChange={handleChange} placeholder="Min. 8 characters" style={{ ...inp, flex: 1 }} />
                                    <button type="button" onClick={generatePassword} title="Auto-generate" style={{ background: '#334155', border: 'none', borderRadius: 7, color: '#94a3b8', padding: '0 12px', cursor: 'pointer', fontSize: 16 }}>⚡</button>
                                </div>
                            </>
                        )}

                        {/* Email section */}
                        <div style={{ background: '#0f172a', borderRadius: 10, padding: '12px 14px', marginBottom: 16 }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13, color: '#cbd5e1', marginBottom: form.send_email ? 12 : 0 }}>
                                <input type="checkbox" name="send_email" checked={form.send_email} onChange={handleChange} style={{ width: 14, height: 14 }} />
                                Send Onboarding Email
                            </label>

                            {form.send_email && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 }}>
                                    <label style={{ display: 'flex', alignItems: 'flex-start', gap: 8, cursor: 'pointer' }}>
                                        <input type="radio" name="email_type" value="employee_setup"
                                            checked={form.email_type === 'employee_setup'}
                                            onChange={handleChange}
                                            disabled={form.role !== 'employee'}
                                            style={{ marginTop: 3 }}
                                        />
                                        <span style={{ fontSize: 12, color: form.role !== 'employee' ? '#475569' : '#94a3b8' }}>
                                            <strong style={{ color: form.role !== 'employee' ? '#475569' : '#e2e8f0' }}>Employee Setup Email</strong><br />
                                            NEF Agent download + installation instructions
                                        </span>
                                    </label>
                                    <label style={{ display: 'flex', alignItems: 'flex-start', gap: 8, cursor: 'pointer' }}>
                                        <input type="radio" name="email_type" value="staff_notification"
                                            checked={form.email_type === 'staff_notification'}
                                            onChange={handleChange}
                                            disabled={form.role === 'employee'}
                                            style={{ marginTop: 3 }}
                                        />
                                        <span style={{ fontSize: 12, color: form.role === 'employee' ? '#475569' : '#94a3b8' }}>
                                            <strong style={{ color: form.role === 'employee' ? '#475569' : '#e2e8f0' }}>Staff Notification Email</strong><br />
                                            Login credentials + dashboard access link
                                        </span>
                                    </label>
                                </div>
                            )}
                        </div>

                        <button type="submit" disabled={submitting} style={{
                            width: '100%', padding: '11px', background: submitting ? '#334155' : '#3b82f6',
                            border: 'none', borderRadius: 8, color: '#fff', fontWeight: 600,
                            fontSize: 14, cursor: submitting ? 'not-allowed' : 'pointer',
                        }}>
                            {submitting ? 'Creating...' : '+ Create User'}
                        </button>
                    </form>
                </div>

                {/* ── People Table ── */}
                <div style={{ flex: '2 1 600px', background: '#1e293b', border: '1px solid #334155', borderRadius: 16, padding: 24 }}>
                    {/* Header */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>
                        <h3 style={{ margin: 0, fontSize: 16 }}>All People ({filtered.length})</h3>
                        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                            <select value={filterRole} onChange={e => setFilterRole(e.target.value)}
                                style={{ ...inp, width: 'auto', padding: '6px 10px', fontSize: 12 }}>
                                <option value="">All Roles</option>
                                <option value="employee">Employee</option>
                                <option value="manager">Manager</option>
                                <option value="hr">HR</option>
                            </select>
                            <select value={filterDept} onChange={e => setFilterDept(e.target.value)}
                                style={{ ...inp, width: 'auto', padding: '6px 10px', fontSize: 12 }}>
                                <option value="">All Depts</option>
                                {departments.map(d => <option key={d.id} value={d.name}>{d.name}</option>)}
                            </select>
                            <button onClick={() => { fetchPeople(); }}
                                style={{ background: 'transparent', border: '1px solid #475569', color: '#94a3b8', padding: '6px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
                                🔄 Refresh
                            </button>
                        </div>
                    </div>

                    {loading ? (
                        <div style={{ textAlign: 'center', padding: 40, color: '#64748b' }}>Loading...</div>
                    ) : (
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid #2d3748', color: '#64748b', textAlign: 'left' }}>
                                        <th style={{ padding: '10px 8px' }}>Name</th>
                                        <th style={{ padding: '10px 8px' }}>Email</th>
                                        <th style={{ padding: '10px 8px' }}>Role</th>
                                        <th style={{ padding: '10px 8px' }}>Department</th>
                                        <th style={{ padding: '10px 8px' }}>Status</th>
                                        <th style={{ padding: '10px 8px', textAlign: 'right' }}>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filtered.length === 0 ? (
                                        <tr><td colSpan="6" style={{ textAlign: 'center', padding: 32, color: '#475569' }}>No people found.</td></tr>
                                    ) : filtered.map(p => {
                                        const roleStyle = ROLE_COLORS[p.role] || ROLE_COLORS.employee;
                                        return (
                                            <tr key={p.id} style={{ borderBottom: '1px solid #1e293b' }}>
                                                <td style={{ padding: '12px 8px', fontWeight: 500 }}>{p.name}</td>
                                                <td style={{ padding: '12px 8px', color: '#94a3b8', fontSize: 12 }}>{p.email}</td>
                                                <td style={{ padding: '12px 8px' }}>
                                                    <span style={{ background: roleStyle.bg, color: roleStyle.color, padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
                                                        {roleStyle.label}
                                                    </span>
                                                </td>
                                                <td style={{ padding: '12px 8px', color: '#94a3b8', fontSize: 12 }}>{p.department || '—'}</td>
                                                <td style={{ padding: '12px 8px' }}>
                                                    {p.status_active
                                                        ? <span style={{ color: '#34d399', fontSize: 11 }}>● Active</span>
                                                        : <span style={{ color: '#f59e0b', fontSize: 11 }}>● Inactive</span>
                                                    }
                                                </td>
                                                <td style={{ padding: '12px 8px', textAlign: 'right' }}>
                                                    <button
                                                        onClick={() => handleDeactivate(p)}
                                                        style={{ background: 'transparent', border: '1px solid #7f1d1d', color: '#ef4444', padding: '4px 10px', borderRadius: 5, cursor: 'pointer', fontSize: 11 }}
                                                        onMouseOver={e => e.currentTarget.style.background = '#7f1d1d55'}
                                                        onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                                                    >Remove</button>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
