#!/usr/bin/env python3
"""
TBAPS Bias Audit CLI Tool

Command-line interface for running bias detection and mitigation audits.

Usage:
    python3 bias_audit_cli.py run-audit              # Run full bias audit
    python3 bias_audit_cli.py detect-gender          # Detect gender bias only
    python3 bias_audit_cli.py detect-department      # Detect department bias only
    python3 bias_audit_cli.py mitigate               # Apply bias mitigation
    python3 bias_audit_cli.py report --date 2026-01-28  # View audit report
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

from app.services.bias_detector import BiasDetector
from app.core.database import get_db


class BiasAuditCLI:
    """CLI for bias detection and mitigation"""
    
    def __init__(self):
        self.detector = BiasDetector()
    
    async def run_full_audit(self):
        """Run comprehensive bias audit"""
        print("=" * 80)
        print("TBAPS BIAS AUDIT - FULL ANALYSIS")
        print("=" * 80)
        print(f"Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        try:
            results = await self.detector.run_full_audit()
            
            # Display results
            self._display_audit_summary(results)
            self._display_gender_bias(results.get('gender_bias', {}))
            self._display_department_bias(results.get('department_bias', {}))
            self._display_seniority_bias(results.get('seniority_bias', {}))
            self._display_location_bias(results.get('location_bias', {}))
            self._display_race_bias(results.get('race_bias', {}))
            self._display_recommendations(results.get('recommendations', []))
            
            print("\n" + "=" * 80)
            print(f"Audit completed in {results['audit_duration_seconds']:.2f} seconds")
            print("=" * 80)
            
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    async def detect_gender_bias(self):
        """Detect gender bias only"""
        print("=" * 80)
        print("GENDER BIAS DETECTION")
        print("=" * 80)
        
        try:
            results = await self.detector.detect_gender_bias()
            self._display_gender_bias(results)
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    async def detect_department_bias(self):
        """Detect department bias only"""
        print("=" * 80)
        print("DEPARTMENT BIAS DETECTION")
        print("=" * 80)
        
        try:
            results = await self.detector.detect_department_bias()
            self._display_department_bias(results)
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    async def detect_seniority_bias(self):
        """Detect seniority bias only"""
        print("=" * 80)
        print("SENIORITY BIAS DETECTION")
        print("=" * 80)
        
        try:
            results = await self.detector.detect_seniority_bias()
            self._display_seniority_bias(results)
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    async def detect_location_bias(self):
        """Detect location bias only"""
        print("=" * 80)
        print("LOCATION BIAS DETECTION")
        print("=" * 80)
        
        try:
            results = await self.detector.detect_location_bias()
            self._display_location_bias(results)
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    async def run_mitigation(self):
        """Run bias mitigation"""
        print("=" * 80)
        print("BIAS MITIGATION")
        print("=" * 80)
        
        try:
            # First run audit to detect bias
            print("Running bias detection...")
            audit_results = await self.detector.run_full_audit()
            
            if not audit_results['overall_bias_detected']:
                print("\n✅ No bias detected. Mitigation not required.")
                return 0
            
            print("\n⚠️  Bias detected. Applying mitigation strategies...\n")
            
            # Apply mitigation
            mitigation_results = await self.detector.mitigate_bias(audit_results)
            
            # Display results
            print(f"Status: {mitigation_results['status']}")
            print(f"Employees affected: {mitigation_results['employees_affected']}")
            print(f"Corrections applied: {len(mitigation_results['corrections_applied'])}\n")
            
            for correction in mitigation_results['corrections_applied']:
                print(f"  • {correction['dimension'].upper()}: {correction['corrections'].get('method', 'N/A')}")
            
            print("\n✅ Bias mitigation complete")
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    async def view_report(self, date: Optional[str] = None):
        """View audit report from a specific date"""
        print("=" * 80)
        print("BIAS AUDIT REPORT")
        print("=" * 80)
        
        try:
            # Find audit file
            if date:
                date_str = date.replace('-', '')
                pattern = f"bias_audit_{date_str}_*.json"
            else:
                pattern = "bias_audit_*.json"
            
            audit_dir = Path("/var/log/tbaps")
            audit_files = sorted(audit_dir.glob(pattern), reverse=True)
            
            if not audit_files:
                print(f"\n❌ No audit reports found for date: {date or 'any'}")
                return 1
            
            # Load most recent
            audit_file = audit_files[0]
            print(f"\nLoading: {audit_file.name}\n")
            
            with open(audit_file, 'r') as f:
                results = json.load(f)
            
            # Display
            self._display_audit_summary(results)
            self._display_recommendations(results.get('recommendations', []))
            
            return 0
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1
    
    # ========================================================================
    # DISPLAY METHODS
    # ========================================================================
    
    def _display_audit_summary(self, results: dict):
        """Display audit summary"""
        print("\n📊 AUDIT SUMMARY")
        print("-" * 80)
        
        bias_status = "⚠️  BIAS DETECTED" if results.get('overall_bias_detected') else "✅ NO BIAS DETECTED"
        print(f"Overall Status: {bias_status}\n")
        
        # Summary table
        dimensions = []
        for dim_name, dim_key in [
            ('Gender', 'gender_bias'),
            ('Department', 'department_bias'),
            ('Seniority', 'seniority_bias'),
            ('Location', 'location_bias'),
            ('Race/Ethnicity', 'race_bias'),
        ]:
            dim_data = results.get(dim_key, {})
            has_bias = dim_data.get('has_bias', False)
            severity = dim_data.get('bias_severity', 'none')
            
            status = "⚠️  YES" if has_bias else "✅ NO"
            dimensions.append([dim_name, status, severity.upper()])
        
        print(tabulate(
            dimensions,
            headers=['Dimension', 'Bias Detected', 'Severity'],
            tablefmt='grid'
        ))
    
    def _display_gender_bias(self, results: dict):
        """Display gender bias results"""
        if not results:
            return
        
        print("\n👥 GENDER BIAS ANALYSIS")
        print("-" * 80)
        
        # Statistics table
        gender_stats = []
        for gender in ['male', 'female', 'nonbinary', 'other']:
            stats = results.get(gender, {})
            sample_size = results.get('sample_sizes', {}).get(gender, 0)
            
            if sample_size > 0:
                gender_stats.append([
                    gender.capitalize(),
                    sample_size,
                    f"{stats.get('mean', 0):.2f}",
                    f"{stats.get('median', 0):.2f}",
                    f"{stats.get('std_dev', 0):.2f}",
                ])
        
        if gender_stats:
            print(tabulate(
                gender_stats,
                headers=['Gender', 'Sample Size', 'Mean Score', 'Median', 'Std Dev'],
                tablefmt='grid'
            ))
        
        # Disparity ratios
        if results.get('disparity_ratios'):
            print("\nDisparity Ratios (vs. Male baseline):")
            for comparison, ratio in results['disparity_ratios'].items():
                if ratio > 0:
                    percentage = (ratio - 1.0) * 100
                    direction = "higher" if ratio > 1.0 else "lower"
                    print(f"  • {comparison}: {ratio:.3f} ({abs(percentage):.1f}% {direction})")
        
        # Bias verdict
        has_bias = results.get('has_bias', False)
        severity = results.get('bias_severity', 'none')
        
        if has_bias:
            print(f"\n⚠️  BIAS DETECTED: {severity.upper()} severity")
            print(f"   Max disparity: {results.get('max_disparity', 0):.1%}")
        else:
            print("\n✅ No significant gender bias detected")
    
    def _display_department_bias(self, results: dict):
        """Display department bias results"""
        if not results:
            return
        
        print("\n🏢 DEPARTMENT BIAS ANALYSIS")
        print("-" * 80)
        
        # Department statistics
        dept_stats = []
        for dept, stats in results.get('by_department', {}).items():
            sample_size = results.get('sample_sizes', {}).get(dept, 0)
            
            if sample_size > 0:
                dept_stats.append([
                    dept,
                    sample_size,
                    f"{stats.get('mean', 0):.2f}",
                    f"{stats.get('median', 0):.2f}",
                ])
        
        if dept_stats:
            # Sort by mean score
            dept_stats.sort(key=lambda x: float(x[2]), reverse=True)
            
            print(tabulate(
                dept_stats,
                headers=['Department', 'Sample Size', 'Mean Score', 'Median'],
                tablefmt='grid'
            ))
        
        # Disparity metrics
        print(f"\nDisparity Metrics:")
        print(f"  • Highest scoring: {results.get('highest_scoring', 'N/A')}")
        print(f"  • Lowest scoring: {results.get('lowest_scoring', 'N/A')}")
        print(f"  • Max difference: {results.get('max_diff', 0):.2f} points")
        print(f"  • Relative disparity: {results.get('relative_disparity', 0):.1%}")
        
        # Bias verdict
        has_bias = results.get('has_bias', False)
        severity = results.get('bias_severity', 'none')
        
        if has_bias:
            print(f"\n⚠️  BIAS DETECTED: {severity.upper()} severity")
        else:
            print("\n✅ No significant department bias detected")
    
    def _display_seniority_bias(self, results: dict):
        """Display seniority bias results"""
        if not results:
            return
        
        print("\n📈 SENIORITY BIAS ANALYSIS")
        print("-" * 80)
        
        # Seniority statistics
        seniority_stats = []
        for level in ['junior', 'mid', 'senior', 'executive']:
            stats = results.get('by_seniority', {}).get(level, {})
            sample_size = results.get('sample_sizes', {}).get(level, 0)
            
            if sample_size > 0:
                seniority_stats.append([
                    level.capitalize(),
                    sample_size,
                    f"{stats.get('mean', 0):.2f}",
                    f"{stats.get('median', 0):.2f}",
                ])
        
        if seniority_stats:
            print(tabulate(
                seniority_stats,
                headers=['Seniority Level', 'Sample Size', 'Mean Score', 'Median'],
                tablefmt='grid'
            ))
        
        # Disparity metrics
        print(f"\nDisparity Metrics:")
        print(f"  • Max difference: {results.get('max_diff', 0):.2f} points")
        print(f"  • Relative disparity: {results.get('relative_disparity', 0):.1%}")
        
        # Bias verdict
        has_bias = results.get('has_bias', False)
        severity = results.get('bias_severity', 'none')
        
        if has_bias:
            print(f"\n⚠️  BIAS DETECTED: {severity.upper()} severity")
            print("   Note: Some seniority differences may be legitimate")
        else:
            print("\n✅ No significant seniority bias detected")
    
    def _display_location_bias(self, results: dict):
        """Display location bias results"""
        if not results:
            return
        
        print("\n📍 LOCATION BIAS ANALYSIS")
        print("-" * 80)
        
        # Location statistics
        location_stats = []
        for location in ['office', 'remote', 'hybrid']:
            stats = results.get('by_location', {}).get(location, {})
            sample_size = results.get('sample_sizes', {}).get(location, 0)
            
            if sample_size > 0:
                location_stats.append([
                    location.capitalize(),
                    sample_size,
                    f"{stats.get('mean', 0):.2f}",
                    f"{stats.get('median', 0):.2f}",
                ])
        
        if location_stats:
            print(tabulate(
                location_stats,
                headers=['Location', 'Sample Size', 'Mean Score', 'Median'],
                tablefmt='grid'
            ))
        
        # Disparity metrics
        print(f"\nDisparity Metrics:")
        print(f"  • Max difference: {results.get('max_diff', 0):.2f} points")
        print(f"  • Relative disparity: {results.get('relative_disparity', 0):.1%}")
        
        # Bias verdict
        has_bias = results.get('has_bias', False)
        severity = results.get('bias_severity', 'none')
        
        if has_bias:
            print(f"\n⚠️  BIAS DETECTED: {severity.upper()} severity")
        else:
            print("\n✅ No significant location bias detected")
    
    def _display_race_bias(self, results: dict):
        """Display race/ethnicity bias results"""
        if not results:
            return
        
        print("\n🌍 RACE/ETHNICITY BIAS ANALYSIS")
        print("-" * 80)
        
        if not results.get('available', False):
            print(f"⚠️  {results.get('reason', 'Data not available')}")
            return
        
        # Race statistics
        race_stats = []
        for race, stats in results.get('by_race', {}).items():
            sample_size = results.get('sample_sizes', {}).get(race, 0)
            
            if sample_size > 0:
                race_stats.append([
                    race,
                    sample_size,
                    f"{stats.get('mean', 0):.2f}",
                    f"{stats.get('median', 0):.2f}",
                ])
        
        if race_stats:
            print(tabulate(
                race_stats,
                headers=['Race/Ethnicity', 'Sample Size', 'Mean Score', 'Median'],
                tablefmt='grid'
            ))
        
        # Disparity metrics
        print(f"\nDisparity Metrics:")
        print(f"  • Max difference: {results.get('max_diff', 0):.2f} points")
        print(f"  • Relative disparity: {results.get('relative_disparity', 0):.1%}")
        
        # Bias verdict
        has_bias = results.get('has_bias', False)
        severity = results.get('bias_severity', 'none')
        
        if has_bias:
            print(f"\n⚠️  BIAS DETECTED: {severity.upper()} severity")
            print("   ⚠️  IMMEDIATE REVIEW REQUIRED")
        else:
            print("\n✅ No significant race/ethnicity bias detected")
    
    def _display_recommendations(self, recommendations: list):
        """Display recommendations"""
        if not recommendations:
            return
        
        print("\n💡 RECOMMENDATIONS")
        print("-" * 80)
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}\n")


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='TBAPS Bias Detection and Mitigation CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full bias audit
  python3 bias_audit_cli.py run-audit
  
  # Detect specific bias types
  python3 bias_audit_cli.py detect-gender
  python3 bias_audit_cli.py detect-department
  
  # Apply bias mitigation
  python3 bias_audit_cli.py mitigate
  
  # View audit report
  python3 bias_audit_cli.py report --date 2026-01-28
        """
    )
    
    parser.add_argument(
        'command',
        choices=[
            'run-audit',
            'detect-gender',
            'detect-department',
            'detect-seniority',
            'detect-location',
            'mitigate',
            'report',
        ],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--date',
        type=str,
        help='Date for report viewing (YYYY-MM-DD)'
    )
    
    args = parser.parse_args()
    
    cli = BiasAuditCLI()
    
    # Execute command
    if args.command == 'run-audit':
        exit_code = await cli.run_full_audit()
    elif args.command == 'detect-gender':
        exit_code = await cli.detect_gender_bias()
    elif args.command == 'detect-department':
        exit_code = await cli.detect_department_bias()
    elif args.command == 'detect-seniority':
        exit_code = await cli.detect_seniority_bias()
    elif args.command == 'detect-location':
        exit_code = await cli.detect_location_bias()
    elif args.command == 'mitigate':
        exit_code = await cli.run_mitigation()
    elif args.command == 'report':
        exit_code = await cli.view_report(args.date)
    else:
        parser.print_help()
        exit_code = 1
    
    sys.exit(exit_code)


if __name__ == '__main__':
    asyncio.run(main())
