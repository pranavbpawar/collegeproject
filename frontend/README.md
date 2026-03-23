# TBAPS Manager Dashboard

## Overview

React-based dashboard for TBAPS managers to monitor employee trust scores, view trends, and identify risks in real-time.

## Features

✅ **Real-time Data Updates** - Auto-refresh every 60 seconds  
✅ **Interactive Charts** - Line charts, bar charts, and circular progress indicators  
✅ **Employee List** - Sortable and filterable with 7-day trends  
✅ **Trust Score Visualization** - Color-coded scores with component breakdown  
✅ **Alert System** - Burnout risks, security violations, performance drops  
✅ **Responsive Design** - Mobile, tablet, and desktop support  
✅ **Accessibility** - WCAG 2.1 AA compliant  

## Quick Start

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Dashboard will be available at `http://localhost:3000`

### Production Build

```bash
npm run build
npm run preview
```

## Configuration

### Environment Variables

Create `.env` file in `frontend/` directory:

```env
REACT_APP_API_URL=http://localhost:8000/api/v1
```

### API Endpoints

The dashboard expects the following API endpoints:

- `GET /api/v1/trust-scores` - List all employee trust scores
- `GET /api/v1/trust-scores/{employee_id}` - Get specific employee score
- `GET /api/v1/trust-scores/{employee_id}/history` - Get score history

## Component Structure

```
src/
├── App.jsx                    # Main dashboard component
├── components/
│   ├── StatCard.jsx          # Statistics cards
│   ├── EmployeeList.jsx      # Employee table
│   ├── DetailPanel.jsx       # Employee detail view
│   ├── AlertsPanel.jsx       # System alerts
│   ├── FilterBar.jsx         # Filtering controls
│   ├── TrendChart.jsx        # Mini trend charts
│   ├── ScoreBar.jsx          # Score visualization bar
│   ├── CircleChart.jsx       # Circular progress chart
│   ├── LoadingSpinner.jsx    # Loading state
│   └── ErrorBoundary.jsx     # Error handling
├── hooks/
│   ├── useEmployeeData.js    # Data fetching hook
│   └── useFilters.js         # Filtering logic hook
└── utils/
    └── scoreUtils.js         # Score calculation utilities
```

## Score Color Coding

| Score Range | Color | Status |
|-------------|-------|--------|
| 0-39 | 🔴 Red | Critical |
| 40-69 | 🟡 Yellow | At Risk |
| 70-100 | 🟢 Green | Good/Excellent |

## Features

### Stats Overview

- **Average Trust Score** - Team average with trend
- **At Risk** - Employees with score < 60
- **Good Standing** - Employees with score > 75
- **Total Monitored** - Total employee count

### Employee List

- Sortable by name, department, trust score
- Filterable by score range, department, status
- 7-day trend visualization
- Click to view details

### Detail Panel

- Overall trust score with circular gauge
- Component breakdown (Outcome, Behavioral, Security, Wellbeing)
- 30-day trend chart
- Recent alerts and warnings

### Alerts System

Automatically detects:
- **Burnout Risk** - Low wellbeing + low trust score
- **Security Violations** - Critical security hygiene issues
- **Performance Drops** - Declining outcome scores
- **Behavioral Anomalies** - Inconsistent patterns

### Filtering

- **Score Range** - Slider to filter by trust score
- **Department** - Dropdown to filter by department
- **Status** - Quick filters (All, At Risk, Good, Excellent)

## Performance

- Initial load: < 2 seconds
- Auto-refresh: Every 60 seconds
- Optimized rendering with React.memo
- Lazy loading for charts

## Accessibility

- WCAG 2.1 AA compliant
- Keyboard navigation support
- Screen reader friendly
- High contrast mode support
- Focus indicators
- Reduced motion support

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Responsive Breakpoints

- **Desktop**: > 1024px
- **Tablet**: 768px - 1024px
- **Mobile**: < 768px

## Troubleshooting

### Dashboard not loading

1. Check API is running: `curl http://localhost:8000/api/v1/trust-scores`
2. Verify CORS settings in backend
3. Check browser console for errors

### No data displaying

1. Ensure trust scores are calculated: `python3 scripts/trust_calculator_cli.py calculate-all`
2. Verify API endpoint returns data
3. Check network tab in browser dev tools

### Charts not rendering

1. Ensure Recharts is installed: `npm install recharts`
2. Check browser console for errors
3. Verify data format matches expected structure

## Development

### Adding New Components

1. Create component file in `src/components/`
2. Create corresponding CSS file
3. Import and use in `App.jsx`

### Modifying Styles

- Global styles: `src/App.css`
- Component styles: `src/components/[Component].css`
- CSS variables defined in `App.css` `:root`

### Testing

```bash
# Run linter
npm run lint

# Format code
npm run format
```

## Deployment

### Build for Production

```bash
npm run build
```

Output will be in `dist/` directory.

### Deploy to Web Server

```bash
# Copy dist folder to web server
scp -r dist/* user@server:/var/www/tbaps-dashboard/

# Or use Docker
docker build -t tbaps-dashboard .
docker run -p 3000:3000 tbaps-dashboard
```

## Security

- No sensitive data in logs
- Secure API calls only (HTTPS in production)
- CORS configured properly
- Input validation on filters
- XSS protection via React

## License

Proprietary - TBAPS Internal Use Only

## Support

For issues or questions:
1. Check documentation
2. Review browser console
3. Check API logs
4. Contact development team

---

**Version:** 1.0.0  
**Last Updated:** 2026-01-25  
**Maintainer:** TBAPS Development Team
