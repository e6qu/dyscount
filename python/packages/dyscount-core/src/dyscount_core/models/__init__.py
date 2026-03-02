"""DynamoDB models for dyscount-core."""

from .attribute_value import AttributeValue, deserialize_dynamodb_json, serialize_to_dynamodb_json
from .errors import (
    DynamoDBException,
    ResourceNotFoundException,
    TableAlreadyExistsException,
    ValidationException,
)
from .operations import (
    CreateTableRequest,
    CreateTableResponse,
    DeleteTableRequest,
    DeleteTableResponse,
    DescribeEndpointsRequest,
    DescribeEndpointsResponse,
    DescribeTableRequest,
    DescribeTableResponse,
    ListTablesRequest,
    ListTablesResponse,
    QueryRequest,
    QueryResponse,
    ScanRequest,
    ScanResponse,
)
from .table import (
    AttributeDefinition,
    BillingMode,
    KeySchemaElement,
    KeyType,
    ProvisionedThroughput,
    ScalarAttributeType,
    TableMetadata,
    TableStatus,
)

__all__ = [
    # Attribute Value
    "AttributeValue",
    "serialize_to_dynamodb_json",
    "deserialize_dynamodb_json",
    # Errors
    "DynamoDBException",
    "ResourceNotFoundException",
    "TableAlreadyExistsException",
    "ValidationException",
    # Table Models
    "AttributeDefinition",
    "BillingMode",
    "KeySchemaElement",
    "KeyType",
    "ProvisionedThroughput",
    "ScalarAttributeType",
    "TableMetadata",
    "TableStatus",
    # Operations
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
    "QueryRequest",
    "QueryResponse",
    "ScanRequest",
    "ScanResponse",
]
