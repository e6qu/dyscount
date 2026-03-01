"""Tests for DeleteTable operation."""

import pytest
from fastapi.testclient import TestClient
from dyscount_api.main import create_app
from dyscount_core.config import Config
import tempfile
import shutil
import os


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def client(temp_data_dir):
    """Create test client with temp data dir"""
    os.environ.pop("DYSCOUNT_STORAGE__DATA_DIRECTORY", None)
    os.environ["DYSCOUNT_STORAGE__DATA_DIRECTORY"] = temp_data_dir
    config = Config()
    app = create_app(config)
    return TestClient(app)


@pytest.fixture
def created_table(client):
    """Create a table and return its name"""
    table_name = "TestTableForDeletion"
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.CreateTable"},
        json={
            "TableName": table_name,
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"}
            ],
            "BillingMode": "PAY_PER_REQUEST"
        }
    )
    assert response.status_code == 200
    return table_name


def test_delete_table_success(client, created_table):
    """Test successful table deletion"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.DeleteTable"},
        json={"TableName": created_table}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["TableDescription"]["TableName"] == created_table
    assert data["TableDescription"]["TableStatus"] == "DELETING"


def test_delete_table_not_found(client):
    """Test deleting table that doesn't exist"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.DeleteTable"},
        json={"TableName": "NonExistentTable"}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "ResourceNotFoundException" in data["__type"]


def test_delete_table_invalid_name(client):
    """Test deleting table with invalid name"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.DeleteTable"},
        json={"TableName": "ab"}  # Too short
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "ValidationException" in data["__type"]


def test_delete_table_twice(client, created_table):
    """Test deleting same table twice"""
    # First deletion
    response1 = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.DeleteTable"},
        json={"TableName": created_table}
    )
    assert response1.status_code == 200
    
    # Second deletion should fail
    response2 = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.DeleteTable"},
        json={"TableName": created_table}
    )
    assert response2.status_code == 400
    assert "ResourceNotFoundException" in response2.json()["__type"]
