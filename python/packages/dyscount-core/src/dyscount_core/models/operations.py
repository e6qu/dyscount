"""DynamoDB API Control Plane operation models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .table import (
    AttributeDefinition,
    BillingMode,
    GlobalSecondaryIndex,
    KeySchemaElement,
    LocalSecondaryIndex,
    ProvisionedThroughput,
    StreamSpecification,
    TableMetadata,
)


# =============================================================================
# CreateTable
# =============================================================================

class CreateTableRequest(BaseModel):
    """Request model for CreateTable operation.
    
    Creates a new DynamoDB table.
    
    Attributes:
        TableName: The name of the table to create (required)
        KeySchema: The primary key structure for the table (required)
        AttributeDefinitions: An array of attributes that describe the key schema (required)
        BillingMode: Controls how you are charged for read and write throughput
        ProvisionedThroughput: Represents the provisioned throughput settings
        GlobalSecondaryIndexes: One or more global secondary indexes
        LocalSecondaryIndexes: One or more local secondary indexes
        StreamSpecification: The settings for DynamoDB Streams
        SSESpecification: Represents the settings used to enable server-side encryption
        Tags: A list of key-value pairs to label the table
        TableClass: The table class (STANDARD or STANDARD_INFREQUENT_ACCESS)
        DeletionProtectionEnabled: Whether to enable deletion protection
    """
    table_name: str = Field(..., min_length=1, max_length=1024, alias="TableName")
    key_schema: List[KeySchemaElement] = Field(..., alias="KeySchema")
    attribute_definitions: List[AttributeDefinition] = Field(..., alias="AttributeDefinitions")
    billing_mode: BillingMode = Field(default="PROVISIONED", alias="BillingMode")
    provisioned_throughput: Optional[ProvisionedThroughput] = Field(default=None, alias="ProvisionedThroughput")
    global_secondary_indexes: Optional[List[GlobalSecondaryIndex]] = Field(default=None, alias="GlobalSecondaryIndexes")
    local_secondary_indexes: Optional[List[LocalSecondaryIndex]] = Field(default=None, alias="LocalSecondaryIndexes")
    stream_specification: Optional[StreamSpecification] = Field(default=None, alias="StreamSpecification")
    sse_specification: Optional[Dict[str, Any]] = Field(default=None, alias="SSESpecification")
    tags: Optional[List[Dict[str, str]]] = Field(default=None, alias="Tags")
    table_class: Optional[str] = Field(default=None, alias="TableClass")
    deletion_protection_enabled: Optional[bool] = Field(default=None, alias="DeletionProtectionEnabled")

    def model_post_init(self, __context: Any) -> None:
        """Set default provisioned throughput if not provided."""
        if self.billing_mode == BillingMode.PROVISIONED and self.provisioned_throughput is None:
            self.provisioned_throughput = ProvisionedThroughput(
                ReadCapacityUnits=5, WriteCapacityUnits=5
            )


class CreateTableResponse(BaseModel):
    """Response model for CreateTable operation.
    
    Attributes:
        TableDescription: The description of the created table
    """
    TableDescription: TableMetadata


# =============================================================================
# DeleteTable
# =============================================================================

class DeleteTableRequest(BaseModel):
    """Request model for DeleteTable operation.
    
    Deletes a table and all of its items.
    
    Attributes:
        TableName: The name of the table to delete
    """
    TableName: str = Field(..., min_length=1, max_length=1024)


class DeleteTableResponse(BaseModel):
    """Response model for DeleteTable operation.
    
    Attributes:
        TableDescription: The description of the deleted table
    """
    TableDescription: Optional[TableMetadata] = None


# =============================================================================
# DescribeTable
# =============================================================================

class DescribeTableRequest(BaseModel):
    """Request model for DescribeTable operation.
    
    Returns information about the table.
    
    Attributes:
        TableName: The name of the table to describe
    """
    TableName: str = Field(..., min_length=1, max_length=1024)


class DescribeTableResponse(BaseModel):
    """Response model for DescribeTable operation.
    
    Attributes:
        Table: The description of the table
    """
    Table: TableMetadata


# =============================================================================
# ListTables
# =============================================================================

class ListTablesRequest(BaseModel):
    """Request model for ListTables operation.
    
    Returns an array of table names associated with the current account and endpoint.
    
    Attributes:
        ExclusiveStartTableName: The first table name that this operation will evaluate
        Limit: A maximum number of table names to return (1-100)
    """
    ExclusiveStartTableName: Optional[str] = None
    Limit: Optional[int] = Field(None, ge=1, le=100)


class ListTablesResponse(BaseModel):
    """Response model for ListTables operation.
    
    Attributes:
        TableNames: The names of the tables associated with the current account
        LastEvaluatedTableName: The name of the last table in the current page of results
    """
    TableNames: List[str]
    LastEvaluatedTableName: Optional[str] = None


# =============================================================================
# DescribeEndpoints
# =============================================================================

class Endpoint(BaseModel):
    """Represents an endpoint for DynamoDB.
    
    Attributes:
        Address: The endpoint address
        CachePeriodInMinutes: How long to cache the endpoint information (in minutes)
    """
    Address: str
    CachePeriodInMinutes: int


class DescribeEndpointsRequest(BaseModel):
    """Request model for DescribeEndpoints operation.
    
    Returns the regional endpoint information.
    """
    pass


class DescribeEndpointsResponse(BaseModel):
    """Response model for DescribeEndpoints operation.
    
    Attributes:
        Endpoints: List of endpoints for DynamoDB
    """
    Endpoints: List[Endpoint]


# =============================================================================
# UpdateTable (additional operation)
# =============================================================================

class UpdateTableRequest(BaseModel):
    """Request model for UpdateTable operation.
    
    Modifies the provisioned throughput settings, global secondary indexes,
    or DynamoDB Streams settings for a given table.
    
    Attributes:
        TableName: The name of the table to be updated
        AttributeDefinitions: An array of attributes that describe the key schema
        BillingMode: Controls how you are charged for read and write throughput
        ProvisionedThroughput: The new provisioned throughput settings
        GlobalSecondaryIndexUpdates: An array of global secondary index updates
        StreamSpecification: Represents the DynamoDB Streams configuration
        SSESpecification: The server-side encryption settings
        DeletionProtectionEnabled: Whether to enable deletion protection
    """
    TableName: str = Field(..., min_length=1, max_length=1024)
    AttributeDefinitions: Optional[List[AttributeDefinition]] = None
    BillingMode: Optional[BillingMode] = None
    ProvisionedThroughput: Optional[ProvisionedThroughput] = None
    GlobalSecondaryIndexUpdates: Optional[List[Dict[str, Any]]] = None
    StreamSpecification: Optional[StreamSpecification] = None
    SSESpecification: Optional[Dict[str, Any]] = None
    DeletionProtectionEnabled: Optional[bool] = None


class UpdateTableResponse(BaseModel):
    """Response model for UpdateTable operation.
    
    Attributes:
        TableDescription: The description of the updated table
    """
    TableDescription: TableMetadata


# =============================================================================
# DescribeLimits (additional operation)
# =============================================================================

class DescribeLimitsRequest(BaseModel):
    """Request model for DescribeLimits operation.
    
    Returns the current provisioned-capacity limits for your AWS account in a region.
    """
    pass


class DescribeLimitsResponse(BaseModel):
    """Response model for DescribeLimits operation.
    
    Attributes:
        AccountMaxReadCapacityUnits: The maximum total read capacity units
        AccountMaxWriteCapacityUnits: The maximum total write capacity units
        TableMaxReadCapacityUnits: The maximum read capacity units per table
        TableMaxWriteCapacityUnits: The maximum write capacity units per table
    """
    AccountMaxReadCapacityUnits: int
    AccountMaxWriteCapacityUnits: int
    TableMaxReadCapacityUnits: int
    TableMaxWriteCapacityUnits: int





# =============================================================================
# GetItem (Data Plane)
# =============================================================================

class ConsumedCapacity(BaseModel):
    """The capacity units consumed by an operation.
    
    Attributes:
        TableName: The name of the table
        CapacityUnits: The total number of capacity units consumed
        ReadCapacityUnits: The total number of read capacity units consumed
        WriteCapacityUnits: The total number of write capacity units consumed
    """
    model_config = {"populate_by_name": True}
    
    table_name: Optional[str] = Field(None, alias="TableName")
    capacity_units: Optional[float] = Field(None, alias="CapacityUnits")
    read_capacity_units: Optional[float] = Field(None, alias="ReadCapacityUnits")
    write_capacity_units: Optional[float] = Field(None, alias="WriteCapacityUnits")


class GetItemRequest(BaseModel):
    """Request model for GetItem operation.
    
    Retrieves a single item from a table based on its primary key.
    
    Attributes:
        TableName: The name of the table (required)
        Key: A map of attribute names to AttributeValue objects representing the primary key (required)
        AttributesToGet: An array of attribute names to retrieve (legacy, use ProjectionExpression)
        ConsistentRead: Whether to use strongly consistent reads (default: false)
        ProjectionExpression: A string that identifies one or more attributes to retrieve
        ExpressionAttributeNames: One or more substitution tokens for attribute names
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., min_length=1, max_length=1024, alias="TableName")
    key: Dict[str, Any] = Field(..., alias="Key")
    attributes_to_get: Optional[List[str]] = Field(None, alias="AttributesToGet")
    consistent_read: Optional[bool] = Field(False, alias="ConsistentRead")
    projection_expression: Optional[str] = Field(None, alias="ProjectionExpression")
    expression_attribute_names: Optional[Dict[str, str]] = Field(None, alias="ExpressionAttributeNames")
    return_consumed_capacity: Optional[str] = Field(None, alias="ReturnConsumedCapacity")


class GetItemResponse(BaseModel):
    """Response model for GetItem operation.
    
    Attributes:
        Item: A map of attribute names to AttributeValue objects (only if item found)
        ConsumedCapacity: The capacity units consumed
    """
    model_config = {"populate_by_name": True}
    
    item: Optional[Dict[str, Any]] = Field(None, alias="Item")
    consumed_capacity: Optional[ConsumedCapacity] = Field(None, alias="ConsumedCapacity")
