"""Tests for CreateTable operation."""

import pytest
from fastapi.testclient import TestClient
from dyscount_api.main import create_app
from dyscount_core.config import Config
import tempfile
import shutil


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def client(temp_data_dir):
    """Create test client with temp data dir"""
    import os
    # Clear any existing env var and set new one
    os.environ.pop("DYSCOUNT_STORAGE__DATA_DIRECTORY", None)
    os.environ["DYSCOUNT_STORAGE__DATA_DIRECTORY"] = temp_data_dir
    
    # Create config with fresh env
    config = Config()
    app = create_app(config)
    return TestClient(app)


def test_create_table_success(client):
    """Test successful table creation"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.CreateTable"},
        json={
            "TableName": "TestTable",
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"}
            ],
            "BillingMode": "PAY_PER_REQUEST"
        }
    )
    
    if response.status_code != 200:
        print(f"Response: {response.status_code}")
        print(f"Body: {response.json()}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["TableDescription"]["TableName"] == "TestTable"
    assert data["TableDescription"]["TableStatus"] == "ACTIVE"
    assert len(data["TableDescription"]["KeySchema"]) == 1
    assert data["TableDescription"]["KeySchema"][0]["AttributeName"] == "pk"
    assert data["TableDescription"]["KeySchema"][0]["KeyType"] == "HASH"


def test_create_table_with_sort_key(client):
    """Test creating table with partition and sort key"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.CreateTable"},
        json={
            "TableName": "TestTable2",
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
    data = response.json()
    assert data["TableDescription"]["TableName"] == "TestTable2"
    assert len(data["TableDescription"]["KeySchema"]) == 2


def test_create_table_already_exists(client):
    """Test creating table that already exists"""
    # Create table first
    client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.CreateTable"},
        json={
            "TableName": "ExistingTable",
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"}
            ]
        }
    )
    
    # Try to create again
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.CreateTable"},
        json={
            "TableName": "ExistingTable",
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"}
            ]
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "TableAlreadyExistsException" in data["__type"]


def test_create_table_invalid_name_too_short(client):
    """Test creating table with name too short"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.CreateTable"},
        json={
            "TableName": "ab",  # Too short
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"}
            ]
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "ValidationException" in data["__type"]


def test_create_table_invalid_name_special_chars(client):
    """Test creating table with invalid special characters"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.CreateTable"},
        json={
            "TableName": "test@table",  # Invalid char
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"}
            ]
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "ValidationException" in data["__type"]


def test_create_table_missing_hash_key(client):
    """Test creating table without HASH key"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.CreateTable"},
        json={
            "TableName": "TestTable",
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "RANGE"}  # Wrong type
            ]
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "ValidationException" in data["__type"]


def test_create_table_missing_attribute_definition(client):
    """Test creating table with missing attribute definition"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.CreateTable"},
        json={
            "TableName": "TestTable",
            "AttributeDefinitions": [
                # Missing definition for 'pk'
                {"AttributeName": "other", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"}
            ]
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "ValidationException" in data["__type"]
