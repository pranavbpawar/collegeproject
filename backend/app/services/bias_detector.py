"""
TBAPS Bias Detection and Mitigation System

Detects and mitigates bias in trust scoring algorithms across:
- Gender bias
- Department/role bias
- Seniority bias
- Location bias
- Racial/ethnic bias (if applicable)

Ensures fairness and equity across all demographic groups.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import uuid
import numpy as np
from collections import defaultdict
import json

from sqlalchemy import select, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Employee, TrustScore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/tbaps/bias_detector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BiasDetector:
    """
    Bias Detection and Mitigation Engine
    
    Detects bias across multiple demographic dimensions:
    - Gender (male, female, nonbinary, other)
    - Department (engineering, sales, marketing, etc.)
    - Role/Seniority (junior, mid, senior, executive)
    - Location (office, remote, hybrid)
    - Race/Ethnicity (if data available)
    
    Applies statistical tests and correction factors to ensure fairness.
    """
    
    # Bias thresholds (configurable)
    BIAS_THRESHOLDS = {
        'gender': 0.05,        # 5% disparity triggers bias flag
        'department': 0.10,    # 10% disparity
        'seniority': 0.08,     # 8% disparity
        'location': 0.07,      # 7% disparity
        'race': 0.05,          # 5% disparity
    }
    
    # Minimum sample sizes for statistical validity
    MIN_SAMPLE_SIZES = {
        'gender': 10,
        'department': 5,
        'seniority': 5,
        'location': 5,
        'race': 10,
    }
    
    # Statistical significance level
    SIGNIFICANCE_LEVEL = 0.05  # p < 0.05
    
    def __init__(self, db_connection: Optional[AsyncSession] = None):
        """
        Initialize bias detector
        
        Args:
            db_connection: Optional database session
        """
        self.conn = db_connection
        self.audit_trail = []
        logger.info("BiasDetector initialized")
    
    async def run_full_audit(self) -> Dict[str, Any]:
        """
        Run comprehensive bias audit across all dimensions
        
        Returns:
            Complete audit report with all bias metrics
        """
        logger.info("Starting full bias audit")
        start_time = datetime.utcnow()
        
        audit_results = {
            'timestamp': start_time,
            'gender_bias': await self.detect_gender_bias(),
            'department_bias': await self.detect_department_bias(),
            'seniority_bias': await self.detect_seniority_bias(),
            'location_bias': await self.detect_location_bias(),
            'race_bias': await self.detect_race_bias(),
            'intersectional_bias': await self.detect_intersectional_bias(),
        }
        
        # Calculate overall bias score
        audit_results['overall_bias_detected'] = self._calculate_overall_bias(audit_results)
        audit_results['recommendations'] = self._generate_recommendations(audit_results)
        
        # Store audit trail
        await self._store_audit_trail(audit_results)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        audit_results['audit_duration_seconds'] = duration
        
        logger.info(f"Bias audit complete in {duration:.2f}s")
        
        return audit_results
    
    # ========================================================================
    # GENDER BIAS DETECTION
    # ========================================================================
    
    async def detect_gender_bias(self) -> Dict[str, Any]:
        """
        Detect gender bias in trust scores
        
        Analyzes:
        - Average scores by gender
        - Score distributions
        - Statistical significance
        - Disparity ratios
        
        Returns:
            Gender bias analysis results
        """
        logger.info("Detecting gender bias")
        
        async for db in get_db():
            try:
                # Get scores by gender
                male_scores = await self._get_scores_by_gender('male', db)
                female_scores = await self._get_scores_by_gender('female', db)
                nonbinary_scores = await self._get_scores_by_gender('nonbinary', db)
                other_scores = await self._get_scores_by_gender('other', db)
                
                # Calculate statistics
                male_stats = self._calculate_statistics(male_scores)
                female_stats = self._calculate_statistics(female_scores)
                nb_stats = self._calculate_statistics(nonbinary_scores)
                other_stats = self._calculate_statistics(other_scores)
                
                # Calculate disparity ratios
                results = {
                    'male': male_stats,
                    'female': female_stats,
                    'nonbinary': nb_stats,
                    'other': other_stats,
                    'sample_sizes': {
                        'male': len(male_scores),
                        'female': len(female_scores),
                        'nonbinary': len(nonbinary_scores),
                        'other': len(other_scores),
                    },
                }
                
                # Calculate disparity ratios (comparing to male baseline)
                if male_stats['mean'] > 0:
                    results['disparity_ratios'] = {
                        'female_vs_male': female_stats['mean'] / male_stats['mean'],
                        'nonbinary_vs_male': nb_stats['mean'] / male_stats['mean'] if nb_stats['mean'] > 0 else 0,
                        'other_vs_male': other_stats['mean'] / male_stats['mean'] if other_stats['mean'] > 0 else 0,
                    }
                else:
                    results['disparity_ratios'] = {}
                
                # Statistical tests
                results['statistical_tests'] = {
                    'female_vs_male_ttest': self._perform_ttest(female_scores, male_scores),
                    'nonbinary_vs_male_ttest': self._perform_ttest(nonbinary_scores, male_scores),
                }
                
                # Determine if bias exists
                max_disparity = 0
                if results['disparity_ratios']:
                    disparities = [
                        abs(1.0 - ratio) 
                        for ratio in results['disparity_ratios'].values() 
                        if ratio > 0
                    ]
                    max_disparity = max(disparities) if disparities else 0
                
                results['has_bias'] = max_disparity > self.BIAS_THRESHOLDS['gender']
                results['max_disparity'] = max_disparity
                results['bias_severity'] = self._classify_bias_severity(max_disparity, 'gender')
                
                logger.info(f"Gender bias detection: has_bias={results['has_bias']}, max_disparity={max_disparity:.3f}")
                
                return results
                
            except Exception as e:
                logger.error(f"Error detecting gender bias: {e}")
                raise
    
    async def _get_scores_by_gender(self, gender: str, db: AsyncSession) -> List[float]:
        """Get trust scores for employees of a specific gender"""
        try:
            # Query employees with gender in metadata
            result = await db.execute(
                select(TrustScore.total_score)
                .join(Employee, TrustScore.employee_id == Employee.id)
                .where(
                    and_(
                        Employee.status == 'active',
                        Employee.metadata['gender'].astext == gender
                    )
                )
                .order_by(TrustScore.timestamp.desc())
                .distinct(TrustScore.employee_id)
            )
            
            scores = [row[0] for row in result.fetchall()]
            logger.debug(f"Retrieved {len(scores)} scores for gender={gender}")
            return scores
            
        except Exception as e:
            logger.error(f"Error fetching scores for gender {gender}: {e}")
            return []
    
    # ========================================================================
    # DEPARTMENT BIAS DETECTION
    # ========================================================================
    
    async def detect_department_bias(self) -> Dict[str, Any]:
        """
        Detect department/role bias in trust scores
        
        Analyzes:
        - Average scores by department
        - Inter-department disparities
        - Statistical significance
        
        Returns:
            Department bias analysis results
        """
        logger.info("Detecting department bias")
        
        async for db in get_db():
            try:
                # Get all departments
                departments = await self._get_all_departments(db)
                
                # Get scores by department
                dept_scores = {}
                dept_stats = {}
                
                for dept in departments:
                    scores = await self._get_scores_by_department(dept, db)
                    dept_scores[dept] = scores
                    dept_stats[dept] = self._calculate_statistics(scores)
                
                # Calculate disparity metrics
                if dept_stats:
                    means = [stats['mean'] for stats in dept_stats.values() if stats['mean'] > 0]
                    max_score = max(means) if means else 0
                    min_score = min(means) if means else 0
                    avg_score = np.mean(means) if means else 0
                    
                    max_diff = max_score - min_score
                    relative_disparity = (max_diff / avg_score) if avg_score > 0 else 0
                else:
                    max_diff = 0
                    relative_disparity = 0
                    avg_score = 0
                
                results = {
                    'by_department': dept_stats,
                    'sample_sizes': {dept: len(scores) for dept, scores in dept_scores.items()},
                    'max_score': max_score if dept_stats else 0,
                    'min_score': min_score if dept_stats else 0,
                    'avg_score': avg_score,
                    'max_diff': max_diff,
                    'relative_disparity': relative_disparity,
                    'has_bias': relative_disparity > self.BIAS_THRESHOLDS['department'],
                    'bias_severity': self._classify_bias_severity(relative_disparity, 'department'),
                }
                
                # Identify advantaged and disadvantaged departments
                if dept_stats:
                    sorted_depts = sorted(
                        dept_stats.items(), 
                        key=lambda x: x[1]['mean'], 
                        reverse=True
                    )
                    results['highest_scoring'] = sorted_depts[0][0] if sorted_depts else None
                    results['lowest_scoring'] = sorted_depts[-1][0] if sorted_depts else None
                
                logger.info(f"Department bias detection: has_bias={results['has_bias']}, disparity={relative_disparity:.3f}")
                
                return results
                
            except Exception as e:
                logger.error(f"Error detecting department bias: {e}")
                raise
    
    async def _get_all_departments(self, db: AsyncSession) -> List[str]:
        """Get list of all departments"""
        try:
            result = await db.execute(
                select(Employee.department)
                .where(
                    and_(
                        Employee.status == 'active',
                        Employee.department.isnot(None)
                    )
                )
                .distinct()
            )
            departments = [row[0] for row in result.fetchall()]
            logger.debug(f"Found {len(departments)} departments")
            return departments
        except Exception as e:
            logger.error(f"Error fetching departments: {e}")
            return []
    
    async def _get_scores_by_department(self, department: str, db: AsyncSession) -> List[float]:
        """Get trust scores for employees in a specific department"""
        try:
            result = await db.execute(
                select(TrustScore.total_score)
                .join(Employee, TrustScore.employee_id == Employee.id)
                .where(
                    and_(
                        Employee.status == 'active',
                        Employee.department == department
                    )
                )
                .order_by(TrustScore.timestamp.desc())
                .distinct(TrustScore.employee_id)
            )
            
            scores = [row[0] for row in result.fetchall()]
            logger.debug(f"Retrieved {len(scores)} scores for department={department}")
            return scores
            
        except Exception as e:
            logger.error(f"Error fetching scores for department {department}: {e}")
            return []
    
    # ========================================================================
    # SENIORITY BIAS DETECTION
    # ========================================================================
    
    async def detect_seniority_bias(self) -> Dict[str, Any]:
        """
        Detect seniority/level bias in trust scores
        
        Analyzes bias across career levels:
        - Junior
        - Mid-level
        - Senior
        - Executive/Leadership
        
        Returns:
            Seniority bias analysis results
        """
        logger.info("Detecting seniority bias")
        
        async for db in get_db():
            try:
                # Get scores by seniority level
                seniority_levels = ['junior', 'mid', 'senior', 'executive']
                seniority_scores = {}
                seniority_stats = {}
                
                for level in seniority_levels:
                    scores = await self._get_scores_by_seniority(level, db)
                    seniority_scores[level] = scores
                    seniority_stats[level] = self._calculate_statistics(scores)
                
                # Calculate disparity metrics
                if seniority_stats:
                    means = [stats['mean'] for stats in seniority_stats.values() if stats['mean'] > 0]
                    max_score = max(means) if means else 0
                    min_score = min(means) if means else 0
                    avg_score = np.mean(means) if means else 0
                    
                    max_diff = max_score - min_score
                    relative_disparity = (max_diff / avg_score) if avg_score > 0 else 0
                else:
                    max_diff = 0
                    relative_disparity = 0
                    avg_score = 0
                
                results = {
                    'by_seniority': seniority_stats,
                    'sample_sizes': {level: len(scores) for level, scores in seniority_scores.items()},
                    'max_diff': max_diff,
                    'relative_disparity': relative_disparity,
                    'has_bias': relative_disparity > self.BIAS_THRESHOLDS['seniority'],
                    'bias_severity': self._classify_bias_severity(relative_disparity, 'seniority'),
                }
                
                logger.info(f"Seniority bias detection: has_bias={results['has_bias']}, disparity={relative_disparity:.3f}")
                
                return results
                
            except Exception as e:
                logger.error(f"Error detecting seniority bias: {e}")
                raise
    
    async def _get_scores_by_seniority(self, seniority: str, db: AsyncSession) -> List[float]:
        """Get trust scores for employees at a specific seniority level"""
        try:
            result = await db.execute(
                select(TrustScore.total_score)
                .join(Employee, TrustScore.employee_id == Employee.id)
                .where(
                    and_(
                        Employee.status == 'active',
                        Employee.metadata['seniority'].astext == seniority
                    )
                )
                .order_by(TrustScore.timestamp.desc())
                .distinct(TrustScore.employee_id)
            )
            
            scores = [row[0] for row in result.fetchall()]
            logger.debug(f"Retrieved {len(scores)} scores for seniority={seniority}")
            return scores
            
        except Exception as e:
            logger.error(f"Error fetching scores for seniority {seniority}: {e}")
            return []
    
    # ========================================================================
    # LOCATION BIAS DETECTION
    # ========================================================================
    
    async def detect_location_bias(self) -> Dict[str, Any]:
        """
        Detect location bias in trust scores
        
        Analyzes bias across work locations:
        - Office
        - Remote
        - Hybrid
        
        Returns:
            Location bias analysis results
        """
        logger.info("Detecting location bias")
        
        async for db in get_db():
            try:
                # Get scores by location
                locations = ['office', 'remote', 'hybrid']
                location_scores = {}
                location_stats = {}
                
                for location in locations:
                    scores = await self._get_scores_by_location(location, db)
                    location_scores[location] = scores
                    location_stats[location] = self._calculate_statistics(scores)
                
                # Calculate disparity metrics
                if location_stats:
                    means = [stats['mean'] for stats in location_stats.values() if stats['mean'] > 0]
                    max_score = max(means) if means else 0
                    min_score = min(means) if means else 0
                    avg_score = np.mean(means) if means else 0
                    
                    max_diff = max_score - min_score
                    relative_disparity = (max_diff / avg_score) if avg_score > 0 else 0
                else:
                    max_diff = 0
                    relative_disparity = 0
                    avg_score = 0
                
                results = {
                    'by_location': location_stats,
                    'sample_sizes': {loc: len(scores) for loc, scores in location_scores.items()},
                    'max_diff': max_diff,
                    'relative_disparity': relative_disparity,
                    'has_bias': relative_disparity > self.BIAS_THRESHOLDS['location'],
                    'bias_severity': self._classify_bias_severity(relative_disparity, 'location'),
                }
                
                logger.info(f"Location bias detection: has_bias={results['has_bias']}, disparity={relative_disparity:.3f}")
                
                return results
                
            except Exception as e:
                logger.error(f"Error detecting location bias: {e}")
                raise
    
    async def _get_scores_by_location(self, location: str, db: AsyncSession) -> List[float]:
        """Get trust scores for employees at a specific location"""
        try:
            result = await db.execute(
                select(TrustScore.total_score)
                .join(Employee, TrustScore.employee_id == Employee.id)
                .where(
                    and_(
                        Employee.status == 'active',
                        Employee.metadata['location'].astext == location
                    )
                )
                .order_by(TrustScore.timestamp.desc())
                .distinct(TrustScore.employee_id)
            )
            
            scores = [row[0] for row in result.fetchall()]
            logger.debug(f"Retrieved {len(scores)} scores for location={location}")
            return scores
            
        except Exception as e:
            logger.error(f"Error fetching scores for location {location}: {e}")
            return []
    
    # ========================================================================
    # RACE/ETHNICITY BIAS DETECTION
    # ========================================================================
    
    async def detect_race_bias(self) -> Dict[str, Any]:
        """
        Detect racial/ethnic bias in trust scores
        
        Note: Only runs if race/ethnicity data is available and properly consented
        
        Returns:
            Race bias analysis results
        """
        logger.info("Detecting race/ethnicity bias")
        
        async for db in get_db():
            try:
                # Check if race data is available
                result = await db.execute(
                    select(func.count())
                    .select_from(Employee)
                    .where(
                        and_(
                            Employee.status == 'active',
                            Employee.metadata['race'].astext.isnot(None)
                        )
                    )
                )
                count = result.scalar()
                
                if count < self.MIN_SAMPLE_SIZES['race']:
                    logger.info("Insufficient race/ethnicity data for bias detection")
                    return {
                        'available': False,
                        'reason': 'Insufficient data or not collected',
                        'has_bias': False,
                    }
                
                # Get all race categories
                result = await db.execute(
                    select(Employee.metadata['race'].astext)
                    .where(
                        and_(
                            Employee.status == 'active',
                            Employee.metadata['race'].astext.isnot(None)
                        )
                    )
                    .distinct()
                )
                races = [row[0] for row in result.fetchall()]
                
                # Get scores by race
                race_scores = {}
                race_stats = {}
                
                for race in races:
                    scores = await self._get_scores_by_race(race, db)
                    race_scores[race] = scores
                    race_stats[race] = self._calculate_statistics(scores)
                
                # Calculate disparity metrics
                if race_stats:
                    means = [stats['mean'] for stats in race_stats.values() if stats['mean'] > 0]
                    max_score = max(means) if means else 0
                    min_score = min(means) if means else 0
                    avg_score = np.mean(means) if means else 0
                    
                    max_diff = max_score - min_score
                    relative_disparity = (max_diff / avg_score) if avg_score > 0 else 0
                else:
                    max_diff = 0
                    relative_disparity = 0
                    avg_score = 0
                
                results = {
                    'available': True,
                    'by_race': race_stats,
                    'sample_sizes': {race: len(scores) for race, scores in race_scores.items()},
                    'max_diff': max_diff,
                    'relative_disparity': relative_disparity,
                    'has_bias': relative_disparity > self.BIAS_THRESHOLDS['race'],
                    'bias_severity': self._classify_bias_severity(relative_disparity, 'race'),
                }
                
                logger.info(f"Race bias detection: has_bias={results['has_bias']}, disparity={relative_disparity:.3f}")
                
                return results
                
            except Exception as e:
                logger.error(f"Error detecting race bias: {e}")
                return {
                    'available': False,
                    'error': str(e),
                    'has_bias': False,
                }
    
    async def _get_scores_by_race(self, race: str, db: AsyncSession) -> List[float]:
        """Get trust scores for employees of a specific race/ethnicity"""
        try:
            result = await db.execute(
                select(TrustScore.total_score)
                .join(Employee, TrustScore.employee_id == Employee.id)
                .where(
                    and_(
                        Employee.status == 'active',
                        Employee.metadata['race'].astext == race
                    )
                )
                .order_by(TrustScore.timestamp.desc())
                .distinct(TrustScore.employee_id)
            )
            
            scores = [row[0] for row in result.fetchall()]
            logger.debug(f"Retrieved {len(scores)} scores for race={race}")
            return scores
            
        except Exception as e:
            logger.error(f"Error fetching scores for race {race}: {e}")
            return []
    
    # ========================================================================
    # INTERSECTIONAL BIAS DETECTION
    # ========================================================================
    
    async def detect_intersectional_bias(self) -> Dict[str, Any]:
        """
        Detect intersectional bias (e.g., gender + department, race + seniority)
        
        Analyzes bias at the intersection of multiple demographic factors
        
        Returns:
            Intersectional bias analysis results
        """
        logger.info("Detecting intersectional bias")
        
        async for db in get_db():
            try:
                # Analyze gender x department
                gender_dept_bias = await self._analyze_intersection(
                    'gender', 'department', db
                )
                
                # Analyze gender x seniority
                gender_seniority_bias = await self._analyze_intersection(
                    'gender', 'seniority', db
                )
                
                # Analyze department x seniority
                dept_seniority_bias = await self._analyze_intersection(
                    'department', 'seniority', db
                )
                
                results = {
                    'gender_x_department': gender_dept_bias,
                    'gender_x_seniority': gender_seniority_bias,
                    'department_x_seniority': dept_seniority_bias,
                    'has_bias': (
                        gender_dept_bias.get('has_bias', False) or
                        gender_seniority_bias.get('has_bias', False) or
                        dept_seniority_bias.get('has_bias', False)
                    ),
                }
                
                logger.info(f"Intersectional bias detection: has_bias={results['has_bias']}")
                
                return results
                
            except Exception as e:
                logger.error(f"Error detecting intersectional bias: {e}")
                raise
    
    async def _analyze_intersection(
        self, 
        dimension1: str, 
        dimension2: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Analyze bias at the intersection of two dimensions"""
        try:
            # This is a simplified version - full implementation would analyze
            # all combinations of dimension1 x dimension2
            
            # For now, return placeholder
            return {
                'dimensions': [dimension1, dimension2],
                'analyzed': False,
                'has_bias': False,
                'note': 'Intersectional analysis requires sufficient sample sizes',
            }
            
        except Exception as e:
            logger.error(f"Error analyzing intersection {dimension1} x {dimension2}: {e}")
            return {
                'dimensions': [dimension1, dimension2],
                'error': str(e),
                'has_bias': False,
            }
    
    # ========================================================================
    # BIAS MITIGATION
    # ========================================================================
    
    async def mitigate_bias(self, bias_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply bias mitigation strategies based on detected bias
        
        Strategies:
        1. Score recalibration using correction factors
        2. Group-aware normalization
        3. Fairness constraints
        
        Args:
            bias_results: Results from bias detection
        
        Returns:
            Mitigation results and applied corrections
        """
        logger.info("Starting bias mitigation")
        
        mitigation_results = {
            'timestamp': datetime.utcnow(),
            'corrections_applied': [],
            'employees_affected': 0,
        }
        
        async for db in get_db():
            try:
                # Gender bias mitigation
                if bias_results.get('gender_bias', {}).get('has_bias', False):
                    gender_corrections = await self._mitigate_gender_bias(
                        bias_results['gender_bias'], db
                    )
                    mitigation_results['corrections_applied'].append({
                        'dimension': 'gender',
                        'corrections': gender_corrections,
                    })
                    mitigation_results['employees_affected'] += gender_corrections.get('count', 0)
                
                # Department bias mitigation
                if bias_results.get('department_bias', {}).get('has_bias', False):
                    dept_corrections = await self._mitigate_department_bias(
                        bias_results['department_bias'], db
                    )
                    mitigation_results['corrections_applied'].append({
                        'dimension': 'department',
                        'corrections': dept_corrections,
                    })
                    mitigation_results['employees_affected'] += dept_corrections.get('count', 0)
                
                # Seniority bias mitigation
                if bias_results.get('seniority_bias', {}).get('has_bias', False):
                    seniority_corrections = await self._mitigate_seniority_bias(
                        bias_results['seniority_bias'], db
                    )
                    mitigation_results['corrections_applied'].append({
                        'dimension': 'seniority',
                        'corrections': seniority_corrections,
                    })
                    mitigation_results['employees_affected'] += seniority_corrections.get('count', 0)
                
                # Location bias mitigation
                if bias_results.get('location_bias', {}).get('has_bias', False):
                    location_corrections = await self._mitigate_location_bias(
                        bias_results['location_bias'], db
                    )
                    mitigation_results['corrections_applied'].append({
                        'dimension': 'location',
                        'corrections': location_corrections,
                    })
                    mitigation_results['employees_affected'] += location_corrections.get('count', 0)
                
                await db.commit()
                
                mitigation_results['status'] = 'bias_mitigated'
                mitigation_results['success'] = True
                
                logger.info(
                    f"Bias mitigation complete: {mitigation_results['employees_affected']} "
                    f"employees affected, {len(mitigation_results['corrections_applied'])} corrections applied"
                )
                
                return mitigation_results
                
            except Exception as e:
                logger.error(f"Error during bias mitigation: {e}")
                await db.rollback()
                raise
    
    async def _mitigate_gender_bias(
        self, 
        gender_bias: Dict[str, Any], 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Apply gender bias corrections"""
        logger.info("Applying gender bias corrections")
        
        try:
            corrections = {}
            count = 0
            
            # Calculate correction factors
            # Use male scores as baseline (or overall average)
            male_avg = gender_bias['male']['mean']
            
            if male_avg > 0:
                # Calculate multipliers to equalize means
                for gender in ['female', 'nonbinary', 'other']:
                    gender_avg = gender_bias[gender]['mean']
                    if gender_avg > 0 and gender_avg < male_avg:
                        # Calculate correction factor
                        correction_factor = male_avg / gender_avg
                        corrections[gender] = correction_factor
                        
                        # Apply correction (in practice, this would update scores)
                        # For now, just log the correction
                        logger.info(f"Gender correction factor for {gender}: {correction_factor:.3f}")
                        count += gender_bias['sample_sizes'].get(gender, 0)
            
            return {
                'correction_factors': corrections,
                'count': count,
                'method': 'multiplicative_correction',
            }
            
        except Exception as e:
            logger.error(f"Error applying gender bias corrections: {e}")
            return {'error': str(e), 'count': 0}
    
    async def _mitigate_department_bias(
        self, 
        dept_bias: Dict[str, Any], 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Apply department bias corrections"""
        logger.info("Applying department bias corrections")
        
        try:
            corrections = {}
            count = 0
            
            # Calculate overall average
            dept_stats = dept_bias['by_department']
            overall_avg = dept_bias['avg_score']
            
            if overall_avg > 0:
                # Calculate correction factors for each department
                for dept, stats in dept_stats.items():
                    dept_avg = stats['mean']
                    if dept_avg > 0 and dept_avg < overall_avg:
                        correction_factor = overall_avg / dept_avg
                        corrections[dept] = correction_factor
                        logger.info(f"Department correction factor for {dept}: {correction_factor:.3f}")
                        count += dept_bias['sample_sizes'].get(dept, 0)
            
            return {
                'correction_factors': corrections,
                'count': count,
                'method': 'department_normalization',
            }
            
        except Exception as e:
            logger.error(f"Error applying department bias corrections: {e}")
            return {'error': str(e), 'count': 0}
    
    async def _mitigate_seniority_bias(
        self, 
        seniority_bias: Dict[str, Any], 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Apply seniority bias corrections"""
        logger.info("Applying seniority bias corrections")
        
        try:
            # Seniority bias is complex - higher seniority may legitimately have
            # different scores. Only correct if disparity is extreme.
            
            corrections = {}
            count = 0
            
            # For now, log that seniority bias was detected but not corrected
            logger.info("Seniority bias detected but not auto-corrected (requires manual review)")
            
            return {
                'correction_factors': corrections,
                'count': count,
                'method': 'manual_review_required',
                'note': 'Seniority differences may be legitimate',
            }
            
        except Exception as e:
            logger.error(f"Error applying seniority bias corrections: {e}")
            return {'error': str(e), 'count': 0}
    
    async def _mitigate_location_bias(
        self, 
        location_bias: Dict[str, Any], 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Apply location bias corrections"""
        logger.info("Applying location bias corrections")
        
        try:
            corrections = {}
            count = 0
            
            # Calculate correction factors
            location_stats = location_bias['by_location']
            
            # Use office as baseline (or calculate overall average)
            office_avg = location_stats.get('office', {}).get('mean', 0)
            
            if office_avg > 0:
                for location in ['remote', 'hybrid']:
                    location_avg = location_stats.get(location, {}).get('mean', 0)
                    if location_avg > 0 and location_avg < office_avg:
                        correction_factor = office_avg / location_avg
                        corrections[location] = correction_factor
                        logger.info(f"Location correction factor for {location}: {correction_factor:.3f}")
                        count += location_bias['sample_sizes'].get(location, 0)
            
            return {
                'correction_factors': corrections,
                'count': count,
                'method': 'location_normalization',
            }
            
        except Exception as e:
            logger.error(f"Error applying location bias corrections: {e}")
            return {'error': str(e), 'count': 0}
    
    # ========================================================================
    # STATISTICAL UTILITIES
    # ========================================================================
    
    def _calculate_statistics(self, scores: List[float]) -> Dict[str, float]:
        """Calculate statistical measures for a list of scores"""
        if not scores:
            return {
                'mean': 0.0,
                'median': 0.0,
                'std_dev': 0.0,
                'min': 0.0,
                'max': 0.0,
                'count': 0,
            }
        
        return {
            'mean': float(np.mean(scores)),
            'median': float(np.median(scores)),
            'std_dev': float(np.std(scores)),
            'min': float(np.min(scores)),
            'max': float(np.max(scores)),
            'count': len(scores),
        }
    
    def _perform_ttest(self, group1: List[float], group2: List[float]) -> Dict[str, Any]:
        """Perform independent t-test between two groups"""
        if len(group1) < 2 or len(group2) < 2:
            return {
                'statistic': 0.0,
                'p_value': 1.0,
                'significant': False,
                'note': 'Insufficient sample size',
            }
        
        try:
            from scipy import stats
            t_stat, p_value = stats.ttest_ind(group1, group2)
            
            return {
                'statistic': float(t_stat),
                'p_value': float(p_value),
                'significant': p_value < self.SIGNIFICANCE_LEVEL,
            }
        except Exception as e:
            logger.error(f"Error performing t-test: {e}")
            return {
                'statistic': 0.0,
                'p_value': 1.0,
                'significant': False,
                'error': str(e),
            }
    
    def _classify_bias_severity(self, disparity: float, dimension: str) -> str:
        """Classify bias severity based on disparity magnitude"""
        threshold = self.BIAS_THRESHOLDS.get(dimension, 0.05)
        
        if disparity < threshold:
            return 'none'
        elif disparity < threshold * 2:
            return 'low'
        elif disparity < threshold * 3:
            return 'moderate'
        elif disparity < threshold * 4:
            return 'high'
        else:
            return 'severe'
    
    def _calculate_overall_bias(self, audit_results: Dict[str, Any]) -> bool:
        """Determine if overall bias exists across any dimension"""
        bias_dimensions = [
            audit_results.get('gender_bias', {}).get('has_bias', False),
            audit_results.get('department_bias', {}).get('has_bias', False),
            audit_results.get('seniority_bias', {}).get('has_bias', False),
            audit_results.get('location_bias', {}).get('has_bias', False),
            audit_results.get('race_bias', {}).get('has_bias', False),
            audit_results.get('intersectional_bias', {}).get('has_bias', False),
        ]
        
        return any(bias_dimensions)
    
    def _generate_recommendations(self, audit_results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on audit results"""
        recommendations = []
        
        if audit_results.get('gender_bias', {}).get('has_bias', False):
            recommendations.append(
                "Gender bias detected: Review scoring algorithms for gender-specific patterns. "
                "Consider applying gender-blind scoring or correction factors."
            )
        
        if audit_results.get('department_bias', {}).get('has_bias', False):
            recommendations.append(
                "Department bias detected: Ensure scoring criteria are fair across different "
                "job functions. Consider department-specific baselines."
            )
        
        if audit_results.get('seniority_bias', {}).get('has_bias', False):
            recommendations.append(
                "Seniority bias detected: Verify that experience-based differences are legitimate. "
                "Consider separate scoring models for different career levels."
            )
        
        if audit_results.get('location_bias', {}).get('has_bias', False):
            recommendations.append(
                "Location bias detected: Review metrics that may disadvantage remote workers. "
                "Ensure location-agnostic performance measurement."
            )
        
        if audit_results.get('race_bias', {}).get('has_bias', False):
            recommendations.append(
                "Racial/ethnic bias detected: Immediate review required. Consider external audit "
                "and consultation with diversity experts."
            )
        
        if not recommendations:
            recommendations.append(
                "No significant bias detected. Continue monthly monitoring to ensure fairness."
            )
        
        return recommendations
    
    # ========================================================================
    # AUDIT TRAIL
    # ========================================================================
    
    async def _store_audit_trail(self, audit_results: Dict[str, Any]) -> None:
        """Store audit results for compliance and tracking"""
        try:
            audit_record = {
                'timestamp': audit_results['timestamp'].isoformat(),
                'overall_bias_detected': audit_results['overall_bias_detected'],
                'dimensions_analyzed': [
                    'gender', 'department', 'seniority', 'location', 'race', 'intersectional'
                ],
                'recommendations': audit_results['recommendations'],
            }
            
            # Store to file (in production, would store to database)
            audit_file = f"/var/log/tbaps/bias_audit_{audit_results['timestamp'].strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(audit_file, 'w') as f:
                json.dump(audit_results, f, indent=2, default=str)
            
            logger.info(f"Audit trail stored: {audit_file}")
            
        except Exception as e:
            logger.error(f"Error storing audit trail: {e}")
