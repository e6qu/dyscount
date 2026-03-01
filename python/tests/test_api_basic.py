"""Basic API tests for dyscount-api."""

import pytest
from fastapi.testclient import TestClient

from dyscount_api.main import create_app


@pytest.fixture
def client():
    """Create a test client for the API."""
    app = create_app()
    return TestClient(app)


def test_health_check(client):
    """Test that API responds to DescribeEndpoints."""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.DescribeEndpoints"},
        json={}
    )
    assert response.status_code == 200


def test_unknown_operation(client):
    """Test unknown operation returns error."""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.UnknownOp"},
        json={}
    )
    assert response.status_code == 400
    assert "Unknown operation" in response.json()["message"]



