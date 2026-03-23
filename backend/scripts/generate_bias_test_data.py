#!/usr/bin/env python3
"""
Sample Data Generator for Bias Detection Testing

Generates synthetic employee and trust score data with configurable bias
for testing the bias detection and mitigation system.

Usage:
    python3 generate_bias_test_data.py --scenario no-bias
    python3 generate_bias_test_data.py --scenario gender-bias
    python3 generate_bias_test_data.py --scenario department-bias
    python3 generate_bias_test_data.py --scenario all-bias
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import uuid
import random
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_db
from app.models import Employee, TrustScore
from sqlalchemy import select


class BiasTestDataGenerator:
    """Generate test data with configurable bias scenarios"""
    
    DEPARTMENTS = ['engineering', 'sales', 'marketing', 'operations', 'hr', 'finance']
    GENDERS = ['male', 'female', 'nonbinary', 'other']
    SENIORITIES = ['junior', 'mid', 'senior', 'executive']
    LOCATIONS = ['office', 'remote', 'hybrid']
    
    def __init__(self, scenario: str = 'no-bias'):
        """
        Initialize data generator
        
        Args:
            scenario: Bias scenario to generate
                - 'no-bias': Equal scores across all groups
                - 'gender-bias': Lower scores for female employees
                - 'department-bias': Lower scores for sales department
                - 'seniority-bias': Lower scores for junior employees
                - 'location-bias': Lower scores for remote workers
                - 'all-bias': Bias across all dimensions
        """
        self.scenario = scenario
        print(f"Initializing test data generator with scenario: {scenario}")
    
    async def generate_employees(self, count: int = 200) -> list:
        """
        Generate synthetic employee records
        
        Args:
            count: Number of employees to generate
        
        Returns:
            List of employee dictionaries
        """
        print(f"Generating {count} employee records...")
        
        employees = []
        
        for i in range(count):
            # Distribute evenly across dimensions
            gender = self.GENDERS[i % len(self.GENDERS)]
            department = self.DEPARTMENTS[i % len(self.DEPARTMENTS)]
            seniority = self.SENIORITIES[i % len(self.SENIORITIES)]
            location = self.LOCATIONS[i % len(self.LOCATIONS)]
            
            employee = {
                'id': uuid.uuid4(),
                'email': f'employee{i}@example.com',
                'name': f'Employee {i}',
                'department': department,
                'role': f'{seniority.capitalize()} {department.capitalize()}',
                'status': 'active',
                'metadata': {
                    'gender': gender,
                    'seniority': seniority,
                    'location': location,
                }
            }
            
            employees.append(employee)
        
        print(f"✅ Generated {len(employees)} employees")
        return employees
    
    async def generate_trust_scores(self, employees: list) -> list:
        """
        Generate trust scores with bias based on scenario
        
        Args:
            employees: List of employee dictionaries
        
        Returns:
            List of trust score dictionaries
        """
        print(f"Generating trust scores for scenario: {self.scenario}...")
        
        scores = []
        
        for employee in employees:
            # Base score (normally distributed around 75)
            base_score = random.gauss(75.0, 8.0)
            
            # Apply bias based on scenario
            bias_adjustment = self._calculate_bias_adjustment(employee)
            
            final_score = max(0.0, min(100.0, base_score + bias_adjustment))
            
            score = {
                'id': uuid.uuid4(),
                'employee_id': employee['id'],
                'outcome_score': random.gauss(75.0, 5.0),
                'behavioral_score': random.gauss(75.0, 5.0),
                'security_score': random.gauss(75.0, 5.0),
                'wellbeing_score': random.gauss(75.0, 5.0),
                'total_score': final_score,
                'timestamp': datetime.utcnow(),
                'calculated_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(days=90),
            }
            
            scores.append(score)
        
        print(f"✅ Generated {len(scores)} trust scores")
        return scores
    
    def _calculate_bias_adjustment(self, employee: dict) -> float:
        """
        Calculate bias adjustment based on scenario
        
        Args:
            employee: Employee dictionary
        
        Returns:
            Score adjustment (positive or negative)
        """
        adjustment = 0.0
        
        if self.scenario == 'no-bias':
            # No bias - all groups equal
            return 0.0
        
        elif self.scenario == 'gender-bias':
            # Female employees score 10 points lower
            if employee['metadata']['gender'] == 'female':
                adjustment -= 10.0
            # Nonbinary employees score 5 points lower
            elif employee['metadata']['gender'] == 'nonbinary':
                adjustment -= 5.0
        
        elif self.scenario == 'department-bias':
            # Sales department scores 15 points lower
            if employee['department'] == 'sales':
                adjustment -= 15.0
            # Marketing scores 8 points lower
            elif employee['department'] == 'marketing':
                adjustment -= 8.0
        
        elif self.scenario == 'seniority-bias':
            # Junior employees score 12 points lower
            if employee['metadata']['seniority'] == 'junior':
                adjustment -= 12.0
            # Mid-level scores 6 points lower
            elif employee['metadata']['seniority'] == 'mid':
                adjustment -= 6.0
        
        elif self.scenario == 'location-bias':
            # Remote workers score 10 points lower
            if employee['metadata']['location'] == 'remote':
                adjustment -= 10.0
            # Hybrid workers score 5 points lower
            elif employee['metadata']['location'] == 'hybrid':
                adjustment -= 5.0
        
        elif self.scenario == 'all-bias':
            # Combine all biases
            if employee['metadata']['gender'] == 'female':
                adjustment -= 5.0
            if employee['department'] == 'sales':
                adjustment -= 5.0
            if employee['metadata']['seniority'] == 'junior':
                adjustment -= 5.0
            if employee['metadata']['location'] == 'remote':
                adjustment -= 5.0
        
        return adjustment
    
    async def insert_data(self, employees: list, scores: list):
        """
        Insert generated data into database
        
        Args:
            employees: List of employee dictionaries
            scores: List of trust score dictionaries
        """
        print("Inserting data into database...")
        
        async for db in get_db():
            try:
                # Insert employees
                for emp_data in employees:
                    employee = Employee(**emp_data)
                    db.add(employee)
                
                await db.flush()
                
                # Insert trust scores
                for score_data in scores:
                    score = TrustScore(**score_data)
                    db.add(score)
                
                await db.commit()
                
                print(f"✅ Inserted {len(employees)} employees and {len(scores)} trust scores")
                
            except Exception as e:
                print(f"❌ Error inserting data: {e}")
                await db.rollback()
                raise
    
    async def generate_and_insert(self, count: int = 200):
        """
        Generate and insert test data
        
        Args:
            count: Number of employees to generate
        """
        print("=" * 80)
        print("BIAS TEST DATA GENERATOR")
        print("=" * 80)
        print(f"Scenario: {self.scenario}")
        print(f"Employee Count: {count}\n")
        
        # Generate data
        employees = await self.generate_employees(count)
        scores = await self.generate_trust_scores(employees)
        
        # Insert into database
        await self.insert_data(employees, scores)
        
        # Print summary
        self._print_summary(employees, scores)
        
        print("\n" + "=" * 80)
        print("✅ Test data generation complete!")
        print("=" * 80)
    
    def _print_summary(self, employees: list, scores: list):
        """Print summary statistics"""
        print("\n📊 SUMMARY STATISTICS")
        print("-" * 80)
        
        # Gender distribution
        gender_counts = {}
        gender_scores = {}
        for emp in employees:
            gender = emp['metadata']['gender']
            gender_counts[gender] = gender_counts.get(gender, 0) + 1
            
            # Find corresponding score
            score = next((s for s in scores if s['employee_id'] == emp['id']), None)
            if score:
                if gender not in gender_scores:
                    gender_scores[gender] = []
                gender_scores[gender].append(score['total_score'])
        
        print("\nGender Distribution:")
        for gender, count in sorted(gender_counts.items()):
            avg_score = sum(gender_scores[gender]) / len(gender_scores[gender]) if gender in gender_scores else 0
            print(f"  {gender.capitalize()}: {count} employees, avg score: {avg_score:.2f}")
        
        # Department distribution
        dept_counts = {}
        dept_scores = {}
        for emp in employees:
            dept = emp['department']
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
            
            score = next((s for s in scores if s['employee_id'] == emp['id']), None)
            if score:
                if dept not in dept_scores:
                    dept_scores[dept] = []
                dept_scores[dept].append(score['total_score'])
        
        print("\nDepartment Distribution:")
        for dept, count in sorted(dept_counts.items()):
            avg_score = sum(dept_scores[dept]) / len(dept_scores[dept]) if dept in dept_scores else 0
            print(f"  {dept.capitalize()}: {count} employees, avg score: {avg_score:.2f}")
        
        # Overall statistics
        all_scores = [s['total_score'] for s in scores]
        print(f"\nOverall Statistics:")
        print(f"  Total Employees: {len(employees)}")
        print(f"  Total Scores: {len(scores)}")
        print(f"  Average Score: {sum(all_scores) / len(all_scores):.2f}")
        print(f"  Min Score: {min(all_scores):.2f}")
        print(f"  Max Score: {max(all_scores):.2f}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate test data for bias detection system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios:
  no-bias          - Equal scores across all groups (baseline)
  gender-bias      - Female employees score 10 points lower
  department-bias  - Sales department scores 15 points lower
  seniority-bias   - Junior employees score 12 points lower
  location-bias    - Remote workers score 10 points lower
  all-bias         - Combined bias across all dimensions

Examples:
  # Generate baseline data (no bias)
  python3 generate_bias_test_data.py --scenario no-bias --count 200
  
  # Generate data with gender bias
  python3 generate_bias_test_data.py --scenario gender-bias --count 200
  
  # Generate data with all biases
  python3 generate_bias_test_data.py --scenario all-bias --count 500
        """
    )
    
    parser.add_argument(
        '--scenario',
        choices=['no-bias', 'gender-bias', 'department-bias', 'seniority-bias', 'location-bias', 'all-bias'],
        default='no-bias',
        help='Bias scenario to generate'
    )
    
    parser.add_argument(
        '--count',
        type=int,
        default=200,
        help='Number of employees to generate (default: 200)'
    )
    
    args = parser.parse_args()
    
    # Generate data
    generator = BiasTestDataGenerator(scenario=args.scenario)
    await generator.generate_and_insert(count=args.count)


if __name__ == '__main__':
    asyncio.run(main())
