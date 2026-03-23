"""
3-Tier Anomaly Detection System
Combines statistical, rule-based, and ML detection with voting mechanism
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
import numpy as np

# ML imports
try:
    from sklearn.ensemble import IsolationForest
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("scikit-learn not available. ML detection disabled.")


# ============================================================================
# DATA CLASSES
# ============================================================================

class AnomalyTier(Enum):
    """Anomaly detection tiers"""
    STATISTICAL = "statistical"
    RULE_BASED = "rule_based"
    MACHINE_LEARNING = "machine_learning"


class AnomalySeverity(Enum):
    """Anomaly severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AnomalyResult:
    """Result from anomaly detection"""
    is_anomaly: bool
    tier: AnomalyTier
    confidence: float  # 0.0 to 1.0
    details: Dict[str, Any]
    severity: AnomalySeverity
    detected_at: datetime


@dataclass
class CombinedAnomalyResult:
    """Combined result from all tiers"""
    is_anomaly: bool
    votes: int  # Number of tiers that detected anomaly
    tier_results: Dict[AnomalyTier, AnomalyResult]
    confidence: float
    severity: AnomalySeverity
    anomaly_types: List[str]
    detected_at: datetime


# ============================================================================
# TIER 1: STATISTICAL ANOMALY DETECTION
# ============================================================================

class StatisticalAnomalyDetector:
    """
    Tier 1: Statistical Anomaly Detection
    
    Uses Z-score (standard deviations from mean) to detect anomalies.
    Based on the 3-sigma rule: values >3 standard deviations are anomalies.
    """
    
    # Thresholds
    Z_SCORE_THRESHOLD = 3.0  # 3-sigma rule (99.7% of data)
    MIN_SAMPLES = 10  # Minimum samples needed for reliable statistics
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def detect(
        self,
        value: float,
        baseline_mean: float,
        baseline_std: float,
        metric_name: str = "unknown"
    ) -> AnomalyResult:
        """
        Detect statistical anomaly using Z-score
        
        Args:
            value: Current value to check
            baseline_mean: Baseline mean
            baseline_std: Baseline standard deviation
            metric_name: Name of metric being checked
        
        Returns:
            AnomalyResult with detection details
        """
        # Handle edge case: no variance in baseline
        if baseline_std == 0:
            return AnomalyResult(
                is_anomaly=False,
                tier=AnomalyTier.STATISTICAL,
                confidence=0.0,
                details={
                    'reason': 'No variance in baseline',
                    'metric': metric_name,
                    'value': value,
                    'baseline_mean': baseline_mean
                },
                severity=AnomalySeverity.LOW,
                detected_at=datetime.utcnow()
            )
        
        # Calculate Z-score
        z_score = abs((value - baseline_mean) / baseline_std)
        
        # Determine if anomaly
        is_anomaly = z_score > self.Z_SCORE_THRESHOLD
        
        # Calculate confidence based on how far beyond threshold
        if is_anomaly:
            # Confidence increases with Z-score
            # 3-sigma = 0.5, 4-sigma = 0.7, 5-sigma = 0.85, 6+ = 0.95
            confidence = min(0.95, 0.5 + (z_score - 3) * 0.15)
        else:
            # Confidence decreases as we approach threshold
            confidence = max(0.0, (self.Z_SCORE_THRESHOLD - z_score) / self.Z_SCORE_THRESHOLD)
        
        # Determine severity based on Z-score
        if z_score > 6:
            severity = AnomalySeverity.CRITICAL
        elif z_score > 5:
            severity = AnomalySeverity.HIGH
        elif z_score > 4:
            severity = AnomalySeverity.MEDIUM
        else:
            severity = AnomalySeverity.LOW
        
        return AnomalyResult(
            is_anomaly=is_anomaly,
            tier=AnomalyTier.STATISTICAL,
            confidence=confidence,
            details={
                'z_score': round(z_score, 2),
                'threshold': self.Z_SCORE_THRESHOLD,
                'metric': metric_name,
                'value': value,
                'baseline_mean': baseline_mean,
                'baseline_std': baseline_std,
                'deviation': round(value - baseline_mean, 2)
            },
            severity=severity,
            detected_at=datetime.utcnow()
        )
    
    def detect_multiple(
        self,
        values: Dict[str, float],
        baselines: Dict[str, Dict[str, float]]
    ) -> List[AnomalyResult]:
        """
        Detect anomalies across multiple metrics
        
        Args:
            values: Dictionary of metric_name -> value
            baselines: Dictionary of metric_name -> {mean, std}
        
        Returns:
            List of AnomalyResults
        """
        results = []
        
        for metric_name, value in values.items():
            if metric_name in baselines:
                baseline = baselines[metric_name]
                result = self.detect(
                    value,
                    baseline['mean'],
                    baseline['std'],
                    metric_name
                )
                results.append(result)
        
        return results


# ============================================================================
# TIER 2: RULE-BASED ANOMALY DETECTION
# ============================================================================

class RuleBasedAnomalyDetector:
    """
    Tier 2: Rule-Based Anomaly Detection
    
    Uses security and business rules to detect anomalies.
    Focuses on security violations and policy breaches.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rules = self._initialize_rules()
    
    def _initialize_rules(self) -> List[Dict[str, Any]]:
        """Initialize detection rules"""
        return [
            {
                'name': 'sensitive_access_without_vpn',
                'check': lambda s: s.get('vpn_connected') is False and s.get('accessing_sensitive_data') is True,
                'severity': AnomalySeverity.CRITICAL,
                'description': 'Accessing sensitive data without VPN connection'
            },
            {
                'name': 'multiple_failed_mfa',
                'check': lambda s: s.get('failed_mfa_attempts', 0) > 5,
                'severity': AnomalySeverity.HIGH,
                'description': 'Multiple failed MFA authentication attempts'
            },
            {
                'name': 'off_hours_data_transfer',
                'check': lambda s: s.get('off_hours') is True and s.get('large_data_download') is True,
                'severity': AnomalySeverity.HIGH,
                'description': 'Large data transfer outside business hours'
            },
            {
                'name': 'unusual_location_sensitive_access',
                'check': lambda s: s.get('unusual_location') is True and s.get('accessing_sensitive_data') is True,
                'severity': AnomalySeverity.CRITICAL,
                'description': 'Accessing sensitive data from unusual location'
            },
            {
                'name': 'excessive_failed_logins',
                'check': lambda s: s.get('failed_login_attempts', 0) > 10,
                'severity': AnomalySeverity.HIGH,
                'description': 'Excessive failed login attempts'
            },
            {
                'name': 'unusual_working_hours',
                'check': lambda s: s.get('working_hours_anomaly') is True,
                'severity': AnomalySeverity.MEDIUM,
                'description': 'Working at unusual hours consistently'
            },
            {
                'name': 'rapid_location_change',
                'check': lambda s: s.get('impossible_travel') is True,
                'severity': AnomalySeverity.CRITICAL,
                'description': 'Impossible travel detected (rapid location change)'
            },
            {
                'name': 'excessive_permissions_usage',
                'check': lambda s: s.get('admin_actions', 0) > s.get('admin_baseline', 10) * 3,
                'severity': AnomalySeverity.HIGH,
                'description': 'Excessive use of administrative permissions'
            },
            {
                'name': 'data_exfiltration_pattern',
                'check': lambda s: (
                    s.get('large_data_download') is True and
                    s.get('external_destination') is True and
                    s.get('off_hours') is True
                ),
                'severity': AnomalySeverity.CRITICAL,
                'description': 'Potential data exfiltration pattern detected'
            },
            {
                'name': 'security_tool_disabled',
                'check': lambda s: s.get('security_software_disabled') is True,
                'severity': AnomalySeverity.CRITICAL,
                'description': 'Security software or monitoring disabled'
            }
        ]
    
    def detect(self, signals: Dict[str, Any]) -> AnomalyResult:
        """
        Detect rule-based anomalies
        
        Args:
            signals: Dictionary of signal values
        
        Returns:
            AnomalyResult with triggered rules
        """
        triggered_rules = []
        max_severity = AnomalySeverity.LOW
        
        # Check each rule
        for rule in self.rules:
            try:
                if rule['check'](signals):
                    triggered_rules.append({
                        'name': rule['name'],
                        'description': rule['description'],
                        'severity': rule['severity'].value
                    })
                    
                    # Track highest severity
                    if self._severity_value(rule['severity']) > self._severity_value(max_severity):
                        max_severity = rule['severity']
                        
            except Exception as e:
                self.logger.error(f"Error checking rule {rule['name']}: {e}")
        
        # Determine if anomaly
        is_anomaly = len(triggered_rules) > 0
        
        # Calculate confidence based on number and severity of triggered rules
        if is_anomaly:
            # More rules = higher confidence
            # Critical rules = higher confidence
            base_confidence = min(0.9, 0.5 + len(triggered_rules) * 0.1)
            severity_boost = self._severity_value(max_severity) * 0.1
            confidence = min(0.95, base_confidence + severity_boost)
        else:
            confidence = 0.0
        
        return AnomalyResult(
            is_anomaly=is_anomaly,
            tier=AnomalyTier.RULE_BASED,
            confidence=confidence,
            details={
                'triggered_rules': triggered_rules,
                'rule_count': len(triggered_rules),
                'signals_checked': list(signals.keys())
            },
            severity=max_severity,
            detected_at=datetime.utcnow()
        )
    
    def _severity_value(self, severity: AnomalySeverity) -> int:
        """Convert severity to numeric value"""
        severity_map = {
            AnomalySeverity.LOW: 1,
            AnomalySeverity.MEDIUM: 2,
            AnomalySeverity.HIGH: 3,
            AnomalySeverity.CRITICAL: 4
        }
        return severity_map.get(severity, 0)


# ============================================================================
# TIER 3: MACHINE LEARNING ANOMALY DETECTION
# ============================================================================

class MLAnomalyDetector:
    """
    Tier 3: Machine Learning Anomaly Detection
    
    Uses Isolation Forest algorithm to detect anomalies.
    Learns normal behavior patterns from historical data.
    """
    
    # Model parameters
    CONTAMINATION = 0.1  # Expected proportion of anomalies (10%)
    N_ESTIMATORS = 100
    MAX_SAMPLES = 256
    RANDOM_STATE = 42
    
    def __init__(self, model_path: str = '/models/anomaly_forest.pkl'):
        """
        Initialize ML Anomaly Detector
        
        Args:
            model_path: Path to saved model
        """
        self.logger = logging.getLogger(__name__)
        self.model_path = model_path
        self.model = None
        self.feature_names = []
        
        if ML_AVAILABLE:
            self.load_or_initialize()
        else:
            self.logger.warning("ML detection disabled - scikit-learn not available")
    
    def load_or_initialize(self):
        """Load pre-trained model or initialize new one"""
        try:
            import os
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                self.logger.info(f"Loaded model from {self.model_path}")
            else:
                self.initialize_model()
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            self.initialize_model()
    
    def initialize_model(self):
        """Initialize new Isolation Forest model"""
        if not ML_AVAILABLE:
            return
        
        self.model = IsolationForest(
            contamination=self.CONTAMINATION,
            n_estimators=self.N_ESTIMATORS,
            max_samples=self.MAX_SAMPLES,
            random_state=self.RANDOM_STATE,
            n_jobs=-1  # Use all CPU cores
        )
        self.logger.info("Initialized new Isolation Forest model")
    
    def train(self, training_data: np.ndarray, feature_names: List[str]):
        """
        Train the model on normal behavior data
        
        Args:
            training_data: NumPy array of shape (n_samples, n_features)
            feature_names: List of feature names
        """
        if not ML_AVAILABLE or self.model is None:
            self.logger.warning("Cannot train - ML not available")
            return
        
        try:
            self.feature_names = feature_names
            self.model.fit(training_data)
            
            # Save model
            import os
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.model, self.model_path)
            
            self.logger.info(f"Model trained on {len(training_data)} samples")
            
        except Exception as e:
            self.logger.error(f"Error training model: {e}")
    
    def detect(self, features: np.ndarray) -> AnomalyResult:
        """
        Detect anomaly using ML model
        
        Args:
            features: Feature vector (1D array)
        
        Returns:
            AnomalyResult with ML detection details
        """
        if not ML_AVAILABLE or self.model is None:
            return AnomalyResult(
                is_anomaly=False,
                tier=AnomalyTier.MACHINE_LEARNING,
                confidence=0.0,
                details={'error': 'ML not available'},
                severity=AnomalySeverity.LOW,
                detected_at=datetime.utcnow()
            )
        
        try:
            # Reshape if needed
            if features.ndim == 1:
                features = features.reshape(1, -1)
            
            # Predict: -1 = anomaly, 1 = normal
            prediction = self.model.predict(features)[0]
            
            # Get anomaly score (more negative = more anomalous)
            score = self.model.score_samples(features)[0]
            
            is_anomaly = (prediction == -1)
            
            # Convert score to confidence (0 to 1)
            # Scores typically range from -0.5 to 0.5
            # More negative = higher confidence it's an anomaly
            if is_anomaly:
                confidence = min(0.95, max(0.5, abs(score) * 2))
            else:
                confidence = min(0.95, max(0.0, (0.5 + score) * 2))
            
            # Determine severity based on score
            if abs(score) > 0.4:
                severity = AnomalySeverity.HIGH
            elif abs(score) > 0.3:
                severity = AnomalySeverity.MEDIUM
            else:
                severity = AnomalySeverity.LOW
            
            return AnomalyResult(
                is_anomaly=is_anomaly,
                tier=AnomalyTier.MACHINE_LEARNING,
                confidence=confidence,
                details={
                    'prediction': int(prediction),
                    'anomaly_score': round(float(score), 4),
                    'feature_count': len(features[0]),
                    'model_type': 'IsolationForest'
                },
                severity=severity,
                detected_at=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Error in ML detection: {e}")
            return AnomalyResult(
                is_anomaly=False,
                tier=AnomalyTier.MACHINE_LEARNING,
                confidence=0.0,
                details={'error': str(e)},
                severity=AnomalySeverity.LOW,
                detected_at=datetime.utcnow()
            )


# ============================================================================
# COMBINED ANOMALY DETECTION SYSTEM
# ============================================================================

class CombinedAnomalyDetector:
    """
    Combined 3-Tier Anomaly Detection System
    
    Uses voting mechanism: 2 out of 3 tiers must agree for anomaly detection.
    Combines statistical, rule-based, and ML detection.
    """
    
    VOTING_THRESHOLD = 2  # Number of tiers needed to confirm anomaly
    
    def __init__(self, ml_model_path: str = '/models/anomaly_forest.pkl'):
        """
        Initialize combined detector
        
        Args:
            ml_model_path: Path to ML model
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize all three tiers
        self.statistical_detector = StatisticalAnomalyDetector()
        self.rule_detector = RuleBasedAnomalyDetector()
        self.ml_detector = MLAnomalyDetector(ml_model_path)
    
    def detect(
        self,
        employee_id: str,
        signals: Dict[str, Any],
        baseline: Optional[Dict[str, Any]] = None,
        ml_features: Optional[np.ndarray] = None
    ) -> CombinedAnomalyResult:
        """
        Detect anomalies using all three tiers with voting
        
        Args:
            employee_id: Employee identifier
            signals: Dictionary of signal values
            baseline: Baseline statistics for statistical detection
            ml_features: Feature vector for ML detection
        
        Returns:
            CombinedAnomalyResult with voting results
        """
        tier_results = {}
        
        # Tier 1: Statistical Detection
        if baseline and 'value' in signals:
            stat_result = self.statistical_detector.detect(
                signals['value'],
                baseline.get('mean', 0),
                baseline.get('std', 1),
                signals.get('metric_name', 'unknown')
            )
            tier_results[AnomalyTier.STATISTICAL] = stat_result
        
        # Tier 2: Rule-Based Detection
        rule_result = self.rule_detector.detect(signals)
        tier_results[AnomalyTier.RULE_BASED] = rule_result
        
        # Tier 3: ML Detection
        if ml_features is not None:
            ml_result = self.ml_detector.detect(ml_features)
            tier_results[AnomalyTier.MACHINE_LEARNING] = ml_result
        
        # Count votes
        votes = sum(1 for result in tier_results.values() if result.is_anomaly)
        
        # Determine final anomaly status (2 of 3 = anomaly)
        is_anomaly = votes >= self.VOTING_THRESHOLD
        
        # Calculate combined confidence (average of detecting tiers)
        detecting_tiers = [r for r in tier_results.values() if r.is_anomaly]
        if detecting_tiers:
            confidence = sum(r.confidence for r in detecting_tiers) / len(detecting_tiers)
        else:
            confidence = 0.0
        
        # Determine overall severity (highest from detecting tiers)
        if detecting_tiers:
            severity_values = {
                AnomalySeverity.LOW: 1,
                AnomalySeverity.MEDIUM: 2,
                AnomalySeverity.HIGH: 3,
                AnomalySeverity.CRITICAL: 4
            }
            max_severity = max(detecting_tiers, key=lambda r: severity_values[r.severity]).severity
        else:
            max_severity = AnomalySeverity.LOW
        
        # Collect anomaly types
        anomaly_types = []
        for tier, result in tier_results.items():
            if result.is_anomaly:
                if tier == AnomalyTier.RULE_BASED:
                    # Add specific rule names
                    for rule in result.details.get('triggered_rules', []):
                        anomaly_types.append(rule['name'])
                else:
                    anomaly_types.append(tier.value)
        
        return CombinedAnomalyResult(
            is_anomaly=is_anomaly,
            votes=votes,
            tier_results=tier_results,
            confidence=confidence,
            severity=max_severity,
            anomaly_types=anomaly_types,
            detected_at=datetime.utcnow()
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_ml_features(signals: Dict[str, Any]) -> np.ndarray:
    """
    Extract feature vector for ML detection
    
    Args:
        signals: Dictionary of signal values
    
    Returns:
        NumPy array of features
    """
    features = [
        signals.get('login_count', 0),
        signals.get('failed_login_attempts', 0),
        signals.get('data_download_mb', 0),
        signals.get('admin_actions', 0),
        signals.get('sensitive_access_count', 0),
        signals.get('working_hours', 8),
        signals.get('location_changes', 0),
        int(signals.get('vpn_connected', True)),
        int(signals.get('off_hours', False)),
        int(signals.get('unusual_location', False))
    ]
    
    return np.array(features, dtype=float)


def is_off_hours(timestamp: datetime) -> bool:
    """Check if timestamp is outside business hours"""
    # Business hours: 9 AM - 5 PM, Monday-Friday
    if timestamp.weekday() >= 5:  # Weekend
        return True
    
    if timestamp.time() < time(9, 0) or timestamp.time() >= time(17, 0):
        return True
    
    return False
