/**
 * useFilters Hook
 * Manages filtering state and logic
 */

import { useState, useMemo } from 'react';
import { getScoreStatus } from '../utils/scoreUtils';

export function useFilters(employees) {
    const [filters, setFilters] = useState({
        scoreRange: [0, 100],
        department: null,
        status: 'all'
    });

    const filteredData = useMemo(() => {
        return employees.filter(emp => {
            // Score range filter
            if (emp.trust_score < filters.scoreRange[0] || emp.trust_score > filters.scoreRange[1]) {
                return false;
            }

            // Department filter
            if (filters.department && emp.department !== filters.department) {
                return false;
            }

            // Status filter
            if (filters.status !== 'all') {
                const status = getScoreStatus(emp.trust_score);
                if (filters.status === 'at-risk' && status !== 'at-risk') return false;
                if (filters.status === 'good' && status !== 'good') return false;
                if (filters.status === 'excellent' && status !== 'excellent') return false;
            }

            return true;
        });
    }, [employees, filters]);

    return {
        filters,
        setFilters,
        filteredData
    };
}
