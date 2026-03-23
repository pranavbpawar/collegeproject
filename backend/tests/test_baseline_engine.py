"""
Unit Tests for Baseline Establishment Engine
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.baseline_engine import BaselineEngine


class TestBaselineEngine:
    """Test suite for BaselineEngine"""
    
    @pytest.fixture
    def engine(self):
        """Create baseline engine instance"""
        return BaselineEngine(min_days=14, target_days=30)
    
    def test_calculate_statistics_normal(self, engine):
        """Test statistical calculations with normal data"""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        stats = engine._calculate_statistics(values)
        
        assert stats['mean'] == pytest.approx(55.0)
        assert stats['median'] == pytest.approx(55.0)
        assert stats['min_value'] == 10.0
        assert stats['max_value'] == 100.0
        assert stats['sample_size'] == 10
        assert 'std_dev' in stats
        assert 'p05' in stats
        assert 'p25' in stats
        assert 'p75' in stats
        assert 'p95' in stats
    
    def test_calculate_statistics_single_value(self, engine):
        """Test statistical calculations with single value"""
        values = [42.0]
        stats = engine._calculate_statistics(values)
        
        assert stats['mean'] == 42.0
        assert stats['median'] == 42.0
        assert stats['std_dev'] == 0.0
        assert stats['min_value'] == 42.0
        assert stats['max_value'] == 42.0
        assert stats['sample_size'] == 1
    
    def test_calculate_statistics_empty(self, engine):
        """Test statistical calculations with empty data"""
        values = []
        stats = engine._calculate_statistics(values)
        
        assert stats == {}
    
    def test_calculate_confidence_full_data(self, engine):
        """Test confidence calculation with full data"""
        # 30 days * 5 signals/day = 150 signals
        confidence = engine._calculate_confidence(
            data_points=150,
            unique_days=30,
            target_days=30
        )
        
        assert confidence == pytest.approx(1.0)
    
    def test_calculate_confidence_partial_data(self, engine):
        """Test confidence calculation with partial data"""
        # 20 days * 5 signals/day = 100 signals
        confidence = engine._calculate_confidence(
            data_points=100,
            unique_days=20,
            target_days=30
        )
        
        # Day coverage: 20/30 = 0.67
        # Data density: 100/150 = 0.67
        # Combined: (0.67 * 0.7) + (0.67 * 0.3) = 0.67
        assert confidence == pytest.approx(0.67, abs=0.01)
    
    def test_calculate_confidence_minimum(self, engine):
        """Test confidence calculation enforces minimum"""
        # Very low data
        confidence = engine._calculate_confidence(
            data_points=10,
            unique_days=5,
            target_days=30
        )
        
        # Should be clamped to minimum (0.5)
        assert confidence >= 0.5
    
    def test_calculate_statistics_percentiles(self, engine):
        """Test percentile calculations"""
        # Create data with known percentiles
        values = list(range(1, 101))  # 1 to 100
        stats = engine._calculate_statistics(values)
        
        assert stats['p05'] == pytest.approx(5.95, abs=1.0)
        assert stats['p25'] == pytest.approx(25.75, abs=1.0)
        assert stats['p50'] == pytest.approx(50.5, abs=1.0)
        assert stats['p75'] == pytest.approx(75.25, abs=1.0)
        assert stats['p95'] == pytest.approx(95.05, abs=1.0)
    
    def test_calculate_statistics_std_dev(self, engine):
        """Test standard deviation calculation"""
        # Known std dev
        values = [2, 4, 4, 4, 5, 5, 7, 9]
        stats = engine._calculate_statistics(values)
        
        # Sample std dev should be ~2.0
        assert stats['std_dev'] == pytest.approx(2.0, abs=0.1)
    
    @pytest.mark.parametrize("values,expected_mean", [
        ([1, 2, 3, 4, 5], 3.0),
        ([10, 20, 30], 20.0),
        ([100], 100.0),
        ([5.5, 10.5, 15.5], 10.5),
    ])
    def test_calculate_statistics_mean(self, engine, values, expected_mean):
        """Test mean calculation with various inputs"""
        stats = engine._calculate_statistics(values)
        assert stats['mean'] == pytest.approx(expected_mean)
    
    def test_min_days_requirement(self, engine):
        """Test minimum days requirement"""
        assert engine.min_days == 14
        assert engine.target_days == 30
    
    def test_min_confidence_threshold(self, engine):
        """Test minimum confidence threshold"""
        assert engine.min_confidence == 0.5


class TestMetricExtraction:
    """Test metric extraction logic"""
    
    @pytest.fixture
    def engine(self):
        return BaselineEngine()
    
    def test_extract_metrics_empty(self, engine):
        """Test metric extraction with no signals"""
        metrics = asyncio.run(engine._extract_metrics([]))
        assert metrics == {}
    
    # Note: More integration tests would require database setup
    # These would test the full pipeline with actual signal data


class TestConfidenceScoring:
    """Test confidence scoring edge cases"""
    
    @pytest.fixture
    def engine(self):
        return BaselineEngine()
    
    def test_confidence_never_exceeds_one(self, engine):
        """Test confidence is capped at 1.0"""
        # Excessive data
        confidence = engine._calculate_confidence(
            data_points=10000,
            unique_days=100,
            target_days=30
        )
        assert confidence <= 1.0
    
    def test_confidence_never_below_minimum(self, engine):
        """Test confidence is floored at minimum"""
        # Minimal data
        confidence = engine._calculate_confidence(
            data_points=1,
            unique_days=1,
            target_days=30
        )
        assert confidence >= 0.5


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
