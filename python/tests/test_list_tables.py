"""Tests for ListTables operation."""

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
def create_test_tables(client):
    """Create multiple test tables"""
    table_names = ["AlphaTable", "BetaTable", "GammaTable", "DeltaTable"]
    for name in table_names:
        response = client.post(
            "/",
            headers={"X-Amz-Target": "DynamoDB_20120810.CreateTable"},
            json={
                "TableName": name,
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
    return table_names


def test_list_tables_all(client, create_test_tables):
    """Test listing all tables"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.ListTables"},
        json={}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "TableNames" in data
    assert len(data["TableNames"]) == 4
    # Should be sorted alphabetically
    assert data["TableNames"] == ["AlphaTable", "BetaTable", "DeltaTable", "GammaTable"]
    assert "LastEvaluatedTableName" not in data or data["LastEvaluatedTableName"] is None


def test_list_tables_with_limit(client, create_test_tables):
    """Test listing tables with limit"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.ListTables"},
        json={"Limit": 2}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["TableNames"]) == 2
    assert data["TableNames"] == ["AlphaTable", "BetaTable"]
    assert data["LastEvaluatedTableName"] == "BetaTable"


def test_list_tables_with_pagination(client, create_test_tables):
    """Test listing tables with pagination"""
    # First page
    response1 = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.ListTables"},
        json={"Limit": 2}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1["TableNames"]) == 2
    assert data1["LastEvaluatedTableName"] == "BetaTable"
    
    # Second page
    response2 = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.ListTables"},
        json={
            "ExclusiveStartTableName": data1["LastEvaluatedTableName"],
            "Limit": 2
        }
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["TableNames"]) == 2
    assert data2["TableNames"] == ["DeltaTable", "GammaTable"]
    assert "LastEvaluatedTableName" not in data2 or data2["LastEvaluatedTableName"] is None


def test_list_tables_empty(client):
    """Test listing tables when none exist"""
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.ListTables"},
        json={}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "TableNames" in data
    assert len(data["TableNames"]) == 0
    assert "LastEvaluatedTableName" not in data or data["LastEvaluatedTableName"] is None


def test_list_tables_after_delete(client, create_test_tables):
    """Test listing tables after deleting one"""
    # Delete a table
    client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.DeleteTable"},
        json={"TableName": "BetaTable"}
    )
    
    # List tables
    response = client.post(
        "/",
        headers={"X-Amz-Target": "DynamoDB_20120810.ListTables"},
        json={}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["TableNames"]) == 3
    assert "BetaTable" not in data["TableNames"]
