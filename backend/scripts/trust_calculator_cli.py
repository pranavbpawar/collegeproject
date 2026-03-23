#!/usr/bin/env python3
"""
TBAPS Trust Score Calculator CLI
Command-line interface for calculating trust scores
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.trust_calculator import TrustCalculator
from app.core.database import get_db


async def calculate_all(window_days: int = 30):
    """Calculate trust scores for all active employees"""
    print(f"\n{'='*80}")
    print("TBAPS Trust Score Calculator - Calculate All Employees")
    print(f"{'='*80}\n")
    print(f"Window: {window_days} days")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    calculator = TrustCalculator(window_days=window_days)
    
    try:
        summary = await calculator.calculate_daily_scores()
        
        print(f"\n{'='*80}")
        print("CALCULATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total Employees:     {summary['total_employees']}")
        print(f"Successful:          {summary['successful']}")
        print(f"Failed:              {summary['failed']}")
        print(f"Duration:            {summary['duration_seconds']:.2f}s")
        print(f"Avg per employee:    {summary['duration_seconds']/summary['total_employees']:.2f}s")
        print(f"{'='*80}\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        return 1


async def calculate_employee(employee_id: str, window_days: int = 30):
    """Calculate trust score for a single employee"""
    print(f"\n{'='*80}")
    print("TBAPS Trust Score Calculator - Single Employee")
    print(f"{'='*80}\n")
    print(f"Employee ID: {employee_id}")
    print(f"Window: {window_days} days")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    calculator = TrustCalculator(window_days=window_days)
    
    try:
        async for db in get_db():
            score = await calculator.calculate_trust_score(employee_id, db=db)
            
            if score is None:
                print("❌ Insufficient data to calculate trust score\n")
                return 1
            
            print(f"{'='*80}")
            print("TRUST SCORE BREAKDOWN")
            print(f"{'='*80}")
            print(f"Total Score:         {score['total']:.2f}/100")
            print(f"Time Decay Factor:   {score['time_decay_factor']:.3f}")
            print(f"\nComponent Scores:")
            print(f"  Outcome (35%):     {score['outcome']:.2f}/100")
            print(f"  Behavioral (30%):  {score['behavioral']:.2f}/100")
            print(f"  Security (20%):    {score['security']:.2f}/100")
            print(f"  Wellbeing (15%):   {score['wellbeing']:.2f}/100")
            print(f"\nCalculated: {score['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}\n")
            
            # Store the score
            await calculator._store_score(employee_id, score, db)
            await db.commit()
            print("✅ Score stored successfully\n")
            
            return 0
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


async def get_latest_score(employee_id: str):
    """Get the latest trust score for an employee"""
    print(f"\n{'='*80}")
    print("TBAPS Trust Score - Latest Score")
    print(f"{'='*80}\n")
    print(f"Employee ID: {employee_id}\n")
    
    try:
        from app.models import TrustScore, Employee
        from sqlalchemy import select, desc
        import uuid
        
        async for db in get_db():
            # Get employee info
            result = await db.execute(
                select(Employee).where(Employee.id == uuid.UUID(employee_id))
            )
            employee = result.scalar_one_or_none()
            
            if not employee:
                print("❌ Employee not found\n")
                return 1
            
            print(f"Employee: {employee.name} ({employee.email})")
            print(f"Department: {employee.department}")
            print(f"Role: {employee.role}\n")
            
            # Get latest score
            result = await db.execute(
                select(TrustScore)
                .where(TrustScore.employee_id == uuid.UUID(employee_id))
                .order_by(desc(TrustScore.timestamp))
                .limit(1)
            )
            score = result.scalar_one_or_none()
            
            if not score:
                print("❌ No trust scores found for this employee\n")
                return 1
            
            print(f"{'='*80}")
            print("LATEST TRUST SCORE")
            print(f"{'='*80}")
            print(f"Total Score:         {score.total_score:.2f}/100")
            print(f"\nComponent Scores:")
            print(f"  Outcome (35%):     {score.outcome_score:.2f}/100")
            print(f"  Behavioral (30%):  {score.behavioral_score:.2f}/100")
            print(f"  Security (20%):    {score.security_score:.2f}/100")
            print(f"  Wellbeing (15%):   {score.wellbeing_score:.2f}/100")
            print(f"\nCalculated: {score.calculated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Timestamp:  {score.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Expires:    {score.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}\n")
            
            return 0
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


async def list_scores(limit: int = 10, sort_by: str = 'total'):
    """List trust scores for all employees"""
    print(f"\n{'='*80}")
    print(f"TBAPS Trust Scores - Top {limit} Employees")
    print(f"{'='*80}\n")
    
    try:
        from app.models import TrustScore, Employee
        from sqlalchemy import select, desc, func
        from sqlalchemy.orm import joinedload
        
        async for db in get_db():
            # Get latest scores for each employee
            subquery = (
                select(
                    TrustScore.employee_id,
                    func.max(TrustScore.timestamp).label('max_timestamp')
                )
                .group_by(TrustScore.employee_id)
                .subquery()
            )
            
            # Sort column
            sort_column = {
                'total': TrustScore.total_score,
                'outcome': TrustScore.outcome_score,
                'behavioral': TrustScore.behavioral_score,
                'security': TrustScore.security_score,
                'wellbeing': TrustScore.wellbeing_score
            }.get(sort_by, TrustScore.total_score)
            
            result = await db.execute(
                select(TrustScore, Employee)
                .join(
                    subquery,
                    (TrustScore.employee_id == subquery.c.employee_id) &
                    (TrustScore.timestamp == subquery.c.max_timestamp)
                )
                .join(Employee, TrustScore.employee_id == Employee.id)
                .order_by(desc(sort_column))
                .limit(limit)
            )
            
            scores = result.all()
            
            if not scores:
                print("❌ No trust scores found\n")
                return 1
            
            print(f"{'Rank':<6} {'Name':<25} {'Email':<30} {'Total':<8} {'O':<6} {'B':<6} {'S':<6} {'W':<6}")
            print(f"{'-'*6} {'-'*25} {'-'*30} {'-'*8} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
            
            for idx, (score, employee) in enumerate(scores, 1):
                print(
                    f"{idx:<6} "
                    f"{employee.name[:24]:<25} "
                    f"{employee.email[:29]:<30} "
                    f"{score.total_score:>6.2f}  "
                    f"{score.outcome_score:>5.1f} "
                    f"{score.behavioral_score:>5.1f} "
                    f"{score.security_score:>5.1f} "
                    f"{score.wellbeing_score:>5.1f}"
                )
            
            print(f"\n{'='*80}")
            print("Legend: O=Outcome, B=Behavioral, S=Security, W=Wellbeing")
            print(f"{'='*80}\n")
            
            return 0
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='TBAPS Trust Score Calculator CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate scores for all employees
  %(prog)s calculate-all
  
  # Calculate score for specific employee
  %(prog)s calculate-employee --employee-id abc-123-def
  
  # Get latest score for employee
  %(prog)s get-score --employee-id abc-123-def
  
  # List top 20 employees by total score
  %(prog)s list-scores --limit 20 --sort-by total
  
  # List top employees by security score
  %(prog)s list-scores --sort-by security
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Calculate all command
    calc_all_parser = subparsers.add_parser(
        'calculate-all',
        help='Calculate trust scores for all active employees'
    )
    calc_all_parser.add_argument(
        '--window-days',
        type=int,
        default=30,
        help='Number of days to analyze (default: 30)'
    )
    
    # Calculate employee command
    calc_emp_parser = subparsers.add_parser(
        'calculate-employee',
        help='Calculate trust score for a single employee'
    )
    calc_emp_parser.add_argument(
        '--employee-id',
        required=True,
        help='Employee UUID'
    )
    calc_emp_parser.add_argument(
        '--window-days',
        type=int,
        default=30,
        help='Number of days to analyze (default: 30)'
    )
    
    # Get score command
    get_score_parser = subparsers.add_parser(
        'get-score',
        help='Get latest trust score for an employee'
    )
    get_score_parser.add_argument(
        '--employee-id',
        required=True,
        help='Employee UUID'
    )
    
    # List scores command
    list_parser = subparsers.add_parser(
        'list-scores',
        help='List trust scores for all employees'
    )
    list_parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Number of employees to show (default: 10)'
    )
    list_parser.add_argument(
        '--sort-by',
        choices=['total', 'outcome', 'behavioral', 'security', 'wellbeing'],
        default='total',
        help='Sort by score component (default: total)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    if args.command == 'calculate-all':
        return asyncio.run(calculate_all(args.window_days))
    
    elif args.command == 'calculate-employee':
        return asyncio.run(calculate_employee(args.employee_id, args.window_days))
    
    elif args.command == 'get-score':
        return asyncio.run(get_latest_score(args.employee_id))
    
    elif args.command == 'list-scores':
        return asyncio.run(list_scores(args.limit, args.sort_by))
    
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
