/**
 * DetailPanel Component
 * Shows detailed employee trust score breakdown
 */

import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import CircleChart from './CircleChart';
import { getScoreColor } from '../utils/scoreUtils';
import './DetailPanel.css';

export default function DetailPanel({ employee, onClose }) {
    if (!employee) return null;

    const components = [
        { name: 'Outcome Reliability', score: employee.outcome_score, weight: '35%', icon: '📋' },
        { name: 'Behavioral Consistency', score: employee.behavioral_score, weight: '30%', icon: '🎯' },
        { name: 'Security Hygiene', score: employee.security_score, weight: '20%', icon: '🔒' },
        { name: 'Psychological Wellbeing', score: employee.wellbeing_score, weight: '15%', icon: '💚' }
    ];

    return (
        <div className="detail-panel">
            <div className="detail-header">
                <div className="detail-title">
                    <h2>{employee.name}</h2>
                    <p className="detail-subtitle">{employee.email} • {employee.department}</p>
                </div>
                <button className="btn-close" onClick={onClose} aria-label="Close">
                    ✕
                </button>
            </div>

            {/* Overall Score */}
            <div className="overall-score">
                <div className="score-display">
                    <div
                        className="score-circle"
                        style={{
                            background: `conic-gradient(
                ${getScoreColor(employee.trust_score)} 0deg ${(employee.trust_score / 100) * 360}deg,
                #e0e0e0 ${(employee.trust_score / 100) * 360}deg 360deg
              )`
                        }}
                    >
                        <div className="score-inner">
                            <div className="score-number">{employee.trust_score.toFixed(1)}</div>
                            <div className="score-label">Trust Score</div>
                        </div>
                    </div>
                </div>
                <div className="score-info">
                    <h3>Overall Trust Score</h3>
                    <p>Based on 4 weighted components over the last 30 days</p>
                    {employee.time_decay_factor && (
                        <p className="decay-info">
                            Time decay factor: {(employee.time_decay_factor * 100).toFixed(0)}%
                        </p>
                    )}
                </div>
            </div>

            {/* Component Breakdown */}
            <div className="component-breakdown">
                <h3>Component Breakdown</h3>
                <div className="component-grid">
                    {components.map(comp => (
                        <div key={comp.name} className="component-card">
                            <div className="component-header">
                                <span className="component-icon">{comp.icon}</span>
                                <div className="component-info">
                                    <h4>{comp.name}</h4>
                                    <span className="component-weight">Weight: {comp.weight}</span>
                                </div>
                            </div>
                            <CircleChart value={comp.score} size={120} />
                        </div>
                    ))}
                </div>
            </div>

            {/* 30-Day Trend */}
            {employee.trend_30day && employee.trend_30day.length > 0 && (
                <div className="trend-section">
                    <h3>30-Day Trust Score Trend</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={employee.trend_30day}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                            <XAxis
                                dataKey="date"
                                stroke="#666"
                                tick={{ fontSize: 12 }}
                            />
                            <YAxis
                                domain={[0, 100]}
                                stroke="#666"
                                tick={{ fontSize: 12 }}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#fff',
                                    border: '1px solid #ddd',
                                    borderRadius: '4px'
                                }}
                            />
                            <Line
                                type="monotone"
                                dataKey="score"
                                stroke="#0088ff"
                                strokeWidth={2}
                                dot={{ fill: '#0088ff', r: 4 }}
                                activeDot={{ r: 6 }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Recent Activity */}
            {employee.recent_alerts && employee.recent_alerts.length > 0 && (
                <div className="recent-alerts">
                    <h3>Recent Alerts</h3>
                    <ul className="alert-list">
                        {employee.recent_alerts.map((alert, idx) => (
                            <li key={idx} className={`alert-item alert-${alert.severity}`}>
                                <span className="alert-icon">
                                    {alert.severity === 'high' ? '🔴' : alert.severity === 'medium' ? '🟡' : '🟢'}
                                </span>
                                <div className="alert-content">
                                    <div className="alert-message">{alert.message}</div>
                                    <div className="alert-time">{new Date(alert.timestamp).toLocaleString()}</div>
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
