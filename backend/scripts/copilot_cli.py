#!/usr/bin/env python3
"""
TBAPS Employee Copilot CLI

Command-line interface for employee insights and recommendations.

Usage:
    python3 copilot_cli.py insights --employee-id abc-123
    python3 copilot_cli.py recommendations --employee-id abc-123
    python3 copilot_cli.py achievements --employee-id abc-123
    python3 copilot_cli.py wellness --employee-id abc-123
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import argparse
from tabulate import tabulate
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.employee_copilot import EmployeeCopilot
from app.core.database import get_db


class CopilotCLI:
    """CLI for Employee Copilot"""
    
    def __init__(self):
        self.copilot = EmployeeCopilot()
    
    async def show_insights(self, employee_id: str, days: int = 30):
        """Show comprehensive insights for employee"""
        print("=" * 80)
        print(f"EMPLOYEE COPILOT - PERSONALIZED INSIGHTS")
        print("=" * 80)
        print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        try:
            insights = await self.copilot.get_personalized_insights(employee_id, days)
            
            # Header
            print(f"👤 {insights['employee_name']}")
            print(f"📅 Period: {insights['period']}\n")
            
            # Summary
            print("📊 SUMMARY")
            print("-" * 80)
            print(f"{insights['summary']}\n")
            
            # Key Metrics
            print("📈 KEY METRICS")
            print("-" * 80)
            metrics = insights['metrics']
            
            trust_score = metrics.get('trust_score', {})
            print(f"Trust Score: {trust_score.get('current', 0):.1f}/100")
            print(f"  • Outcome: {trust_score.get('outcome', 0):.1f}")
            print(f"  • Behavioral: {trust_score.get('behavioral', 0):.1f}")
            print(f"  • Security: {trust_score.get('security', 0):.1f}")
            print(f"  • Wellbeing: {trust_score.get('wellbeing', 0):.1f}\n")
            
            activity = metrics.get('activity', {})
            print(f"Activity (Last 30 days):")
            print(f"  • Tasks Completed: {activity.get('tasks_30d', 0)}")
            print(f"  • Meetings Attended: {activity.get('meetings_30d', 0)}")
            print(f"  • Active Days: {activity.get('active_days_30d', 0)}/30\n")
            
            # Achievements
            if insights.get('wins'):
                print("🏆 ACHIEVEMENTS & WINS")
                print("-" * 80)
                for win in insights['wins']:
                    print(f"{win['icon']} {win['title']}")
                    print(f"   {win['description']}")
                    print()
            
            # Wellness
            wellness = insights.get('wellness', {})
            if wellness:
                print("💚 WELLNESS INSIGHTS")
                print("-" * 80)
                status_icons = {
                    'excellent': '✅',
                    'good': '👍',
                    'needs_attention': '⚠️',
                    'concerning': '🚨',
                }
                icon = status_icons.get(wellness['status'], '•')
                print(f"{icon} Status: {wellness['status'].replace('_', ' ').title()}")
                print(f"   Score: {wellness['score']}/100")
                print(f"   {wellness['message']}\n")
            
            # Recommendations
            if insights.get('recommendations'):
                print("💡 PERSONALIZED RECOMMENDATIONS")
                print("-" * 80)
                for i, rec in enumerate(insights['recommendations'][:5], 1):
                    priority_icons = {
                        'high': '🔴',
                        'medium': '🟡',
                        'low': '🟢',
                    }
                    icon = priority_icons.get(rec['priority'], '•')
                    
                    print(f"{i}. {icon} {rec['title']}")
                    print(f"   Category: {rec['category'].title()}")
                    print(f"   {rec['description']}")
                    print(f"   ➡️  Action: {rec['action']}")
                    print(f"   Impact: {rec['impact']}")
                    print()
            
            # Productivity Patterns
            patterns = insights.get('patterns', {})
            if patterns:
                print("⏰ PRODUCTIVITY PATTERNS")
                print("-" * 80)
                if 'peak_hours' in patterns:
                    start, end = patterns['peak_hours']
                    print(f"🌟 Peak Hours: {start}:00 - {end}:00")
                    print(f"   You're most productive during this time!")
                if patterns.get('consistent_performance'):
                    print(f"🎯 Consistent Performance: You maintain steady productivity")
                print()
            
            # Focus Areas
            if insights.get('focus_areas'):
                print("🎯 FOCUS AREAS")
                print("-" * 80)
                for area in insights['focus_areas']:
                    print(f"{area['icon']} {area['title']}")
                    print(f"   {area['description']}")
                    print()
            
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    async def show_recommendations(self, employee_id: str):
        """Show recommendations only"""
        print("=" * 80)
        print(f"EMPLOYEE COPILOT - RECOMMENDATIONS")
        print("=" * 80)
        print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        try:
            async for db in get_db():
                trends = await self.copilot.get_trends(employee_id, 30, db)
                challenges = await self.copilot.identify_challenges(employee_id, db)
                recommendations = await self.copilot.generate_recommendations(
                    employee_id, trends, challenges, db
                )
            
            if not recommendations:
                print("✅ No recommendations - you're doing great!")
                return 0
            
            print(f"💡 {len(recommendations)} Personalized Recommendations:\n")
            
            for i, rec in enumerate(recommendations, 1):
                priority_icons = {
                    'high': '🔴',
                    'medium': '🟡',
                    'low': '🟢',
                }
                icon = priority_icons.get(rec['priority'], '•')
                
                print(f"{i}. {icon} {rec['title']}")
                print(f"   Priority: {rec['priority'].upper()}")
                print(f"   Category: {rec['category'].title()}")
                print(f"   {rec['description']}")
                print(f"   ➡️  Action: {rec['action']}")
                print(f"   💫 Impact: {rec['impact']}")
                print()
            
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    async def show_achievements(self, employee_id: str, days: int = 30):
        """Show achievements only"""
        print("=" * 80)
        print(f"EMPLOYEE COPILOT - ACHIEVEMENTS & WINS")
        print("=" * 80)
        print(f"Period: Last {days} days")
        print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        try:
            async for db in get_db():
                achievements = await self.copilot.get_achievements(employee_id, days, db)
            
            if not achievements:
                print("Keep up the good work! Achievements will appear here as you progress.")
                return 0
            
            print(f"🏆 {len(achievements)} Achievements:\n")
            
            for achievement in achievements:
                print(f"{achievement['icon']} {achievement['title']}")
                print(f"   Type: {achievement['type'].title()}")
                print(f"   Impact: {achievement['impact'].title()}")
                print(f"   {achievement['description']}")
                print()
            
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    async def show_wellness(self, employee_id: str):
        """Show wellness insights"""
        print("=" * 80)
        print(f"EMPLOYEE COPILOT - WELLNESS INSIGHTS")
        print("=" * 80)
        print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        try:
            async for db in get_db():
                trends = await self.copilot.get_trends(employee_id, 30, db)
                challenges = await self.copilot.identify_challenges(employee_id, db)
            
            wellness = self.copilot._generate_wellness_insights(trends)
            
            # Wellness Status
            print("💚 WELLNESS STATUS")
            print("-" * 80)
            
            status_icons = {
                'excellent': '✅',
                'good': '👍',
                'needs_attention': '⚠️',
                'concerning': '🚨',
            }
            icon = status_icons.get(wellness['status'], '•')
            
            print(f"{icon} Status: {wellness['status'].replace('_', ' ').title()}")
            print(f"   Score: {wellness['score']}/100")
            print(f"   {wellness['message']}\n")
            
            # Wellness Challenges
            wellness_challenges = [
                c for c in challenges
                if c in ['late_night_work', 'weekend_work', 'long_work_days']
            ]
            
            if wellness_challenges:
                print("⚠️  WELLNESS CONCERNS")
                print("-" * 80)
                
                concern_map = {
                    'late_night_work': 'Working late hours frequently',
                    'weekend_work': 'Working on weekends often',
                    'long_work_days': 'Working very long days',
                }
                
                for challenge in wellness_challenges:
                    print(f"• {concern_map.get(challenge, challenge)}")
                print()
            
            # Wellness Recommendations
            async for db in get_db():
                all_recommendations = await self.copilot.generate_recommendations(
                    employee_id, trends, challenges, db
                )
            
            wellness_recs = [
                r for r in all_recommendations
                if r['category'] == 'wellness'
            ]
            
            if wellness_recs:
                print("💡 WELLNESS RECOMMENDATIONS")
                print("-" * 80)
                for i, rec in enumerate(wellness_recs, 1):
                    print(f"{i}. {rec['title']}")
                    print(f"   {rec['description']}")
                    print(f"   ➡️  Action: {rec['action']}")
                    print(f"   💫 Impact: {rec['impact']}")
                    print()
            
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='TBAPS Employee Copilot CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show comprehensive insights
  python3 copilot_cli.py insights --employee-id abc-123
  
  # Show recommendations only
  python3 copilot_cli.py recommendations --employee-id abc-123
  
  # Show achievements
  python3 copilot_cli.py achievements --employee-id abc-123 --days 30
  
  # Show wellness insights
  python3 copilot_cli.py wellness --employee-id abc-123
        """
    )
    
    parser.add_argument(
        'command',
        choices=['insights', 'recommendations', 'achievements', 'wellness'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--employee-id',
        type=str,
        required=True,
        help='Employee ID'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to analyze (default: 30)'
    )
    
    args = parser.parse_args()
    
    cli = CopilotCLI()
    
    # Execute command
    if args.command == 'insights':
        exit_code = await cli.show_insights(args.employee_id, args.days)
    elif args.command == 'recommendations':
        exit_code = await cli.show_recommendations(args.employee_id)
    elif args.command == 'achievements':
        exit_code = await cli.show_achievements(args.employee_id, args.days)
    elif args.command == 'wellness':
        exit_code = await cli.show_wellness(args.employee_id)
    else:
        parser.print_help()
        exit_code = 1
    
    sys.exit(exit_code)


if __name__ == '__main__':
    asyncio.run(main())
