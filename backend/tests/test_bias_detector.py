"""
Tests for Bias Detection and Mitigation System

Comprehensive test suite covering:
- Gender bias detection
- Department bias detection
- Seniority bias detection
- Location bias detection
- Bias mitigation strategies
- Statistical calculations
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from app.services.bias_detector import BiasDetector


class TestBiasDetector:
    """Test suite for BiasDetector class"""
    
    @pytest.fixture
    def detector(self):
        """Create BiasDetector instance"""
        return BiasDetector()
    
    @pytest.fixture
    def sample_scores_equal(self):
        """Sample scores with no bias"""
        return {
            'male': [75.0, 76.0, 74.0, 77.0, 75.5],
            'female': [75.2, 74.8, 76.1, 75.0, 74.9],
            'nonbinary': [75.5, 75.0, 74.5],
        }
    
    @pytest.fixture
    def sample_scores_biased(self):
        """Sample scores with gender bias"""
        return {
            'male': [80.0, 81.0, 79.0, 82.0, 80.5],
            'female': [70.0, 71.0, 69.0, 72.0, 70.5],  # 10 points lower
            'nonbinary': [75.0, 74.0, 76.0],
        }
    
    # ========================================================================
    # STATISTICAL UTILITIES TESTS
    # ========================================================================
    
    def test_calculate_statistics_valid_scores(self, detector):
        """Test statistical calculations with valid scores"""
        scores = [70.0, 75.0, 80.0, 85.0, 90.0]
        
        stats = detector._calculate_statistics(scores)
        
        assert stats['count'] == 5
        assert stats['mean'] == 80.0
        assert stats['median'] == 80.0
        assert stats['min'] == 70.0
        assert stats['max'] == 90.0
        assert stats['std_dev'] > 0
    
    def test_calculate_statistics_empty_scores(self, detector):
        """Test statistical calculations with empty list"""
        stats = detector._calculate_statistics([])
        
        assert stats['count'] == 0
        assert stats['mean'] == 0.0
        assert stats['median'] == 0.0
    
    def test_calculate_statistics_single_score(self, detector):
        """Test statistical calculations with single score"""
        stats = detector._calculate_statistics([75.0])
        
        assert stats['count'] == 1
        assert stats['mean'] == 75.0
        assert stats['median'] == 75.0
        assert stats['std_dev'] == 0.0
    
    def test_perform_ttest_significant_difference(self, detector):
        """Test t-test with significantly different groups"""
        group1 = [80.0, 81.0, 82.0, 83.0, 84.0] * 10  # Higher scores
        group2 = [70.0, 71.0, 72.0, 73.0, 74.0] * 10  # Lower scores
        
        result = detector._perform_ttest(group1, group2)
        
        assert 'statistic' in result
        assert 'p_value' in result
        assert result['significant'] is True  # Should be significant
        assert result['p_value'] < 0.05
    
    def test_perform_ttest_no_difference(self, detector):
        """Test t-test with similar groups"""
        group1 = [75.0, 76.0, 74.0, 77.0, 75.5] * 10
        group2 = [75.2, 74.8, 76.1, 75.0, 74.9] * 10
        
        result = detector._perform_ttest(group1, group2)
        
        assert result['significant'] is False  # Should not be significant
        assert result['p_value'] > 0.05
    
    def test_perform_ttest_insufficient_data(self, detector):
        """Test t-test with insufficient sample size"""
        group1 = [75.0]
        group2 = [76.0]
        
        result = detector._perform_ttest(group1, group2)
        
        assert result['significant'] is False
        assert 'note' in result
    
    # ========================================================================
    # BIAS SEVERITY CLASSIFICATION TESTS
    # ========================================================================
    
    def test_classify_bias_severity_none(self, detector):
        """Test bias severity classification - no bias"""
        severity = detector._classify_bias_severity(0.02, 'gender')
        assert severity == 'none'
    
    def test_classify_bias_severity_low(self, detector):
        """Test bias severity classification - low bias"""
        severity = detector._classify_bias_severity(0.07, 'gender')
        assert severity == 'low'
    
    def test_classify_bias_severity_moderate(self, detector):
        """Test bias severity classification - moderate bias"""
        severity = detector._classify_bias_severity(0.12, 'gender')
        assert severity == 'moderate'
    
    def test_classify_bias_severity_high(self, detector):
        """Test bias severity classification - high bias"""
        severity = detector._classify_bias_severity(0.18, 'gender')
        assert severity == 'high'
    
    def test_classify_bias_severity_severe(self, detector):
        """Test bias severity classification - severe bias"""
        severity = detector._classify_bias_severity(0.25, 'gender')
        assert severity == 'severe'
    
    # ========================================================================
    # GENDER BIAS DETECTION TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_detect_gender_bias_no_bias(self, detector, sample_scores_equal):
        """Test gender bias detection with equal scores"""
        with patch.object(detector, '_get_scores_by_gender') as mock_get_scores:
            # Mock database calls
            async def get_scores_side_effect(gender, db):
                return sample_scores_equal.get(gender, [])
            
            mock_get_scores.side_effect = get_scores_side_effect
            
            # Mock get_db
            with patch('app.services.bias_detector.get_db') as mock_db:
                mock_db.return_value.__aiter__.return_value = [AsyncMock()]
                
                results = await detector.detect_gender_bias()
                
                assert results['has_bias'] is False
                assert results['bias_severity'] == 'none'
                assert 'disparity_ratios' in results
    
    @pytest.mark.asyncio
    async def test_detect_gender_bias_with_bias(self, detector, sample_scores_biased):
        """Test gender bias detection with biased scores"""
        with patch.object(detector, '_get_scores_by_gender') as mock_get_scores:
            # Mock database calls
            async def get_scores_side_effect(gender, db):
                return sample_scores_biased.get(gender, [])
            
            mock_get_scores.side_effect = get_scores_side_effect
            
            # Mock get_db
            with patch('app.services.bias_detector.get_db') as mock_db:
                mock_db.return_value.__aiter__.return_value = [AsyncMock()]
                
                results = await detector.detect_gender_bias()
                
                assert results['has_bias'] is True
                assert results['bias_severity'] in ['moderate', 'high', 'severe']
                assert results['max_disparity'] > detector.BIAS_THRESHOLDS['gender']
    
    @pytest.mark.asyncio
    async def test_detect_gender_bias_disparity_ratios(self, detector, sample_scores_biased):
        """Test gender bias disparity ratio calculations"""
        with patch.object(detector, '_get_scores_by_gender') as mock_get_scores:
            async def get_scores_side_effect(gender, db):
                return sample_scores_biased.get(gender, [])
            
            mock_get_scores.side_effect = get_scores_side_effect
            
            with patch('app.services.bias_detector.get_db') as mock_db:
                mock_db.return_value.__aiter__.return_value = [AsyncMock()]
                
                results = await detector.detect_gender_bias()
                
                # Female scores should be ~0.875 of male scores (70/80)
                assert 'disparity_ratios' in results
                assert 'female_vs_male' in results['disparity_ratios']
                assert 0.85 < results['disparity_ratios']['female_vs_male'] < 0.90
    
    # ========================================================================
    # DEPARTMENT BIAS DETECTION TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_detect_department_bias_no_bias(self, detector):
        """Test department bias detection with equal scores"""
        dept_scores = {
            'engineering': [75.0, 76.0, 74.0, 77.0],
            'sales': [75.5, 74.5, 76.0, 75.0],
            'marketing': [74.8, 75.2, 75.5, 74.5],
        }
        
        with patch.object(detector, '_get_all_departments') as mock_get_depts:
            with patch.object(detector, '_get_scores_by_department') as mock_get_scores:
                mock_get_depts.return_value = list(dept_scores.keys())
                
                async def get_scores_side_effect(dept, db):
                    return dept_scores.get(dept, [])
                
                mock_get_scores.side_effect = get_scores_side_effect
                
                with patch('app.services.bias_detector.get_db') as mock_db:
                    mock_db.return_value.__aiter__.return_value = [AsyncMock()]
                    
                    results = await detector.detect_department_bias()
                    
                    assert results['has_bias'] is False
                    assert results['relative_disparity'] < detector.BIAS_THRESHOLDS['department']
    
    @pytest.mark.asyncio
    async def test_detect_department_bias_with_bias(self, detector):
        """Test department bias detection with biased scores"""
        dept_scores = {
            'engineering': [85.0, 86.0, 84.0, 87.0],  # High scores
            'sales': [70.0, 71.0, 69.0, 72.0],        # Low scores
            'marketing': [75.0, 76.0, 74.0, 77.0],    # Medium scores
        }
        
        with patch.object(detector, '_get_all_departments') as mock_get_depts:
            with patch.object(detector, '_get_scores_by_department') as mock_get_scores:
                mock_get_depts.return_value = list(dept_scores.keys())
                
                async def get_scores_side_effect(dept, db):
                    return dept_scores.get(dept, [])
                
                mock_get_scores.side_effect = get_scores_side_effect
                
                with patch('app.services.bias_detector.get_db') as mock_db:
                    mock_db.return_value.__aiter__.return_value = [AsyncMock()]
                    
                    results = await detector.detect_department_bias()
                    
                    assert results['has_bias'] is True
                    assert results['highest_scoring'] == 'engineering'
                    assert results['lowest_scoring'] == 'sales'
                    assert results['max_diff'] > 10  # ~15 point difference
    
    # ========================================================================
    # SENIORITY BIAS DETECTION TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_detect_seniority_bias_no_bias(self, detector):
        """Test seniority bias detection with equal scores"""
        seniority_scores = {
            'junior': [75.0, 76.0, 74.0],
            'mid': [75.5, 74.5, 76.0],
            'senior': [74.8, 75.2, 75.5],
            'executive': [75.0, 75.5, 74.5],
        }
        
        with patch.object(detector, '_get_scores_by_seniority') as mock_get_scores:
            async def get_scores_side_effect(level, db):
                return seniority_scores.get(level, [])
            
            mock_get_scores.side_effect = get_scores_side_effect
            
            with patch('app.services.bias_detector.get_db') as mock_db:
                mock_db.return_value.__aiter__.return_value = [AsyncMock()]
                
                results = await detector.detect_seniority_bias()
                
                assert results['has_bias'] is False
                assert results['relative_disparity'] < detector.BIAS_THRESHOLDS['seniority']
    
    @pytest.mark.asyncio
    async def test_detect_seniority_bias_with_bias(self, detector):
        """Test seniority bias detection with biased scores"""
        seniority_scores = {
            'junior': [65.0, 66.0, 64.0],     # Low scores
            'mid': [75.0, 76.0, 74.0],        # Medium scores
            'senior': [85.0, 86.0, 84.0],     # High scores
            'executive': [90.0, 91.0, 89.0],  # Very high scores
        }
        
        with patch.object(detector, '_get_scores_by_seniority') as mock_get_scores:
            async def get_scores_side_effect(level, db):
                return seniority_scores.get(level, [])
            
            mock_get_scores.side_effect = get_scores_side_effect
            
            with patch('app.services.bias_detector.get_db') as mock_db:
                mock_db.return_value.__aiter__.return_value = [AsyncMock()]
                
                results = await detector.detect_seniority_bias()
                
                assert results['has_bias'] is True
                assert results['max_diff'] > 20  # ~25 point difference
    
    # ========================================================================
    # LOCATION BIAS DETECTION TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_detect_location_bias_no_bias(self, detector):
        """Test location bias detection with equal scores"""
        location_scores = {
            'office': [75.0, 76.0, 74.0, 77.0],
            'remote': [75.5, 74.5, 76.0, 75.0],
            'hybrid': [74.8, 75.2, 75.5, 74.5],
        }
        
        with patch.object(detector, '_get_scores_by_location') as mock_get_scores:
            async def get_scores_side_effect(location, db):
                return location_scores.get(location, [])
            
            mock_get_scores.side_effect = get_scores_side_effect
            
            with patch('app.services.bias_detector.get_db') as mock_db:
                mock_db.return_value.__aiter__.return_value = [AsyncMock()]
                
                results = await detector.detect_location_bias()
                
                assert results['has_bias'] is False
                assert results['relative_disparity'] < detector.BIAS_THRESHOLDS['location']
    
    @pytest.mark.asyncio
    async def test_detect_location_bias_with_bias(self, detector):
        """Test location bias detection with biased scores"""
        location_scores = {
            'office': [85.0, 86.0, 84.0, 87.0],  # High scores
            'remote': [70.0, 71.0, 69.0, 72.0],  # Low scores
            'hybrid': [77.0, 78.0, 76.0, 79.0],  # Medium scores
        }
        
        with patch.object(detector, '_get_scores_by_location') as mock_get_scores:
            async def get_scores_side_effect(location, db):
                return location_scores.get(location, [])
            
            mock_get_scores.side_effect = get_scores_side_effect
            
            with patch('app.services.bias_detector.get_db') as mock_db:
                mock_db.return_value.__aiter__.return_value = [AsyncMock()]
                
                results = await detector.detect_location_bias()
                
                assert results['has_bias'] is True
                assert results['max_diff'] > 10  # ~15 point difference
    
    # ========================================================================
    # BIAS MITIGATION TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_mitigate_gender_bias(self, detector):
        """Test gender bias mitigation"""
        gender_bias = {
            'male': {'mean': 80.0},
            'female': {'mean': 70.0},
            'nonbinary': {'mean': 75.0},
            'other': {'mean': 0.0},
            'sample_sizes': {
                'male': 100,
                'female': 100,
                'nonbinary': 20,
                'other': 0,
            },
            'has_bias': True,
        }
        
        with patch('app.services.bias_detector.get_db') as mock_db:
            mock_db.return_value.__aiter__.return_value = [AsyncMock()]
            
            result = await detector._mitigate_gender_bias(gender_bias, AsyncMock())
            
            assert 'correction_factors' in result
            assert 'female' in result['correction_factors']
            assert result['correction_factors']['female'] > 1.0  # Should boost female scores
            assert result['count'] > 0
    
    @pytest.mark.asyncio
    async def test_mitigate_department_bias(self, detector):
        """Test department bias mitigation"""
        dept_bias = {
            'by_department': {
                'engineering': {'mean': 85.0},
                'sales': {'mean': 70.0},
                'marketing': {'mean': 75.0},
            },
            'avg_score': 76.67,
            'sample_sizes': {
                'engineering': 50,
                'sales': 50,
                'marketing': 50,
            },
            'has_bias': True,
        }
        
        with patch('app.services.bias_detector.get_db') as mock_db:
            mock_db.return_value.__aiter__.return_value = [AsyncMock()]
            
            result = await detector._mitigate_department_bias(dept_bias, AsyncMock())
            
            assert 'correction_factors' in result
            assert 'sales' in result['correction_factors']  # Lowest scoring
            assert result['correction_factors']['sales'] > 1.0
    
    @pytest.mark.asyncio
    async def test_mitigate_bias_full_workflow(self, detector, sample_scores_biased):
        """Test full bias mitigation workflow"""
        # Create mock audit results
        audit_results = {
            'gender_bias': {
                'has_bias': True,
                'male': {'mean': 80.0},
                'female': {'mean': 70.0},
                'nonbinary': {'mean': 75.0},
                'other': {'mean': 0.0},
                'sample_sizes': {
                    'male': 100,
                    'female': 100,
                    'nonbinary': 20,
                    'other': 0,
                },
            },
            'department_bias': {'has_bias': False},
            'seniority_bias': {'has_bias': False},
            'location_bias': {'has_bias': False},
            'race_bias': {'has_bias': False},
        }
        
        with patch('app.services.bias_detector.get_db') as mock_db:
            mock_db.return_value.__aiter__.return_value = [AsyncMock()]
            
            result = await detector.mitigate_bias(audit_results)
            
            assert result['status'] == 'bias_mitigated'
            assert result['success'] is True
            assert len(result['corrections_applied']) > 0
            assert result['employees_affected'] > 0
    
    # ========================================================================
    # OVERALL BIAS CALCULATION TESTS
    # ========================================================================
    
    def test_calculate_overall_bias_no_bias(self, detector):
        """Test overall bias calculation with no bias"""
        audit_results = {
            'gender_bias': {'has_bias': False},
            'department_bias': {'has_bias': False},
            'seniority_bias': {'has_bias': False},
            'location_bias': {'has_bias': False},
            'race_bias': {'has_bias': False},
            'intersectional_bias': {'has_bias': False},
        }
        
        overall = detector._calculate_overall_bias(audit_results)
        assert overall is False
    
    def test_calculate_overall_bias_with_bias(self, detector):
        """Test overall bias calculation with bias detected"""
        audit_results = {
            'gender_bias': {'has_bias': True},
            'department_bias': {'has_bias': False},
            'seniority_bias': {'has_bias': False},
            'location_bias': {'has_bias': False},
            'race_bias': {'has_bias': False},
            'intersectional_bias': {'has_bias': False},
        }
        
        overall = detector._calculate_overall_bias(audit_results)
        assert overall is True
    
    # ========================================================================
    # RECOMMENDATIONS TESTS
    # ========================================================================
    
    def test_generate_recommendations_no_bias(self, detector):
        """Test recommendation generation with no bias"""
        audit_results = {
            'gender_bias': {'has_bias': False},
            'department_bias': {'has_bias': False},
            'seniority_bias': {'has_bias': False},
            'location_bias': {'has_bias': False},
            'race_bias': {'has_bias': False},
        }
        
        recommendations = detector._generate_recommendations(audit_results)
        
        assert len(recommendations) == 1
        assert 'No significant bias' in recommendations[0]
    
    def test_generate_recommendations_with_bias(self, detector):
        """Test recommendation generation with bias detected"""
        audit_results = {
            'gender_bias': {'has_bias': True},
            'department_bias': {'has_bias': True},
            'seniority_bias': {'has_bias': False},
            'location_bias': {'has_bias': False},
            'race_bias': {'has_bias': False},
        }
        
        recommendations = detector._generate_recommendations(audit_results)
        
        assert len(recommendations) >= 2
        assert any('Gender bias' in rec for rec in recommendations)
        assert any('Department bias' in rec for rec in recommendations)
    
    def test_generate_recommendations_race_bias(self, detector):
        """Test recommendation generation with race bias"""
        audit_results = {
            'gender_bias': {'has_bias': False},
            'department_bias': {'has_bias': False},
            'seniority_bias': {'has_bias': False},
            'location_bias': {'has_bias': False},
            'race_bias': {'has_bias': True},
        }
        
        recommendations = detector._generate_recommendations(audit_results)
        
        assert len(recommendations) >= 1
        assert any('Racial/ethnic bias' in rec for rec in recommendations)
        assert any('Immediate review' in rec for rec in recommendations)


# ========================================================================
# INTEGRATION TESTS
# ========================================================================

class TestBiasDetectorIntegration:
    """Integration tests for BiasDetector"""
    
    @pytest.mark.asyncio
    async def test_full_audit_workflow(self):
        """Test complete audit workflow"""
        detector = BiasDetector()
        
        # Mock all database calls
        with patch('app.services.bias_detector.get_db') as mock_db:
            mock_db.return_value.__aiter__.return_value = [AsyncMock()]
            
            with patch.object(detector, 'detect_gender_bias') as mock_gender:
                with patch.object(detector, 'detect_department_bias') as mock_dept:
                    with patch.object(detector, 'detect_seniority_bias') as mock_seniority:
                        with patch.object(detector, 'detect_location_bias') as mock_location:
                            with patch.object(detector, 'detect_race_bias') as mock_race:
                                with patch.object(detector, 'detect_intersectional_bias') as mock_intersect:
                                    # Mock return values
                                    mock_gender.return_value = {'has_bias': False}
                                    mock_dept.return_value = {'has_bias': False}
                                    mock_seniority.return_value = {'has_bias': False}
                                    mock_location.return_value = {'has_bias': False}
                                    mock_race.return_value = {'has_bias': False}
                                    mock_intersect.return_value = {'has_bias': False}
                                    
                                    with patch.object(detector, '_store_audit_trail'):
                                        result = await detector.run_full_audit()
                                        
                                        assert 'timestamp' in result
                                        assert 'overall_bias_detected' in result
                                        assert 'recommendations' in result
                                        assert 'audit_duration_seconds' in result
                                        assert result['overall_bias_detected'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
