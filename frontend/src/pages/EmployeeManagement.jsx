/**
 * Employee Management Feature
 * Admin Dashboard child page for creating and managing monitored Employee accounts.
 */

import React, { useState, useEffect } from 'react';

export default function EmployeeManagement({ token }) {
    const [employees, setEmployees] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');

    // Form state for creating an Employee
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        department: '',
    });

    const fetchEmployees = async () => {
        try {
            const res = await fetch('/api/v1/admin/employees', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                setEmployees(await res.json());
            }
        } catch (err) {
            console.error(err);
        }
    };

    const fetchDepartments = async () => {
        try {
            const res = await fetch('/api/v1/admin/departments', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                setDepartments(await res.json());
            }
        } catch (err) {
            console.error(err);
        }
    };

    const loadData = async () => {
        setLoading(true);
        await Promise.all([fetchEmployees(), fetchDepartments()]);
        setLoading(false);
    };

    useEffect(() => {
        loadData();
    }, [token]);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        setMessage('');
        setError('');

        if (!formData.name || !formData.email || !formData.department) {
            setError('Please fill all fields');
            return;
        }

        try {
            const res = await fetch('/api/v1/admin/create-employee', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(formData),
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || 'Failed to create employee');
            }

            setMessage('✅ ' + data.message + ' (Onboarding email queued)');
            setFormData({ name: '', email: '', department: '' });
            fetchEmployees(); // Refresh list
            
            // Auto hide message
            setTimeout(() => setMessage(''), 6000);
        } catch (err) {
            setError('❌ ' + err.message);
        }
    };

    const handleDelete = async (id, name) => {
        try {
            const res = await fetch(`/api/v1/admin/employees/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                alert(`✅ Successfully removed ${name} from Active Tracking.`);
                fetchEmployees();
            } else {
                const data = await res.json();
                alert(data.detail || "Deletion failed...");
            }
        } catch (err) {
            console.error(err);
            alert("Error: " + err.message);
        }
    };

    const inputStyle = {
        width: '100%', padding: '10px 14px', borderRadius: 8,
        background: '#111827', border: '1px solid #2d3748',
        color: '#e2e8f0', fontSize: 14, outline: 'none',
        boxSizing: 'border-box', marginBottom: 16
    };

    return (
        <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto', color: '#e2e8f0', fontFamily: 'Inter, sans-serif' }}>
            <h2 style={{ fontSize: 28, marginBottom: 8, fontWeight: 700 }}>👨‍💻 Employee Management</h2>
            <p style={{ color: '#94a3b8', marginBottom: 32 }}>Onboard network participants and revoke NEF Agent accesses.</p>

            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'flex-start' }}>
                
                {/* Create Form */}
                <div style={{
                    flex: '1 1 350px', background: '#1e293b', border: '1px solid #334155',
                    borderRadius: 16, padding: 24,
                }}>
                    <h3 style={{ marginTop: 0, marginBottom: 20, color: '#f8fafc' }}>Onboard Employee</h3>
                    
                    {message && <div style={{ background: '#064e3b', color: '#34d399', padding: '12px', borderRadius: 8, marginBottom: 16, fontSize: 13 }}>{message}</div>}
                    {error && <div style={{ background: '#7f1d1d', color: '#fca5a5', padding: '12px', borderRadius: 8, marginBottom: 16, fontSize: 13 }}>{error}</div>}

                    <form onSubmit={handleCreate}>
                        <label style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4, display: 'block' }}>Full Name</label>
                        <input type="text" name="name" value={formData.name} onChange={handleChange} placeholder="e.g. John Doe" style={inputStyle} />

                        <label style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4, display: 'block' }}>Email</label>
                        <input type="email" name="email" value={formData.email} onChange={handleChange} placeholder="john@company.com" style={inputStyle} />

                        <label style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4, display: 'block' }}>Department</label>
                        <select name="department" value={formData.department} onChange={handleChange} style={inputStyle}>
                            <option value="">-- Select Department --</option>
                            {departments.map(d => <option key={d.id} value={d.name}>{d.name}</option>)}
                        </select>

                        <button type="submit" style={{
                            width: '100%', padding: '12px', background: '#10b981', border: 'none',
                            borderRadius: 8, color: '#fff', fontWeight: 600, fontSize: 14, cursor: 'pointer',
                            marginTop: 8, boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
                        }}>
                            + Send Onboarding Invite
                        </button>
                    </form>
                </div>

                {/* Employee List Table */}
                <div style={{
                    flex: '2 1 600px', background: '#1e293b', border: '1px solid #334155',
                    borderRadius: 16, padding: 24, overflow: 'hidden'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                        <h3 style={{ margin: 0, color: '#f8fafc' }}>Monitored Personnel ({employees.length})</h3>
                        <button onClick={fetchEmployees} style={{ background: 'transparent', border: '1px solid #475569', color: '#cbd5e1', padding: '6px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>
                            🔄 Refresh
                        </button>
                    </div>

                    {loading ? (
                        <div style={{ textAlign: 'center', padding: 40, color: '#64748b' }}>Loading data...</div>
                    ) : (
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', textAlign: 'left' }}>
                                        <th style={{ padding: '12px 0', fontWeight: 600 }}>Name</th>
                                        <th style={{ padding: '12px 0', fontWeight: 600 }}>Email</th>
                                        <th style={{ padding: '12px 0', fontWeight: 600 }}>Department</th>
                                        <th style={{ padding: '12px 0', fontWeight: 600 }}>Status</th>
                                        <th style={{ padding: '12px 0', fontWeight: 600, textAlign: 'right' }}>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {employees.length === 0 ? (
                                        <tr><td colSpan="5" style={{ textAlign: 'center', padding: 32, color: '#64748b' }}>No employees found.</td></tr>
                                    ) : employees.map(m => (
                                        <tr key={m.id} style={{ borderBottom: '1px solid #334155' }}>
                                            <td style={{ padding: '14px 0', fontWeight: 500 }}>{m.name}</td>
                                            <td style={{ padding: '14px 0', color: '#cbd5e1' }}>{m.email}</td>
                                            <td style={{ padding: '14px 0' }}>
                                                <span style={{ background: '#3b82f622', color: '#60a5fa', padding: '4px 8px', borderRadius: 4, fontSize: 12, fontWeight: 500 }}>
                                                    {m.department || 'Unassigned'}
                                                </span>
                                            </td>
                                            <td style={{ padding: '14px 0' }}>
                                                {m.status === 'active' ? 
                                                    <span style={{ color: '#34d399', fontSize: 12 }}>● Active</span> : 
                                                    <span style={{ color: '#f59e0b', fontSize: 12 }}>● {m.status || 'Unknown'}</span>
                                                }
                                            </td>
                                            <td style={{ padding: '14px 0', textAlign: 'right' }}>
                                                <button 
                                                    onClick={() => handleDelete(m.id, m.name)}
                                                    title="Permanently Remove Access"
                                                    style={{ background: 'transparent', border: '1px solid #7f1d1d', color: '#ef4444', padding: '4px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 12, transition: '0.2s' }}
                                                    onMouseOver={e => e.target.style.background = '#7f1d1d44'}
                                                    onMouseOut={e => e.target.style.background = 'transparent'}
                                                >
                                                    Remove
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
