#!/usr/bin/env python3
"""
TBAPS Intervention Engine CLI

Command-line interface for generating and managing intervention recommendations.

Usage:
    python3 intervention_cli.py recommend --employee-id abc-123
    python3 intervention_cli.py recommend-team --department engineering
    python3 intervention_cli.py list-critical
    python3 intervention_cli.py report
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json
from typing import Optional
import argparse
from tabulate import tabulate

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.intervention_engine import InterventionEngine
from app.core.database import get_db


class InterventionCLI:
    """CLI for intervention recommendations"""
    
    def __init__(self):
        self.engine = InterventionEngine()
    
    async def recommend_for_employee(self, employee_id: str):
        """Generate recommendations for a single employee"""
        print("=" * 80)
        print(f"INTERVENTION RECOMMENDATIONS - Employee {employee_id}")
        print("=" * 80)
        print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        try:
            interventions = await self.engine.recommend_interventions(employee_id)
            
            if not interventions:
                print("✅ No interventions needed - employee is doing well!")
                return 0
            
            print(f"📋 {len(interventions)} intervention(s) recommended:\n")
            
            for i, intervention in enumerate(interventions, 1):
                self._display_intervention(i, intervention)
            
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    async def recommend_for_team(
        self, 
        team_id: Optional[str] = None,
        department: Optional[str] = None
    ):
        """Generate recommendations for a team"""
        print("=" * 80)
        print(f"TEAM INTERVENTION RECOMMENDATIONS")
        print("=" * 80)
        
        if department:
            print(f"Department: {department}")
        if team_id:
            print(f"Team ID: {team_id}")
        
        print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        try:
            interventions = await self.engine.recommend_team_interventions(
                team_id=team_id,
                department=department
            )
            
            if not interventions:
                print("✅ No team interventions needed - team is healthy!")
                return 0
            
            print(f"📋 {len(interventions)} team intervention(s) recommended:\n")
            
            for i, intervention in enumerate(interventions, 1):
                self._display_intervention(i, intervention)
            
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    async def list_critical_interventions(self):
        """List all critical priority interventions"""
        print("=" * 80)
        print("CRITICAL INTERVENTIONS - IMMEDIATE ACTION REQUIRED")
        print("=" * 80)
        print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        try:
            # Get all active employees
            async for db in get_db():
                from app.models import Employee
                from sqlalchemy import select
                
                result = await db.execute(
                    select(Employee.id).where(Employee.status == 'active')
                )
                employee_ids = [str(row[0]) for row in result.fetchall()]
            
            critical_interventions = []
            
            for emp_id in employee_ids:
                interventions = await self.engine.recommend_interventions(
                    emp_id, 
                    include_low_priority=False
                )
                
                critical = [
                    i for i in interventions 
                    if i['priority'] == 'critical'
                ]
                
                critical_interventions.extend(critical)
            
            if not critical_interventions:
                print("✅ No critical interventions - all employees are doing well!")
                return 0
            
            print(f"🚨 {len(critical_interventions)} CRITICAL intervention(s) found:\n")
            
            for i, intervention in enumerate(critical_interventions, 1):
                self._display_intervention(i, intervention)
            
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    async def generate_report(self):
        """Generate comprehensive intervention report"""
        print("=" * 80)
        print("INTERVENTION SUMMARY REPORT")
        print("=" * 80)
        print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        try:
            # Get all active employees
            async for db in get_db():
                from app.models import Employee
                from sqlalchemy import select
                
                result = await db.execute(
                    select(Employee.id, Employee.name, Employee.department)
                    .where(Employee.status == 'active')
                )
                employees = result.fetchall()
            
            # Collect statistics
            stats = {
                'total_employees': len(employees),
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'no_intervention': 0,
                'by_category': {
                    'wellness': 0,
                    'performance': 0,
                    'engagement': 0,
                    'development': 0,
                    'team': 0,
                },
            }
            
            all_interventions = []
            
            for emp_id, emp_name, emp_dept in employees:
                interventions = await self.engine.recommend_interventions(str(emp_id))
                
                if not interventions:
                    stats['no_intervention'] += 1
                    continue
                
                for intervention in interventions:
                    priority = intervention['priority']
                    category = intervention['category']
                    
                    stats[priority] = stats.get(priority, 0) + 1
                    stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
                    
                    all_interventions.append({
                        'employee': emp_name,
                        'department': emp_dept,
                        **intervention
                    })
            
            # Display summary
            print("📊 SUMMARY STATISTICS")
            print("-" * 80)
            print(f"Total Employees: {stats['total_employees']}")
            print(f"Employees Needing Intervention: {stats['total_employees'] - stats['no_intervention']}")
            print(f"Employees Doing Well: {stats['no_intervention']}\n")
            
            # Priority breakdown
            priority_table = [
                ['🚨 Critical', stats['critical']],
                ['⚠️  High', stats['high']],
                ['⚡ Medium', stats['medium']],
                ['📌 Low', stats['low']],
            ]
            
            print("Priority Breakdown:")
            print(tabulate(priority_table, headers=['Priority', 'Count'], tablefmt='grid'))
            print()
            
            # Category breakdown
            category_table = [
                [cat.capitalize(), count]
                for cat, count in stats['by_category'].items()
                if count > 0
            ]
            
            print("Category Breakdown:")
            print(tabulate(category_table, headers=['Category', 'Count'], tablefmt='grid'))
            print()
            
            # Critical interventions
            critical = [i for i in all_interventions if i['priority'] == 'critical']
            if critical:
                print("\n🚨 CRITICAL INTERVENTIONS (Immediate Action Required)")
                print("-" * 80)
                for intervention in critical:
                    print(f"\n• {intervention['employee']} ({intervention['department']})")
                    print(f"  {intervention['title']}")
                    print(f"  Urgency: {intervention['urgency_days']} days")
            
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    def _display_intervention(self, index: int, intervention: Dict[str, Any]):
        """Display a single intervention"""
        priority_icons = {
            'critical': '🚨',
            'high': '⚠️ ',
            'medium': '⚡',
            'low': '📌',
        }
        
        icon = priority_icons.get(intervention['priority'], '•')
        
        print(f"{index}. {icon} {intervention['title']}")
        print(f"   Priority: {intervention['priority'].upper()}")
        print(f"   Category: {intervention['category'].capitalize()}")
        print(f"   Urgency: {intervention['urgency_days']} days")
        
        if 'employee_name' in intervention:
            print(f"   Employee: {intervention['employee_name']}")
        
        if 'department' in intervention:
            print(f"   Department: {intervention['department']}")
        
        print(f"\n   Description:")
        print(f"   {intervention['description']}")
        
        print(f"\n   Recommended Actions:")
        for action in intervention['actions']:
            print(f"   • {action}")
        
        # Additional metrics
        if 'risk_level' in intervention:
            print(f"\n   Burnout Risk: {intervention['risk_level']:.1%}")
        
        if 'trust_score' in intervention:
            print(f"   Trust Score: {intervention['trust_score']:.1f}")
        
        if 'performance_trend' in intervention:
            trend = intervention['performance_trend']
            trend_str = f"+{trend:.1%}" if trend > 0 else f"{trend:.1%}"
            print(f"   Performance Trend: {trend_str}")
        
        print()


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='TBAPS Intervention Engine CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate recommendations for specific employee
  python3 intervention_cli.py recommend --employee-id abc-123
  
  # Generate team recommendations
  python3 intervention_cli.py recommend-team --department engineering
  
  # List all critical interventions
  python3 intervention_cli.py list-critical
  
  # Generate comprehensive report
  python3 intervention_cli.py report
        """
    )
    
    parser.add_argument(
        'command',
        choices=[
            'recommend',
            'recommend-team',
            'list-critical',
            'report',
        ],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--employee-id',
        type=str,
        help='Employee ID for individual recommendations'
    )
    
    parser.add_argument(
        '--team-id',
        type=str,
        help='Team ID for team recommendations'
    )
    
    parser.add_argument(
        '--department',
        type=str,
        help='Department name for team recommendations'
    )
    
    args = parser.parse_args()
    
    cli = InterventionCLI()
    
    # Execute command
    if args.command == 'recommend':
        if not args.employee_id:
            print("❌ ERROR: --employee-id required for recommend command")
            sys.exit(1)
        exit_code = await cli.recommend_for_employee(args.employee_id)
    
    elif args.command == 'recommend-team':
        if not args.team_id and not args.department:
            print("❌ ERROR: --team-id or --department required for recommend-team command")
            sys.exit(1)
        exit_code = await cli.recommend_for_team(
            team_id=args.team_id,
            department=args.department
        )
    
    elif args.command == 'list-critical':
        exit_code = await cli.list_critical_interventions()
    
    elif args.command == 'report':
        exit_code = await cli.generate_report()
    
    else:
        parser.print_help()
        exit_code = 1
    
    sys.exit(exit_code)


if __name__ == '__main__':
    asyncio.run(main())
