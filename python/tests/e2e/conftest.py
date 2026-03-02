"""Pytest configuration and fixtures for E2E tests."""

import uuid
from typing import Generator

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import ClientError


@pytest.fixture(scope="session")
def dynamodb_client() -> Generator:
    """Create a boto3 DynamoDB client pointing to local dyscount server.
    
    Yields:
        boto3 DynamoDB client configured for local testing
    """
    client = boto3.client(
        "dynamodb",
        endpoint_url="http://localhost:8000",
        region_name="eu-west-1",
        aws_access_key_id="dummy",
        aws_secret_access_key="dummy",
        config=Config(
            retries={"max_attempts": 0},
            connect_timeout=5,
            read_timeout=5,
        ),
    )
    yield client


@pytest.fixture
def unique_table_name() -> str:
    """Generate a unique table name for test isolation.
    
    Returns:
        Unique table name with test prefix
    """
    return f"test_table_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_table(dynamodb_client, unique_table_name: str) -> Generator[str, None, None]:
    """Create a test table and yield its name, cleaning up after test.
    
    Args:
        dynamodb_client: boto3 DynamoDB client
        unique_table_name: Unique name for the table
        
    Yields:
        Name of the created test table
    """
    table_name = unique_table_name
    
    # Create table with simple primary key
    try:
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
    except ClientError as e:
        pytest.fail(f"Failed to create test table: {e}")
    
    yield table_name
    
    # Cleanup: delete table
    try:
        dynamodb_client.delete_table(TableName=table_name)
    except ClientError:
        pass  # Table may already be deleted


@pytest.fixture
def test_table_with_sort_key(dynamodb_client, unique_table_name: str) -> Generator[str, None, None]:
    """Create a test table with composite key and yield its name.
    
    Args:
        dynamodb_client: boto3 DynamoDB client
        unique_table_name: Unique name for the table
        
    Yields:
        Name of the created test table with sort key
    """
    table_name = f"{unique_table_name}_sk"
    
    try:
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
    except ClientError as e:
        pytest.fail(f"Failed to create test table: {e}")
    
    yield table_name
    
    # Cleanup
    try:
        dynamodb_client.delete_table(TableName=table_name)
    except ClientError:
        pass


@pytest.fixture
def sample_item() -> dict:
    """Return a sample item for testing.
    
    Returns:
        Sample DynamoDB item with various attribute types
    """
    return {
        "pk": {"S": "user#123"},
        "name": {"S": "John Doe"},
        "age": {"N": "30"},
        "active": {"BOOL": True},
        "tags": {"SS": ["tag1", "tag2"]},
        "metadata": {"M": {"key1": {"S": "value1"}}},
    }
