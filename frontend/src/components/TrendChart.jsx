/**
 * TrendChart Component
 * Mini line chart for 7-day trends
 */

import React from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

export default function TrendChart({ data, width = 100, height = 40 }) {
    if (!data || data.length === 0) {
        return <span className="no-trend-data">—</span>;
    }

    // Calculate trend direction
    const firstScore = data[0].score;
    const lastScore = data[data.length - 1].score;
    const trendDirection = lastScore > firstScore ? 'up' : lastScore < firstScore ? 'down' : 'neutral';
    const strokeColor = trendDirection === 'up' ? '#44aa44' : trendDirection === 'down' ? '#ff4444' : '#0088ff';

    return (
        <ResponsiveContainer width={width} height={height}>
            <LineChart data={data}>
                <Line
                    type="monotone"
                    dataKey="score"
                    stroke={strokeColor}
                    strokeWidth={2}
                    dot={false}
                />
            </LineChart>
        </ResponsiveContainer>
    );
}
