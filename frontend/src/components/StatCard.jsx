/**
 * StatCard Component
 * Displays key statistics with optional trends
 */

import React from 'react';
import './StatCard.css';

export default function StatCard({ label, value, type = 'info', icon, subtitle, trend }) {
    const getTrendIcon = () => {
        if (!trend) return null;
        if (trend > 0) return <span className="trend trend-up">↑ {trend.toFixed(1)}%</span>;
        if (trend < 0) return <span className="trend trend-down">↓ {Math.abs(trend).toFixed(1)}%</span>;
        return <span className="trend trend-neutral">→ 0%</span>;
    };

    return (
        <div className={`stat-card stat-${type}`}>
            <div className="stat-header">
                {icon && <span className="stat-icon">{icon}</span>}
                <div className="stat-label">{label}</div>
            </div>
            <div className="stat-value">{value}</div>
            {subtitle && <div className="stat-subtitle">{subtitle}</div>}
            {trend !== undefined && <div className="stat-trend">{getTrendIcon()}</div>}
        </div>
    );
}
