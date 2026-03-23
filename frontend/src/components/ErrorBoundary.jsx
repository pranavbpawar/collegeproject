/**
 * ErrorBoundary Component
 * Catches and displays React errors gracefully
 */

import React from 'react';
import './ErrorBoundary.css';

export default class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        console.error('Error caught by boundary:', error, errorInfo);
        this.setState({ error, errorInfo });
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="error-boundary">
                    <div className="error-content">
                        <h1>⚠️ Something went wrong</h1>
                        <p>We're sorry, but something unexpected happened.</p>
                        <button
                            className="btn-reload"
                            onClick={() => window.location.reload()}
                        >
                            Reload Page
                        </button>
                        {process.env.NODE_ENV === 'development' && this.state.error && (
                            <details className="error-details">
                                <summary>Error Details</summary>
                                <pre>{this.state.error.toString()}</pre>
                                <pre>{this.state.errorInfo.componentStack}</pre>
                            </details>
                        )}
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
