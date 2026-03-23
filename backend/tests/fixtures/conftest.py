"""
Test Fixtures and Shared Test Data
Provides reusable test data and database setup for all tests
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import uuid
from typing import List, Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Test database URL
TEST_DATABASE_URL = "postgresql://test:test@localhost:5432/tbaps_test"


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine"""
    engine = create_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        echo=False
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create test database session"""
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    
    yield session
    
    session.rollback()
    session.close()


# ============================================================================
# EMPLOYEE FIXTURES
# ============================================================================

@pytest.fixture
def sample_employee():
    """Create sample employee data"""
    return {
        "id": str(uuid.uuid4()),
        "email": f"test_{uuid.uuid4()}@test.com",
        "name": "Test Employee",
        "department": "Engineering",
        "role": "Software Engineer",
        "hire_date": datetime.utcnow() - timedelta(days=365),
        "is_active": True
    }


@pytest.fixture
def sample_employees():
    """Create multiple sample employees"""
    departments = ["Engineering", "Sales", "Marketing", "HR", "Finance"]
    roles = ["Engineer", "Manager", "Director", "Analyst", "Specialist"]
    
    employees = []
    for i in range(10):
        employees.append({
            "id": str(uuid.uuid4()),
            "email": f"employee_{i}@test.com",
            "name": f"Employee {i}",
            "department": departments[i % len(departments)],
            "role": roles[i % len(roles)],
            "hire_date": datetime.utcnow() - timedelta(days=365 - i*30),
            "is_active": True
        })
    
    return employees


# ============================================================================
# SIGNAL FIXTURES
# ============================================================================

@pytest.fixture
def sample_signals():
    """Create sample signal events"""
    employee_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    signals = []
    
    # Email signals
    for i in range(10):
        signals.append({
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "signal_type": "email_sent",
            "signal_value": 1.0,
            "metadata": {
                "response_time_minutes": 30 + i*5,
                "recipients": 2 + i
            },
            "source": "gmail",
            "timestamp": now - timedelta(hours=i),
            "created_at": now,
            "expires_at": now + timedelta(days=90)
        })
    
    # Meeting signals
    for i in range(5):
        signals.append({
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "signal_type": "meeting_attended",
            "signal_value": 1.0,
            "metadata": {
                "duration_minutes": 60,
                "participated": True
            },
            "source": "calendar",
            "timestamp": now - timedelta(days=i),
            "created_at": now,
            "expires_at": now + timedelta(days=90)
        })
    
    # Task signals
    for i in range(8):
        signals.append({
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "signal_type": "task_completed",
            "signal_value": 1.0,
            "metadata": {
                "task_id": f"task_{i}",
                "on_time": i < 6
            },
            "source": "jira",
            "timestamp": now - timedelta(days=i),
            "created_at": now,
            "expires_at": now + timedelta(days=90)
        })
    
    return signals


@pytest.fixture
def signal_factory():
    """Factory for creating custom signals"""
    def create_signal(
        signal_type: str,
        employee_id: str = None,
        metadata: Dict = None,
        timestamp: datetime = None
    ):
        return {
            "id": str(uuid.uuid4()),
            "employee_id": employee_id or str(uuid.uuid4()),
            "signal_type": signal_type,
            "signal_value": 1.0,
            "metadata": metadata or {},
            "source": "test",
            "timestamp": timestamp or datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=90)
        }
    
    return create_signal


# ============================================================================
# BASELINE FIXTURES
# ============================================================================

@pytest.fixture
def sample_baseline():
    """Create sample baseline profile"""
    return {
        "id": str(uuid.uuid4()),
        "employee_id": str(uuid.uuid4()),
        "metric": "meetings_per_day",
        "baseline_value": 3.5,
        "std_dev": 1.2,
        "p05": 1.5,
        "p50": 3.5,
        "p95": 5.5,
        "min_value": 0.0,
        "max_value": 8.0,
        "sample_size": 30,
        "confidence": 0.95,
        "calculated_at": datetime.utcnow(),
        "window_start": datetime.utcnow() - timedelta(days=30),
        "window_end": datetime.utcnow()
    }


# ============================================================================
# TRUST SCORE FIXTURES
# ============================================================================

@pytest.fixture
def sample_trust_score():
    """Create sample trust score"""
    return {
        "id": str(uuid.uuid4()),
        "employee_id": str(uuid.uuid4()),
        "outcome_score": 85.0,
        "behavioral_score": 78.0,
        "security_score": 92.0,
        "wellbeing_score": 75.0,
        "total_score": 82.5,
        "weights": {
            "outcome": 0.35,
            "behavioral": 0.30,
            "security": 0.20,
            "wellbeing": 0.15
        },
        "timestamp": datetime.utcnow(),
        "calculated_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=30)
    }


# ============================================================================
# TIME-BASED FIXTURES
# ============================================================================

@pytest.fixture
def time_ranges():
    """Provide common time ranges for testing"""
    now = datetime.utcnow()
    
    return {
        "today": (now.replace(hour=0, minute=0, second=0), now),
        "yesterday": (
            (now - timedelta(days=1)).replace(hour=0, minute=0, second=0),
            (now - timedelta(days=1)).replace(hour=23, minute=59, second=59)
        ),
        "last_7_days": (now - timedelta(days=7), now),
        "last_30_days": (now - timedelta(days=30), now),
        "last_90_days": (now - timedelta(days=90), now)
    }


# ============================================================================
# MOCK DATA FIXTURES
# ============================================================================

@pytest.fixture
def mock_calendar_events():
    """Mock calendar events for testing"""
    now = datetime.utcnow()
    
    events = []
    for i in range(10):
        events.append({
            "id": f"event_{i}",
            "summary": f"Meeting {i}",
            "start": (now + timedelta(hours=i)).isoformat(),
            "end": (now + timedelta(hours=i, minutes=60)).isoformat(),
            "attendees": [
                {"email": "attendee1@test.com"},
                {"email": "attendee2@test.com"}
            ],
            "status": "confirmed"
        })
    
    return events


@pytest.fixture
def mock_email_messages():
    """Mock email messages for testing"""
    now = datetime.utcnow()
    
    messages = []
    for i in range(20):
        messages.append({
            "id": f"msg_{i}",
            "subject": f"Test Email {i}",
            "from": "sender@test.com",
            "to": ["recipient@test.com"],
            "date": (now - timedelta(hours=i)).isoformat(),
            "thread_id": f"thread_{i // 3}",
            "labels": ["INBOX", "UNREAD"] if i < 5 else ["INBOX"]
        })
    
    return messages


@pytest.fixture
def mock_jira_issues():
    """Mock JIRA issues for testing"""
    now = datetime.utcnow()
    
    issues = []
    statuses = ["To Do", "In Progress", "Done"]
    
    for i in range(15):
        issues.append({
            "id": f"TASK-{i+1}",
            "summary": f"Test Task {i+1}",
            "status": statuses[i % 3],
            "assignee": "test@test.com",
            "created": (now - timedelta(days=i)).isoformat(),
            "updated": (now - timedelta(hours=i)).isoformat(),
            "priority": "Medium",
            "type": "Task"
        })
    
    return issues


# ============================================================================
# ASYNC FIXTURES
# ============================================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_data(test_db_session):
    """Automatically cleanup test data after each test"""
    yield
    
    # Cleanup logic here
    # Delete test employees, signals, etc.
    pass


# ============================================================================
# CONFIGURATION FIXTURES
# ============================================================================

@pytest.fixture
def test_config():
    """Provide test configuration"""
    return {
        "database_url": TEST_DATABASE_URL,
        "jwt_secret": "test_secret_key",
        "encryption_key": "test_encryption_key_32_bytes_long",
        "redis_url": "redis://localhost:6379/15",  # Use DB 15 for tests
        "celery_broker": "redis://localhost:6379/14",
        "window_days": 30,
        "min_confidence": 0.7,
        "min_sample_size": 10
    }
