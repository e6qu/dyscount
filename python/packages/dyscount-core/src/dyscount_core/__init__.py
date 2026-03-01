"""Dyscount Core - Core library for the Dyscount DynamoDB-compatible API service."""

from .config import Config
from .models import (
    AttributeDefinition,
    AttributeValue,
    BillingMode,
    CreateTableRequest,
    CreateTableResponse,
    DeleteTableRequest,
    DeleteTableResponse,
    DescribeEndpointsRequest,
    DescribeEndpointsResponse,
    DescribeTableRequest,
    DescribeTableResponse,
    KeySchemaElement,
    KeyType,
    ListTablesRequest,
    ListTablesResponse,
    ProvisionedThroughput,
    ScalarAttributeType,
    TableMetadata,
    TableStatus,
    deserialize_dynamodb_json,
    serialize_to_dynamodb_json,
)
from .storage import SQLiteConnectionManager, TableManager

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # Config
    "Config",
    # Models
    "AttributeValue",
    "serialize_to_dynamodb_json",
    "deserialize_dynamodb_json",
    "AttributeDefinition",
    "BillingMode",
    "KeySchemaElement",
    "KeyType",
    "ProvisionedThroughput",
    "ScalarAttributeType",
    "TableMetadata",
    "TableStatus",
    "CreateTableRequest",
    "CreateTableResponse",
    "DeleteTableRequest",
    "DeleteTableResponse",
    "DescribeEndpointsRequest",
    "DescribeEndpointsResponse",
    "DescribeTableRequest",
    "DescribeTableResponse",
    "ListTablesRequest",
    "ListTablesResponse",
    # Storage
    "SQLiteConnectionManager",
    "TableManager",
]
