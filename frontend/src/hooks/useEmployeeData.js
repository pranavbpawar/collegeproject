/**
 * useEmployeeData Hook
 * Fetches and manages employee data with auto-refresh
 */

import { useState, useEffect, useCallback } from 'react';

export function useEmployeeData(apiBaseUrl, refreshInterval = 60000) {
    const [employees, setEmployees] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchEmployees = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch(`${apiBaseUrl}/trust-scores`, {
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Transform data to match expected format
            const transformedData = data.map(emp => ({
                id: emp.employee_id,
                name: emp.name || 'Unknown',
                email: emp.email || '',
                department: emp.department || 'N/A',
                trust_score: emp.total_score || 0,
                outcome_score: emp.outcome_score || 0,
                behavioral_score: emp.behavioral_score || 0,
                security_score: emp.security_score || 0,
                wellbeing_score: emp.wellbeing_score || 0,
                time_decay_factor: emp.time_decay_factor || 1.0,
                trend_7day: emp.trend_7day || [],
                trend_30day: emp.trend_30day || [],
                recent_alerts: emp.recent_alerts || []
            }));

            setEmployees(transformedData);
        } catch (err) {
            console.error('Failed to fetch employees:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl]);

    useEffect(() => {
        fetchEmployees();

        // Set up auto-refresh
        const interval = setInterval(fetchEmployees, refreshInterval);

        return () => clearInterval(interval);
    }, [fetchEmployees, refreshInterval]);

    return {
        employees,
        loading,
        error,
        refetch: fetchEmployees
    };
}
