"""Tests for DescribeTable operation."""

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
    table_name = "TestTableForDescribe"
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.CreateTable"},
        json={
            "TableName": table_name,
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "N"}
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"}
            ],
            "BillingMode": "PAY_PER_REQUEST"
        }
    )
    assert response.status_code == 200
    return table_name


def test_describe_table_success(client, created_table):
    """Test successful table description"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.DescribeTable"},
        json={"TableName": created_table}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["Table"]["TableName"] == created_table
    assert data["Table"]["TableStatus"] == "ACTIVE"
    assert len(data["Table"]["KeySchema"]) == 2
    assert len(data["Table"]["AttributeDefinitions"]) == 2
    assert "CreationDateTime" in data["Table"]


def test_describe_table_not_found(client):
    """Test describing table that doesn't exist"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.DescribeTable"},
        json={"TableName": "NonExistentTable"}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "ResourceNotFoundException" in data["__type"]


def test_describe_table_invalid_name(client):
    """Test describing table with invalid name"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.DescribeTable"},
        json={"TableName": "ab"}  # Too short
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "ValidationException" in data["__type"]


def test_describe_endpoints(client):
    """Test DescribeEndpoints operation"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.DescribeEndpoints"},
        json={}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "Endpoints" in data
    assert len(data["Endpoints"]) == 1
    assert "Address" in data["Endpoints"][0]
    assert "CachePeriodInMinutes" in data["Endpoints"][0]
    assert data["Endpoints"][0]["CachePeriodInMinutes"] == 1440
