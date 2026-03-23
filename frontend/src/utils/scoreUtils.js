/**
 * Score Utilities
 * Helper functions for score calculations and formatting
 */

/**
 * Get color based on score
 */
export function getScoreColor(score) {
    if (score < 40) return '#ff4444'; // Red
    if (score < 70) return '#ffaa00'; // Yellow
    return '#44aa44'; // Green
}

/**
 * Get status label based on score
 */
export function getScoreStatus(score) {
    if (score < 60) return 'at-risk';
    if (score < 75) return 'good';
    return 'excellent';
}

/**
 * Calculate statistics from employee array
 */
export function calculateStats(employees) {
    if (employees.length === 0) {
        return {
            avgScore: '0.0',
            atRisk: 0,
            goodStanding: 0,
            total: 0,
            avgTrend: 0
        };
    }

    const totalScore = employees.reduce((sum, emp) => sum + emp.trust_score, 0);
    const avgScore = (totalScore / employees.length).toFixed(1);
    const atRisk = employees.filter(emp => emp.trust_score < 60).length;
    const goodStanding = employees.filter(emp => emp.trust_score > 75).length;

    // Calculate average trend (if available)
    let avgTrend = 0;
    const employeesWithTrend = employees.filter(emp =>
        emp.trend_7day && emp.trend_7day.length >= 2
    );

    if (employeesWithTrend.length > 0) {
        const trends = employeesWithTrend.map(emp => {
            const first = emp.trend_7day[0].score;
            const last = emp.trend_7day[emp.trend_7day.length - 1].score;
            return ((last - first) / first) * 100;
        });
        avgTrend = trends.reduce((sum, t) => sum + t, 0) / trends.length;
    }

    return {
        avgScore,
        atRisk,
        goodStanding,
        total: employees.length,
        avgTrend
    };
}

/**
 * Format score for display
 */
export function formatScore(score) {
    return score.toFixed(1);
}

/**
 * Get score category
 */
export function getScoreCategory(score) {
    if (score < 40) return 'Critical';
    if (score < 60) return 'At Risk';
    if (score < 75) return 'Good';
    if (score < 90) return 'Very Good';
    return 'Excellent';
}
