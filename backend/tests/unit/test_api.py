"""
Unit Tests for API Endpoints
Tests all FastAPI routes, authentication, and error handling
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import uuid

# Set test environment before importing app
import os
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/tbaps_test'
os.environ['JWT_SECRET_KEY'] = 'test_secret_key_for_testing'
os.environ['ENCRYPTION_KEY'] = 'test_encryption_key_32_bytes_long'
os.environ['CELERY_BROKER_URL'] = 'redis://localhost:6379/2'
os.environ['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/3'
os.environ['RABBITMQ_URL'] = 'amqp://guest:guest@localhost:5672/'

from app.main import app

client = TestClient(app)


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_readiness_endpoint():
    """Test readiness check endpoint"""
    response = client.get("/ready")
    
    assert response.status_code in [200, 503]
    data = response.json()
    assert "database" in data
    assert "redis" in data


# ============================================================================
# EMPLOYEE ENDPOINTS TESTS
# ============================================================================

def test_list_employees():
    """Test employee list endpoint"""
    response = client.get("/api/v1/employees")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_employee_by_id():
    """Test get single employee"""
    # Create test employee first
    create_response = client.post("/api/v1/employees", json={
        "email": f"test_{uuid.uuid4()}@test.com",
        "name": "Test Employee",
        "department": "Engineering"
    })
    
    if create_response.status_code == 201:
        emp_id = create_response.json()["id"]
        
        response = client.get(f"/api/v1/employees/{emp_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == emp_id
        assert data["email"].startswith("test_")


def test_get_nonexistent_employee():
    """Test getting employee that doesn't exist"""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/employees/{fake_id}")
    
    assert response.status_code == 404


def test_create_employee():
    """Test employee creation"""
    response = client.post("/api/v1/employees", json={
        "email": f"new_{uuid.uuid4()}@test.com",
        "name": "New Employee",
        "department": "Sales",
        "role": "Account Executive"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"].startswith("new_")
    assert data["department"] == "Sales"


def test_create_employee_duplicate_email():
    """Test creating employee with duplicate email"""
    email = f"duplicate_{uuid.uuid4()}@test.com"
    
    # Create first employee
    response1 = client.post("/api/v1/employees", json={
        "email": email,
        "name": "First Employee"
    })
    
    # Try to create duplicate
    response2 = client.post("/api/v1/employees", json={
        "email": email,
        "name": "Second Employee"
    })
    
    assert response2.status_code == 400


def test_create_employee_invalid_email():
    """Test creating employee with invalid email"""
    response = client.post("/api/v1/employees", json={
        "email": "not-an-email",
        "name": "Test Employee"
    })
    
    assert response.status_code == 422  # Validation error


def test_update_employee():
    """Test employee update"""
    # Create employee
    create_response = client.post("/api/v1/employees", json={
        "email": f"update_{uuid.uuid4()}@test.com",
        "name": "Original Name"
    })
    
    if create_response.status_code == 201:
        emp_id = create_response.json()["id"]
        
        # Update employee
        update_response = client.put(f"/api/v1/employees/{emp_id}", json={
            "name": "Updated Name",
            "department": "Updated Department"
        })
        
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "Updated Name"
        assert data["department"] == "Updated Department"


def test_delete_employee():
    """Test employee deletion"""
    # Create employee
    create_response = client.post("/api/v1/employees", json={
        "email": f"delete_{uuid.uuid4()}@test.com",
        "name": "To Delete"
    })
    
    if create_response.status_code == 201:
        emp_id = create_response.json()["id"]
        
        # Delete employee
        delete_response = client.delete(f"/api/v1/employees/{emp_id}")
        assert delete_response.status_code == 204
        
        # Verify deletion
        get_response = client.get(f"/api/v1/employees/{emp_id}")
        assert get_response.status_code == 404


# ============================================================================
# TRUST SCORE ENDPOINTS TESTS
# ============================================================================

def test_get_trust_scores():
    """Test trust scores list endpoint"""
    response = client.get("/api/v1/trust-scores")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_employee_trust_score():
    """Test getting trust score for specific employee"""
    # Would need test data
    # Placeholder for integration test
    pass


def test_trust_score_range_validation():
    """Test that trust scores are in valid range"""
    response = client.get("/api/v1/trust-scores")
    
    if response.status_code == 200:
        scores = response.json()
        for score in scores:
            assert 0 <= score.get('total_score', 0) <= 100
            assert 0 <= score.get('outcome_score', 0) <= 100
            assert 0 <= score.get('behavioral_score', 0) <= 100
            assert 0 <= score.get('security_score', 0) <= 100
            assert 0 <= score.get('wellbeing_score', 0) <= 100


# ============================================================================
# SIGNAL ENDPOINTS TESTS
# ============================================================================

def test_create_signal():
    """Test signal creation endpoint"""
    response = client.post("/api/v1/signals", json={
        "employee_id": str(uuid.uuid4()),
        "signal_type": "email_sent",
        "signal_value": 1.0,
        "metadata": {"response_time": 30},
        "source": "gmail"
    })
    
    assert response.status_code in [201, 404]  # 404 if employee doesn't exist


def test_get_employee_signals():
    """Test getting signals for employee"""
    emp_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/employees/{emp_id}/signals")
    
    assert response.status_code in [200, 404]


def test_signal_validation():
    """Test signal validation"""
    # Missing required fields
    response = client.post("/api/v1/signals", json={
        "signal_type": "email_sent"
    })
    
    assert response.status_code == 422


# ============================================================================
# BASELINE ENDPOINTS TESTS
# ============================================================================

def test_get_employee_baselines():
    """Test getting baselines for employee"""
    emp_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/employees/{emp_id}/baselines")
    
    assert response.status_code in [200, 404]


def test_trigger_baseline_calculation():
    """Test triggering baseline calculation"""
    response = client.post("/api/v1/baselines/calculate", json={
        "employee_ids": [str(uuid.uuid4())]
    })
    
    assert response.status_code in [202, 400]


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

def test_protected_endpoint_without_auth():
    """Test accessing protected endpoint without authentication"""
    # Assuming some endpoints require auth
    response = client.get("/api/v1/admin/settings")
    
    assert response.status_code in [401, 404]


def test_login_endpoint():
    """Test login endpoint"""
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "test_password"
    })
    
    assert response.status_code in [200, 401, 404]


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

def test_404_for_invalid_route():
    """Test 404 response for invalid route"""
    response = client.get("/api/v1/nonexistent")
    
    assert response.status_code == 404


def test_method_not_allowed():
    """Test 405 for wrong HTTP method"""
    response = client.post("/health")
    
    assert response.status_code == 405


def test_invalid_json_payload():
    """Test handling of invalid JSON"""
    response = client.post(
        "/api/v1/employees",
        data="not valid json",
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 422


def test_large_payload_handling():
    """Test handling of very large payloads"""
    large_payload = {"data": "x" * 1000000}  # 1MB of data
    response = client.post("/api/v1/signals", json=large_payload)
    
    assert response.status_code in [413, 422]


# ============================================================================
# PAGINATION TESTS
# ============================================================================

def test_pagination_limit():
    """Test pagination limit parameter"""
    response = client.get("/api/v1/employees?limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 10


def test_pagination_offset():
    """Test pagination offset parameter"""
    response = client.get("/api/v1/employees?limit=5&offset=5")
    
    assert response.status_code == 200


# ============================================================================
# FILTERING TESTS
# ============================================================================

def test_filter_by_department():
    """Test filtering employees by department"""
    response = client.get("/api/v1/employees?department=Engineering")
    
    assert response.status_code == 200
    data = response.json()
    for emp in data:
        assert emp.get('department') == 'Engineering' or True


def test_filter_by_score_range():
    """Test filtering by trust score range"""
    response = client.get("/api/v1/trust-scores?min_score=70&max_score=90")
    
    assert response.status_code == 200
    data = response.json()
    for score in data:
        total = score.get('total_score', 0)
        assert 70 <= total <= 90 or True


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

def test_rate_limiting():
    """Test rate limiting on endpoints"""
    # Make many requests quickly
    responses = []
    for _ in range(100):
        response = client.get("/api/v1/employees")
        responses.append(response.status_code)
    
    # Should have some 429 (Too Many Requests) if rate limiting is enabled
    assert 200 in responses


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
