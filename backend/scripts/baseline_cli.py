#!/usr/bin/env python3
"""
TBAPS Baseline CLI
Command-line interface for baseline establishment operations
"""

import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.baseline_engine import BaselineEngine


async def establish_all(args):
    """Establish baselines for all employees"""
    engine = BaselineEngine(min_days=args.min_days, target_days=args.target_days)
    summary = await engine.establish_all_baselines(days_lookback=args.days)
    
    print("\n" + "="*60)
    print("BASELINE ESTABLISHMENT SUMMARY")
    print("="*60)
    print(f"Total employees:     {summary['total_employees']}")
    print(f"Successful:          {summary['successful']}")
    print(f"Insufficient data:   {summary['insufficient_data']}")
    print(f"Failed:              {summary['failed']}")
    print(f"Duration:            {summary['duration_seconds']:.2f}s")
    print("="*60)
    
    if summary['errors']:
        print(f"\nErrors ({len(summary['errors'])}):")
        for error in summary['errors'][:10]:
            print(f"  - {error}")
    
    return 0 if summary['failed'] == 0 else 1


async def establish_employee(args):
    """Establish baseline for a single employee"""
    engine = BaselineEngine(min_days=args.min_days, target_days=args.target_days)
    
    print(f"Establishing baseline for employee {args.employee_id}...")
    success = await engine.establish_employee_baseline(
        args.employee_id,
        days_lookback=args.days
    )
    
    if success:
        print("✓ Baseline established successfully")
        return 0
    else:
        print("✗ Failed to establish baseline (insufficient data)")
        return 1


async def get_baseline(args):
    """Get baseline for an employee"""
    engine = BaselineEngine()
    baselines = await engine.get_employee_baseline(
        args.employee_id,
        metric=args.metric
    )
    
    if not baselines:
        print(f"No baselines found for employee {args.employee_id}")
        return 1
    
    print(f"\nBaselines for employee {args.employee_id}:")
    print("="*80)
    
    for baseline in baselines:
        print(f"\nMetric: {baseline['metric']}")
        print(f"  Baseline (mean):  {baseline['baseline_value']:.2f}")
        print(f"  Std Dev:          {baseline['std_dev']:.2f}")
        print(f"  Median (p50):     {baseline['p50']:.2f}")
        print(f"  95th percentile:  {baseline['p95']:.2f}")
        print(f"  Range:            [{baseline['min_value']:.2f}, {baseline['max_value']:.2f}]")
        print(f"  Confidence:       {baseline['confidence']:.1%}")
        print(f"  Sample size:      {baseline['sample_size']}")
        print(f"  Updated:          {baseline['updated_at']}")
    
    print("="*80)
    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='TBAPS Baseline Establishment CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Establish baselines for all employees
  %(prog)s establish-all

  # Establish baseline for specific employee
  %(prog)s establish-employee --employee-id abc123

  # Get baseline for employee
  %(prog)s get-baseline --employee-id abc123

  # Get specific metric baseline
  %(prog)s get-baseline --employee-id abc123 --metric meetings_per_day
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # establish-all command
    establish_all_parser = subparsers.add_parser(
        'establish-all',
        help='Establish baselines for all employees'
    )
    establish_all_parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to look back (default: 30)'
    )
    establish_all_parser.add_argument(
        '--min-days',
        type=int,
        default=14,
        help='Minimum days required (default: 14)'
    )
    establish_all_parser.add_argument(
        '--target-days',
        type=int,
        default=30,
        help='Target days for full confidence (default: 30)'
    )
    establish_all_parser.set_defaults(func=establish_all)
    
    # establish-employee command
    establish_employee_parser = subparsers.add_parser(
        'establish-employee',
        help='Establish baseline for a single employee'
    )
    establish_employee_parser.add_argument(
        '--employee-id',
        required=True,
        help='Employee UUID'
    )
    establish_employee_parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to look back (default: 30)'
    )
    establish_employee_parser.add_argument(
        '--min-days',
        type=int,
        default=14,
        help='Minimum days required (default: 14)'
    )
    establish_employee_parser.add_argument(
        '--target-days',
        type=int,
        default=30,
        help='Target days for full confidence (default: 30)'
    )
    establish_employee_parser.set_defaults(func=establish_employee)
    
    # get-baseline command
    get_baseline_parser = subparsers.add_parser(
        'get-baseline',
        help='Get baseline for an employee'
    )
    get_baseline_parser.add_argument(
        '--employee-id',
        required=True,
        help='Employee UUID'
    )
    get_baseline_parser.add_argument(
        '--metric',
        help='Specific metric name (optional)'
    )
    get_baseline_parser.set_defaults(func=get_baseline)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Run async function
    return asyncio.run(args.func(args))


if __name__ == '__main__':
    sys.exit(main())
