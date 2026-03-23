/**
 * ScoreBar Component
 * Visual score bar with color coding
 */

import React from 'react';
import { getScoreColor } from '../utils/scoreUtils';
import './ScoreBar.css';

export default function ScoreBar({ score }) {
    const color = getScoreColor(score);

    return (
        <div className="score-bar-container">
            <div className="score-bar">
                <div
                    className="score-fill"
                    style={{
                        width: `${score}%`,
                        backgroundColor: color
                    }}
                />
            </div>
            <span className="score-text" style={{ color }}>
                {score.toFixed(1)}
            </span>
        </div>
    );
}
