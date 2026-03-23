/**
 * LoadingSpinner Component
 */

import React from 'react';
import './LoadingSpinner.css';

export default function LoadingSpinner({ message = 'Loading...' }) {
    return (
        <div className="loading-spinner-container">
            <div className="loading-spinner"></div>
            <p className="loading-message">{message}</p>
        </div>
    );
}
