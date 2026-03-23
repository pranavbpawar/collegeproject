/**
 * EmployeeList Component
 * Sortable and filterable employee table
 */

import React from 'react';
import TrendChart from './TrendChart';
import ScoreBar from './ScoreBar';
import { getScoreStatus } from '../utils/scoreUtils';
import './EmployeeList.css';

export default function EmployeeList({
    employees,
    onSelectEmployee,
    selectedEmployee,
    sortConfig,
    onSort
}) {
    const getSortIcon = (key) => {
        if (sortConfig.key !== key) return '⇅';
        return sortConfig.direction === 'asc' ? '↑' : '↓';
    };

    if (employees.length === 0) {
        return (
            <div className="employee-list empty">
                <p>No employees match the current filters</p>
            </div>
        );
    }

    return (
        <div className="employee-list">
            <div className="list-header">
                <h2>Employee Trust Scores</h2>
                <span className="employee-count">{employees.length} employees</span>
            </div>

            <div className="table-container">
                <table className="employee-table">
                    <thead>
                        <tr>
                            <th onClick={() => onSort('name')} className="sortable">
                                Name {getSortIcon('name')}
                            </th>
                            <th onClick={() => onSort('department')} className="sortable">
                                Department {getSortIcon('department')}
                            </th>
                            <th onClick={() => onSort('trust_score')} className="sortable">
                                Trust Score {getSortIcon('trust_score')}
                            </th>
                            <th>7-Day Trend</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {employees.map(emp => (
                            <tr
                                key={emp.id}
                                className={selectedEmployee?.id === emp.id ? 'selected' : ''}
                                onClick={() => onSelectEmployee(emp)}
                            >
                                <td className="employee-name">
                                    <div className="name-cell">
                                        <span className="name">{emp.name}</span>
                                        <span className="email">{emp.email}</span>
                                    </div>
                                </td>
                                <td>{emp.department || 'N/A'}</td>
                                <td>
                                    <ScoreBar score={emp.trust_score} />
                                </td>
                                <td className="trend-cell">
                                    {emp.trend_7day && emp.trend_7day.length > 0 ? (
                                        <TrendChart data={emp.trend_7day} />
                                    ) : (
                                        <span className="no-data">No data</span>
                                    )}
                                </td>
                                <td>
                                    <span className={`status-badge status-${getScoreStatus(emp.trust_score)}`}>
                                        {getScoreStatus(emp.trust_score)}
                                    </span>
                                </td>
                                <td>
                                    <button
                                        className="btn-view-details"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onSelectEmployee(emp);
                                        }}
                                    >
                                        View Details
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
