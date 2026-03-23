/**
 * FilterBar Component
 * Provides filtering controls for employee list
 */

import React from 'react';
import './FilterBar.css';

export default function FilterBar({ filters, setFilters, employees }) {
    // Get unique departments
    const departments = React.useMemo(() => {
        const depts = new Set(employees.map(e => e.department).filter(Boolean));
        return Array.from(depts).sort();
    }, [employees]);

    const handleScoreRangeChange = (type, value) => {
        const newRange = [...filters.scoreRange];
        if (type === 'min') {
            newRange[0] = parseInt(value);
        } else {
            newRange[1] = parseInt(value);
        }
        setFilters({ ...filters, scoreRange: newRange });
    };

    const handleDepartmentChange = (dept) => {
        setFilters({ ...filters, department: dept === 'all' ? null : dept });
    };

    const handleStatusChange = (status) => {
        setFilters({ ...filters, status });
    };

    const clearFilters = () => {
        setFilters({
            scoreRange: [0, 100],
            department: null,
            status: 'all'
        });
    };

    const hasActiveFilters =
        filters.scoreRange[0] !== 0 ||
        filters.scoreRange[1] !== 100 ||
        filters.department !== null ||
        filters.status !== 'all';

    return (
        <section className="filter-bar">
            <div className="filter-header">
                <h3>🔍 Filters</h3>
                {hasActiveFilters && (
                    <button className="btn-clear-filters" onClick={clearFilters}>
                        Clear All
                    </button>
                )}
            </div>

            <div className="filter-controls">
                {/* Score Range Filter */}
                <div className="filter-group">
                    <label className="filter-label">Trust Score Range</label>
                    <div className="range-inputs">
                        <div className="range-input-group">
                            <input
                                type="number"
                                min="0"
                                max="100"
                                value={filters.scoreRange[0]}
                                onChange={(e) => handleScoreRangeChange('min', e.target.value)}
                                className="range-number-input"
                            />
                            <span className="range-label">to</span>
                            <input
                                type="number"
                                min="0"
                                max="100"
                                value={filters.scoreRange[1]}
                                onChange={(e) => handleScoreRangeChange('max', e.target.value)}
                                className="range-number-input"
                            />
                        </div>
                        <div className="range-slider-group">
                            <input
                                type="range"
                                min="0"
                                max="100"
                                value={filters.scoreRange[0]}
                                onChange={(e) => handleScoreRangeChange('min', e.target.value)}
                                className="range-slider"
                            />
                            <input
                                type="range"
                                min="0"
                                max="100"
                                value={filters.scoreRange[1]}
                                onChange={(e) => handleScoreRangeChange('max', e.target.value)}
                                className="range-slider"
                            />
                        </div>
                    </div>
                </div>

                {/* Department Filter */}
                <div className="filter-group">
                    <label className="filter-label">Department</label>
                    <select
                        value={filters.department || 'all'}
                        onChange={(e) => handleDepartmentChange(e.target.value)}
                        className="filter-select"
                    >
                        <option value="all">All Departments</option>
                        {departments.map(dept => (
                            <option key={dept} value={dept}>{dept}</option>
                        ))}
                    </select>
                </div>

                {/* Status Filter */}
                <div className="filter-group">
                    <label className="filter-label">Status</label>
                    <div className="filter-buttons">
                        <button
                            className={`filter-btn ${filters.status === 'all' ? 'active' : ''}`}
                            onClick={() => handleStatusChange('all')}
                        >
                            All
                        </button>
                        <button
                            className={`filter-btn ${filters.status === 'at-risk' ? 'active' : ''}`}
                            onClick={() => handleStatusChange('at-risk')}
                        >
                            At Risk
                        </button>
                        <button
                            className={`filter-btn ${filters.status === 'good' ? 'active' : ''}`}
                            onClick={() => handleStatusChange('good')}
                        >
                            Good
                        </button>
                        <button
                            className={`filter-btn ${filters.status === 'excellent' ? 'active' : ''}`}
                            onClick={() => handleStatusChange('excellent')}
                        >
                            Excellent
                        </button>
                    </div>
                </div>
            </div>
        </section>
    );
}
