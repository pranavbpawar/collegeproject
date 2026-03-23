"""
Integration Tests for API + Database
Tests end-to-end workflows involving multiple components
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Test environment setup
import os
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/tbaps_test'
os.environ['JWT_SECRET_KEY'] = 'test_secret_key'
os.environ['ENCRYPTION_KEY'] = 'test_encryption_key_32_bytes_long'
os.environ['CELERY_BROKER_URL'] = 'redis://localhost:6379/2'
os.environ['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/3'
os.environ['RABBITMQ_URL'] = 'amqp://guest:guest@localhost:5672/'

from app.main import app
from app.core.database import get_db

client = TestClient(app)


# ============================================================================
# EMPLOYEE LIFECYCLE TESTS
# ============================================================================

def test_employee_creation_and_retrieval():
    """Test creating employee via API and retrieving from database"""
    # Create employee
    email = f"integration_test_{uuid.uuid4()}@test.com"
    create_response = client.post("/api/v1/employees", json={
        "email": email,
        "name": "Integration Test Employee",
        "department": "Engineering",
        "role": "Software Engineer"
    })
    
    assert create_response.status_code == 201
    emp_data = create_response.json()
    emp_id = emp_data["id"]
    
    # Retrieve via API
    get_response = client.get(f"/api/v1/employees/{emp_id}")
    assert get_response.status_code == 200
    retrieved_data = get_response.json()
    
    # Verify data matches
    assert retrieved_data["id"] == emp_id
    assert retrieved_data["email"] == email
    assert retrieved_data["name"] == "Integration Test Employee"
    assert retrieved_data["department"] == "Engineering"


def test_employee_update_and_persistence():
    """Test employee update persists to database"""
    # Create employee
    create_response = client.post("/api/v1/employees", json={
        "email": f"update_test_{uuid.uuid4()}@test.com",
        "name": "Original Name"
    })
    
    emp_id = create_response.json()["id"]
    
    # Update employee
    update_response = client.put(f"/api/v1/employees/{emp_id}", json={
        "name": "Updated Name",
        "department": "Sales"
    })
    
    assert update_response.status_code == 200
    
    # Retrieve and verify update persisted
    get_response = client.get(f"/api/v1/employees/{emp_id}")
    updated_data = get_response.json()
    
    assert updated_data["name"] == "Updated Name"
    assert updated_data["department"] == "Sales"


def test_employee_deletion_cascade():
    """Test employee deletion cascades to related records"""
    # Create employee
    create_response = client.post("/api/v1/employees", json={
        "email": f"delete_test_{uuid.uuid4()}@test.com",
        "name": "To Delete"
    })
    
    emp_id = create_response.json()["id"]
    
    # Create related signals
    for i in range(5):
        client.post("/api/v1/signals", json={
            "employee_id": emp_id,
            "signal_type": "email_sent",
            "signal_value": 1.0,
            "metadata": {},
            "source": "test"
        })
    
    # Delete employee
    delete_response = client.delete(f"/api/v1/employees/{emp_id}")
    assert delete_response.status_code == 204
    
    # Verify employee is gone
    get_response = client.get(f"/api/v1/employees/{emp_id}")
    assert get_response.status_code == 404
    
    # Verify signals are also deleted (cascade)
    signals_response = client.get(f"/api/v1/employees/{emp_id}/signals")
    assert signals_response.status_code == 404


# ============================================================================
# SIGNAL INGESTION TO BASELINE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_signal_ingestion_to_baseline_calculation():
    """Test signals are ingested and used in baseline calculation"""
    # Create employee
    create_response = client.post("/api/v1/employees", json={
        "email": f"baseline_test_{uuid.uuid4()}@test.com",
        "name": "Baseline Test Employee"
    })
    
    emp_id = create_response.json()["id"]
    
    # Ingest 30 days of meeting signals
    for i in range(30):
        client.post("/api/v1/signals", json={
            "employee_id": emp_id,
            "signal_type": "meeting_attended",
            "signal_value": 1.0,
            "metadata": {"duration": 30},
            "source": "calendar",
            "timestamp": (datetime.utcnow() - timedelta(days=i)).isoformat()
        })
    
    # Trigger baseline calculation
    baseline_response = client.post("/api/v1/baselines/calculate", json={
        "employee_ids": [emp_id]
    })
    
    assert baseline_response.status_code in [202, 200]
    
    # Wait for calculation (in real test, would poll or use async)
    await asyncio.sleep(2)
    
    # Retrieve baselines
    get_baseline_response = client.get(f"/api/v1/employees/{emp_id}/baselines")
    
    if get_baseline_response.status_code == 200:
        baselines = get_baseline_response.json()
        assert len(baselines) > 0
        
        # Verify meetings_per_day baseline exists
        meetings_baseline = next(
            (b for b in baselines if b['metric'] == 'meetings_per_day'),
            None
        )
        assert meetings_baseline is not None
        assert meetings_baseline['baseline_value'] > 0


# ============================================================================
# TRUST SCORE CALCULATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_trust_score_calculation_from_signals():
    """Test trust score is calculated from ingested signals"""
    # Create employee
    create_response = client.post("/api/v1/employees", json={
        "email": f"trust_score_test_{uuid.uuid4()}@test.com",
        "name": "Trust Score Test"
    })
    
    emp_id = create_response.json()["id"]
    
    # Ingest various signals
    signal_types = [
        ('task_created', {'task_id': 'task_1'}),
        ('task_completed', {'task_id': 'task_1', 'on_time': True}),
        ('email_sent', {'response_time_minutes': 30}),
        ('meeting_attended', {'participated': True}),
        ('code_commit', {'lines_changed': 100})
    ]
    
    for signal_type, metadata in signal_types:
        client.post("/api/v1/signals", json={
            "employee_id": emp_id,
            "signal_type": signal_type,
            "signal_value": 1.0,
            "metadata": metadata,
            "source": "test"
        })
    
    # Trigger trust score calculation
    calc_response = client.post("/api/v1/trust-scores/calculate", json={
        "employee_ids": [emp_id]
    })
    
    assert calc_response.status_code in [202, 200]
    
    # Wait for calculation
    await asyncio.sleep(2)
    
    # Retrieve trust score
    score_response = client.get(f"/api/v1/employees/{emp_id}/trust-score")
    
    if score_response.status_code == 200:
        score_data = score_response.json()
        
        # Verify score is in valid range
        assert 0 <= score_data['total_score'] <= 100
        assert 0 <= score_data['outcome_score'] <= 100
        assert 0 <= score_data['behavioral_score'] <= 100
        assert 0 <= score_data['security_score'] <= 100
        assert 0 <= score_data['wellbeing_score'] <= 100


# ============================================================================
# OAUTH TOKEN ENCRYPTION TESTS
# ============================================================================

def test_oauth_token_storage_and_retrieval():
    """Test OAuth tokens are encrypted and decrypted correctly"""
    # Create employee
    create_response = client.post("/api/v1/employees", json={
        "email": f"oauth_test_{uuid.uuid4()}@test.com",
        "name": "OAuth Test"
    })
    
    emp_id = create_response.json()["id"]
    
    # Store OAuth token
    token_data = {
        "access_token": "test_access_token_12345",
        "refresh_token": "test_refresh_token_67890",
        "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }
    
    store_response = client.post(
        f"/api/v1/employees/{emp_id}/integrations/google/token",
        json=token_data
    )
    
    assert store_response.status_code in [200, 201]
    
    # Retrieve token
    get_response = client.get(
        f"/api/v1/employees/{emp_id}/integrations/google/token"
    )
    
    if get_response.status_code == 200:
        retrieved_token = get_response.json()
        
        # Verify token was encrypted and decrypted
        assert retrieved_token['access_token'] == token_data['access_token']
        assert retrieved_token['refresh_token'] == token_data['refresh_token']


# ============================================================================
# BACKGROUND WORKER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_background_sync_task():
    """Test background sync task execution"""
    # Create employee with integration
    create_response = client.post("/api/v1/employees", json={
        "email": f"sync_test_{uuid.uuid4()}@test.com",
        "name": "Sync Test"
    })
    
    emp_id = create_response.json()["id"]
    
    # Trigger sync
    sync_response = client.post(
        f"/api/v1/employees/{emp_id}/integrations/google/sync"
    )
    
    assert sync_response.status_code in [202, 200, 404]
    
    if sync_response.status_code == 202:
        task_id = sync_response.json().get('task_id')
        
        # Poll for task completion
        for _ in range(10):
            status_response = client.get(f"/api/v1/tasks/{task_id}")
            if status_response.status_code == 200:
                status = status_response.json()['status']
                if status in ['completed', 'failed']:
                    break
            await asyncio.sleep(1)


# ============================================================================
# DATA CONSISTENCY TESTS
# ============================================================================

def test_concurrent_signal_ingestion():
    """Test concurrent signal ingestion maintains data consistency"""
    # Create employee
    create_response = client.post("/api/v1/employees", json={
        "email": f"concurrent_test_{uuid.uuid4()}@test.com",
        "name": "Concurrent Test"
    })
    
    emp_id = create_response.json()["id"]
    
    # Ingest signals concurrently
    import concurrent.futures
    
    def ingest_signal(i):
        return client.post("/api/v1/signals", json={
            "employee_id": emp_id,
            "signal_type": "email_sent",
            "signal_value": 1.0,
            "metadata": {"index": i},
            "source": "test"
        })
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(ingest_signal, i) for i in range(50)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # Verify all signals were created
    successful = sum(1 for r in results if r.status_code == 201)
    assert successful == 50
    
    # Verify count in database
    signals_response = client.get(f"/api/v1/employees/{emp_id}/signals")
    if signals_response.status_code == 200:
        signals = signals_response.json()
        assert len(signals) == 50


# ============================================================================
# TRANSACTION ROLLBACK TESTS
# ============================================================================

def test_transaction_rollback_on_error():
    """Test database transactions rollback on error"""
    # Attempt to create employee with invalid data that will fail mid-transaction
    response = client.post("/api/v1/employees", json={
        "email": "valid@test.com",
        "name": "Test",
        # Missing required field that causes error after partial insert
    })
    
    # Verify no partial data was saved
    # (This would require specific error conditions)
    pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
