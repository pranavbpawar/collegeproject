/**
 * CircleChart Component
 * Circular progress chart for component scores
 */

import React from 'react';
import { getScoreColor } from '../utils/scoreUtils';
import './CircleChart.css';

export default function CircleChart({ value, size = 100 }) {
    const color = getScoreColor(value);
    const percentage = (value / 100) * 360;

    return (
        <div className="circle-chart-container" style={{ width: size, height: size }}>
            <div
                className="circle-chart"
                style={{
                    background: `conic-gradient(
            ${color} 0deg ${percentage}deg,
            #e0e0e0 ${percentage}deg 360deg
          )`
                }}
            >
                <div className="circle-inner">
                    <div className="circle-value">{value.toFixed(1)}</div>
                </div>
            </div>
        </div>
    );
}
