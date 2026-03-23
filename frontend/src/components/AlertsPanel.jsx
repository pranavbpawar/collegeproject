/**
 * AlertsPanel Component
 * Displays system alerts and warnings
 */

import React, { useMemo } from 'react';
import './AlertsPanel.css';

export default function AlertsPanel({ employees }) {
    const alerts = useMemo(() => {
        const alertList = [];

        employees.forEach(emp => {
            // Burnout risk (low wellbeing + low score)
            if (emp.wellbeing_score < 50 && emp.trust_score < 60) {
                alertList.push({
                    id: `burnout-${emp.id}`,
                    severity: 'high',
                    type: 'burnout',
                    employee: emp.name,
                    message: `${emp.name} shows signs of burnout risk (Wellbeing: ${emp.wellbeing_score.toFixed(1)})`,
                    timestamp: new Date()
                });
            }

            // Security violations (low security score)
            if (emp.security_score < 40) {
                alertList.push({
                    id: `security-${emp.id}`,
                    severity: 'high',
                    type: 'security',
                    employee: emp.name,
                    message: `${emp.name} has critical security hygiene issues (Score: ${emp.security_score.toFixed(1)})`,
                    timestamp: new Date()
                });
            }

            // Performance drop (low outcome score)
            if (emp.outcome_score < 50) {
                alertList.push({
                    id: `performance-${emp.id}`,
                    severity: 'medium',
                    type: 'performance',
                    employee: emp.name,
                    message: `${emp.name} has declining performance (Outcome: ${emp.outcome_score.toFixed(1)})`,
                    timestamp: new Date()
                });
            }

            // Behavioral anomaly (low behavioral score)
            if (emp.behavioral_score < 50) {
                alertList.push({
                    id: `behavior-${emp.id}`,
                    severity: 'medium',
                    type: 'anomaly',
                    employee: emp.name,
                    message: `${emp.name} shows behavioral inconsistencies (Score: ${emp.behavioral_score.toFixed(1)})`,
                    timestamp: new Date()
                });
            }
        });

        // Sort by severity
        return alertList.sort((a, b) => {
            const severityOrder = { high: 0, medium: 1, low: 2 };
            return severityOrder[a.severity] - severityOrder[b.severity];
        });
    }, [employees]);

    if (alerts.length === 0) {
        return (
            <section className="alerts-panel">
                <div className="alerts-header">
                    <h2>🟢 System Alerts</h2>
                    <span className="alert-count">No active alerts</span>
                </div>
                <div className="no-alerts">
                    <p>✅ All employees are in good standing</p>
                </div>
            </section>
        );
    }

    const highSeverity = alerts.filter(a => a.severity === 'high').length;
    const mediumSeverity = alerts.filter(a => a.severity === 'medium').length;

    return (
        <section className="alerts-panel">
            <div className="alerts-header">
                <h2>
                    {highSeverity > 0 ? '🔴' : mediumSeverity > 0 ? '🟡' : '🟢'} System Alerts
                </h2>
                <span className="alert-count">
                    {alerts.length} active alert{alerts.length !== 1 ? 's' : ''}
                </span>
            </div>

            <div className="alert-summary">
                {highSeverity > 0 && (
                    <div className="alert-summary-item severity-high">
                        <span className="severity-icon">🔴</span>
                        <span className="severity-count">{highSeverity} High Priority</span>
                    </div>
                )}
                {mediumSeverity > 0 && (
                    <div className="alert-summary-item severity-medium">
                        <span className="severity-icon">🟡</span>
                        <span className="severity-count">{mediumSeverity} Medium Priority</span>
                    </div>
                )}
            </div>

            <div className="alerts-list">
                {alerts.slice(0, 5).map(alert => (
                    <div key={alert.id} className={`alert-card alert-${alert.severity}`}>
                        <div className="alert-icon-wrapper">
                            {alert.severity === 'high' ? '🔴' : '🟡'}
                        </div>
                        <div className="alert-content">
                            <div className="alert-type-badge">{alert.type}</div>
                            <div className="alert-message">{alert.message}</div>
                            <div className="alert-meta">
                                <span className="alert-employee">{alert.employee}</span>
                                <span className="alert-time">{alert.timestamp.toLocaleTimeString()}</span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {alerts.length > 5 && (
                <div className="alerts-footer">
                    <button className="btn-view-all">
                        View all {alerts.length} alerts →
                    </button>
                </div>
            )}
        </section>
    );
}
