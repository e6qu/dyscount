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
    BillingMode: Optional[Any] = None  # Using Any to avoid name collision with BillingMode type
    ProvisionedThroughput: Optional[Any] = None  # Using Any to avoid name collision
    GlobalSecondaryIndexUpdates: Optional[List[Dict[str, Any]]] = None
    StreamSpecification: Optional[Any] = None  # Using Any to avoid name collision
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


# =============================================================================
# PutItem (Data Plane)
# =============================================================================

class PutItemRequest(BaseModel):
    """Request model for PutItem operation.
    
    Creates a new item, or replaces an old item with a new item.
    
    Attributes:
        TableName: The name of the table (required)
        Item: A map of attribute name to AttributeValue (required)
        ConditionExpression: A condition that must be satisfied
        ExpressionAttributeNames: One or more substitution tokens for attribute names
        ExpressionAttributeValues: One or more values that can be substituted
        ReturnConsumedCapacity: Whether to return consumed capacity (INDEXES, TOTAL, NONE)
        ReturnItemCollectionMetrics: Whether to return item collection metrics (SIZE, NONE)
        ReturnValues: Use ALL_OLD to get the previous item attributes
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., min_length=1, max_length=1024, alias="TableName")
    item: dict[str, Any] = Field(..., alias="Item")
    condition_expression: str | None = Field(None, alias="ConditionExpression")
    expression_attribute_names: dict[str, str] | None = Field(None, alias="ExpressionAttributeNames")
    expression_attribute_values: dict[str, Any] | None = Field(None, alias="ExpressionAttributeValues")
    return_consumed_capacity: str | None = Field(None, alias="ReturnConsumedCapacity")
    return_item_collection_metrics: str | None = Field(None, alias="ReturnItemCollectionMetrics")
    return_values: str | None = Field(None, alias="ReturnValues")


class PutItemResponse(BaseModel):
    """Response model for PutItem operation.
    
    Attributes:
        Attributes: The attribute values as they appeared before the PutItem operation
        ConsumedCapacity: The capacity units consumed
        ItemCollectionMetrics: Information about item collections
    """
    model_config = {"populate_by_name": True}
    
    attributes: dict[str, Any] | None = Field(None, alias="Attributes")
    consumed_capacity: ConsumedCapacity | None = Field(None, alias="ConsumedCapacity")
    item_collection_metrics: dict[str, Any] | None = Field(None, alias="ItemCollectionMetrics")


# =============================================================================
# DeleteItem (Data Plane)
# =============================================================================

class DeleteItemRequest(BaseModel):
    """Request model for DeleteItem operation.
    
    Deletes a single item in a table by primary key.
    
    Attributes:
        TableName: The name of the table (required)
        Key: A map of attribute names to AttributeValue objects representing the primary key (required)
        ConditionExpression: A condition that must be satisfied
        ExpressionAttributeNames: One or more substitution tokens for attribute names
        ExpressionAttributeValues: One or more values that can be substituted
        ReturnConsumedCapacity: Whether to return consumed capacity
        ReturnItemCollectionMetrics: Whether to return item collection metrics
        ReturnValues: Use ALL_OLD to get the deleted item attributes
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., min_length=1, max_length=1024, alias="TableName")
    key: dict[str, Any] = Field(..., alias="Key")
    condition_expression: str | None = Field(None, alias="ConditionExpression")
    expression_attribute_names: dict[str, str] | None = Field(None, alias="ExpressionAttributeNames")
    expression_attribute_values: dict[str, Any] | None = Field(None, alias="ExpressionAttributeValues")
    return_consumed_capacity: str | None = Field(None, alias="ReturnConsumedCapacity")
    return_item_collection_metrics: str | None = Field(None, alias="ReturnItemCollectionMetrics")
    return_values: str | None = Field(None, alias="ReturnValues")


class DeleteItemResponse(BaseModel):
    """Response model for DeleteItem operation.
    
    Attributes:
        Attributes: The attribute values as they appeared before the DeleteItem operation
        ConsumedCapacity: The capacity units consumed
        ItemCollectionMetrics: Information about item collections
    """
    model_config = {"populate_by_name": True}
    
    attributes: dict[str, Any] | None = Field(None, alias="Attributes")
    consumed_capacity: ConsumedCapacity | None = Field(None, alias="ConsumedCapacity")
    item_collection_metrics: dict[str, Any] | None = Field(None, alias="ItemCollectionMetrics")


# =============================================================================
# UpdateItem (Data Plane)
# =============================================================================

class UpdateItemRequest(BaseModel):
    """Request model for UpdateItem operation.
    
    Edits an existing item's attributes, or adds a new item to the table if
    it does not already exist.
    
    Attributes:
        TableName: The name of the table (required)
        Key: A map of attribute names to AttributeValue objects representing the primary key (required)
        UpdateExpression: An expression that describes one or more attributes to be updated (required)
        ConditionExpression: A condition that must be satisfied
        ExpressionAttributeNames: One or more substitution tokens for attribute names
        ExpressionAttributeValues: One or more values that can be substituted
        ReturnConsumedCapacity: Whether to return consumed capacity
        ReturnItemCollectionMetrics: Whether to return item collection metrics
        ReturnValues: Use ALL_OLD, ALL_NEW, UPDATED_OLD, or UPDATED_NEW
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., min_length=1, max_length=1024, alias="TableName")
    key: dict[str, Any] = Field(..., alias="Key")
    update_expression: str = Field(..., alias="UpdateExpression")
    condition_expression: str | None = Field(None, alias="ConditionExpression")
    expression_attribute_names: dict[str, str] | None = Field(None, alias="ExpressionAttributeNames")
    expression_attribute_values: dict[str, Any] | None = Field(None, alias="ExpressionAttributeValues")
    return_consumed_capacity: str | None = Field(None, alias="ReturnConsumedCapacity")
    return_item_collection_metrics: str | None = Field(None, alias="ReturnItemCollectionMetrics")
    return_values: str | None = Field(None, alias="ReturnValues")


class UpdateItemResponse(BaseModel):
    """Response model for UpdateItem operation.
    
    Attributes:
        Attributes: The attribute values as they appeared before/after the operation
        ConsumedCapacity: The capacity units consumed
        ItemCollectionMetrics: Information about item collections
    """
    model_config = {"populate_by_name": True}
    
    attributes: dict[str, Any] | None = Field(None, alias="Attributes")
    consumed_capacity: ConsumedCapacity | None = Field(None, alias="ConsumedCapacity")
    item_collection_metrics: dict[str, Any] | None = Field(None, alias="ItemCollectionMetrics")



# =============================================================================
# Query (Data Plane)
# =============================================================================

class QueryRequest(BaseModel):
    """Request model for Query operation.
    
    Queries a table or index using the primary key.
    
    Attributes:
        TableName: The name of the table (required)
        IndexName: The name of a secondary index to query
        KeyConditionExpression: The condition that specifies the key values (required)
        FilterExpression: A filter expression to apply after the query
        ProjectionExpression: A string that identifies attributes to retrieve
        ExpressionAttributeNames: Substitution tokens for attribute names
        ExpressionAttributeValues: Values that can be substituted
        ScanIndexForward: If true, results in ascending order; if false, descending
        Select: Attributes to return (ALL_ATTRIBUTES, ALL_PROJECTED_ATTRIBUTES, SPECIFIC_ATTRIBUTES, COUNT)
        Limit: The maximum number of items to evaluate
        ExclusiveStartKey: The primary key of the first item to evaluate
        ReturnConsumedCapacity: Whether to return consumed capacity
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., min_length=1, max_length=1024, alias="TableName")
    index_name: str | None = Field(None, alias="IndexName")
    key_condition_expression: str = Field(..., alias="KeyConditionExpression")
    filter_expression: str | None = Field(None, alias="FilterExpression")
    projection_expression: str | None = Field(None, alias="ProjectionExpression")
    expression_attribute_names: dict[str, str] | None = Field(None, alias="ExpressionAttributeNames")
    expression_attribute_values: dict[str, Any] | None = Field(None, alias="ExpressionAttributeValues")
    scan_index_forward: bool = Field(True, alias="ScanIndexForward")
    select: str | None = Field(None, alias="Select")
    limit: int | None = Field(None, ge=1, alias="Limit")
    exclusive_start_key: dict[str, Any] | None = Field(None, alias="ExclusiveStartKey")
    return_consumed_capacity: str | None = Field(None, alias="ReturnConsumedCapacity")


class QueryResponse(BaseModel):
    """Response model for Query operation.
    
    Attributes:
        Items: An array of item attributes that match the query criteria
        Count: The number of items that matched the query conditions
        ScannedCount: The number of items evaluated
        LastEvaluatedKey: The primary key of the item where the operation stopped
        ConsumedCapacity: The capacity units consumed
    """
    model_config = {"populate_by_name": True}
    
    items: list[dict[str, Any]] = Field(default_factory=list, alias="Items")
    count: int = Field(0, alias="Count")
    scanned_count: int = Field(0, alias="ScannedCount")
    last_evaluated_key: dict[str, Any] | None = Field(None, alias="LastEvaluatedKey")
    consumed_capacity: ConsumedCapacity | None = Field(None, alias="ConsumedCapacity")


# =============================================================================
# Scan (Data Plane)
# =============================================================================

class ScanRequest(BaseModel):
    """Request model for Scan operation.
    
    Scans a table or index and returns one or more items.
    
    Attributes:
        TableName: The name of the table (required)
        IndexName: The name of a secondary index to scan
        FilterExpression: A filter expression to apply to the results
        ProjectionExpression: A string that identifies attributes to retrieve
        ExpressionAttributeNames: Substitution tokens for attribute names
        ExpressionAttributeValues: Values that can be substituted
        Segment: For parallel scan, the segment to scan
        TotalSegments: For parallel scan, the total number of segments
        Select: Attributes to return
        Limit: The maximum number of items to evaluate
        ExclusiveStartKey: The primary key of the first item to evaluate
        ReturnConsumedCapacity: Whether to return consumed capacity
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., min_length=1, max_length=1024, alias="TableName")
    index_name: str | None = Field(None, alias="IndexName")
    filter_expression: str | None = Field(None, alias="FilterExpression")
    projection_expression: str | None = Field(None, alias="ProjectionExpression")
    expression_attribute_names: dict[str, str] | None = Field(None, alias="ExpressionAttributeNames")
    expression_attribute_values: dict[str, Any] | None = Field(None, alias="ExpressionAttributeValues")
    segment: int | None = Field(None, ge=0, alias="Segment")
    total_segments: int | None = Field(None, ge=1, alias="TotalSegments")
    select: str | None = Field(None, alias="Select")
    limit: int | None = Field(None, ge=1, alias="Limit")
    exclusive_start_key: dict[str, Any] | None = Field(None, alias="ExclusiveStartKey")
    return_consumed_capacity: str | None = Field(None, alias="ReturnConsumedCapacity")


class ScanResponse(BaseModel):
    """Response model for Scan operation.
    
    Attributes:
        Items: An array of item attributes that match the scan criteria
        Count: The number of items that matched the filter expression
        ScannedCount: The number of items evaluated
        LastEvaluatedKey: The primary key of the item where the operation stopped
        ConsumedCapacity: The capacity units consumed
    """
    model_config = {"populate_by_name": True}
    
    items: list[dict[str, Any]] = Field(default_factory=list, alias="Items")
    count: int = Field(0, alias="Count")
    scanned_count: int = Field(0, alias="ScannedCount")
    last_evaluated_key: dict[str, Any] | None = Field(None, alias="LastEvaluatedKey")
    consumed_capacity: ConsumedCapacity | None = Field(None, alias="ConsumedCapacity")



# =============================================================================
# BatchGetItem (Data Plane)
# =============================================================================

class BatchGetItemRequest(BaseModel):
    """Request model for BatchGetItem operation.
    
    Retrieves multiple items from one or more tables.
    
    Attributes:
        RequestItems: A map of table names to GetItem requests (required)
        ReturnConsumedCapacity: Whether to return consumed capacity (INDEXES, TOTAL, NONE)
    """
    model_config = {"populate_by_name": True}
    
    request_items: dict[str, "BatchGetItemTableRequest"] = Field(..., alias="RequestItems")
    return_consumed_capacity: str | None = Field(None, alias="ReturnConsumedCapacity")


class BatchGetItemTableRequest(BaseModel):
    """Request for a single table in BatchGetItem.
    
    Attributes:
        Keys: List of primary keys to retrieve
        ProjectionExpression: Attributes to retrieve
        ExpressionAttributeNames: Substitution tokens for attribute names
        ConsistentRead: Whether to use strongly consistent reads
    """
    model_config = {"populate_by_name": True}
    
    keys: list[dict[str, Any]] = Field(..., alias="Keys")
    projection_expression: str | None = Field(None, alias="ProjectionExpression")
    expression_attribute_names: dict[str, str] | None = Field(None, alias="ExpressionAttributeNames")
    consistent_read: bool = Field(False, alias="ConsistentRead")


class BatchGetItemResponse(BaseModel):
    """Response model for BatchGetItem operation.
    
    Attributes:
        Responses: A map of table names to retrieved items
        UnprocessedKeys: Keys that could not be processed (due to limits)
        ConsumedCapacity: The capacity units consumed
    """
    model_config = {"populate_by_name": True}
    
    responses: dict[str, list[dict[str, Any]]] = Field(default_factory=dict, alias="Responses")
    unprocessed_keys: Optional[dict[str, BatchGetItemTableRequest]] = Field(None, alias="UnprocessedKeys")
    consumed_capacity: list[ConsumedCapacity] | None = Field(None, alias="ConsumedCapacity")


# =============================================================================
# BatchWriteItem (Data Plane)
# =============================================================================

class BatchWriteItemRequest(BaseModel):
    """Request model for BatchWriteItem operation.
    
    Puts or deletes multiple items in one or more tables.
    
    Attributes:
        RequestItems: A map of table names to write requests (required)
        ReturnConsumedCapacity: Whether to return consumed capacity
        ReturnItemCollectionMetrics: Whether to return item collection metrics
    """
    model_config = {"populate_by_name": True}
    
    request_items: dict[str, list["BatchWriteItemTableRequest"]] = Field(..., alias="RequestItems")
    return_consumed_capacity: str | None = Field(None, alias="ReturnConsumedCapacity")
    return_item_collection_metrics: str | None = Field(None, alias="ReturnItemCollectionMetrics")


class BatchWriteItemTableRequest(BaseModel):
    """Request for a single write operation in BatchWriteItem.
    
    Attributes:
        PutRequest: Item to put (if present, DeleteRequest must not be)
        DeleteRequest: Key to delete (if present, PutRequest must not be)
    """
    model_config = {"populate_by_name": True}
    
    put_request: Optional["PutRequest"] = Field(None, alias="PutRequest")
    delete_request: Optional["DeleteRequest"] = Field(None, alias="DeleteRequest")


class PutRequest(BaseModel):
    """Put request for BatchWriteItem.
    
    Attributes:
        Item: The item to put
    """
    model_config = {"populate_by_name": True}
    
    item: dict[str, Any] = Field(..., alias="Item")


class DeleteRequest(BaseModel):
    """Delete request for BatchWriteItem.
    
    Attributes:
        Key: The key of the item to delete
    """
    model_config = {"populate_by_name": True}
    
    key: dict[str, Any] = Field(..., alias="Key")


class BatchWriteItemResponse(BaseModel):
    """Response model for BatchWriteItem operation.
    
    Attributes:
        UnprocessedItems: Items that could not be processed (due to limits)
        ItemCollectionMetrics: Information about item collections
        ConsumedCapacity: The capacity units consumed
    """
    model_config = {"populate_by_name": True}
    
    unprocessed_items: Optional[dict[str, list[BatchWriteItemTableRequest]]] = Field(None, alias="UnprocessedItems")
    item_collection_metrics: dict[str, Any] | None = Field(None, alias="ItemCollectionMetrics")
    consumed_capacity: list[ConsumedCapacity] | None = Field(None, alias="ConsumedCapacity")



# =============================================================================
# TransactGetItems (Data Plane)
# =============================================================================

class TransactGetItemsRequest(BaseModel):
    """Request model for TransactGetItems operation.
    
    Retrieves multiple items from one or more tables in a single atomic transaction.
    
    Attributes:
        TransactItems: A list of Get operations (up to 100) (required)
        ReturnConsumedCapacity: Whether to return consumed capacity (INDEXES, TOTAL, NONE)
    """
    model_config = {"populate_by_name": True}
    
    transact_items: list["TransactGetItem"] = Field(..., alias="TransactItems")
    return_consumed_capacity: Optional[str] = Field(None, alias="ReturnConsumedCapacity")


class TransactGetItem(BaseModel):
    """Single Get operation within a TransactGetItems transaction.
    
    Attributes:
        Get: The Get operation details
    """
    model_config = {"populate_by_name": True}
    
    get: "TransactGet" = Field(..., alias="Get")


class TransactGet(BaseModel):
    """Details of a Get operation within a transaction.
    
    Attributes:
        TableName: The name of the table (required)
        Key: The primary key of the item to retrieve (required)
        ProjectionExpression: Attributes to retrieve
        ExpressionAttributeNames: Substitution tokens for attribute names
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., min_length=1, max_length=1024, alias="TableName")
    key: dict[str, Any] = Field(..., alias="Key")
    projection_expression: Optional[str] = Field(None, alias="ProjectionExpression")
    expression_attribute_names: Optional[dict[str, str]] = Field(None, alias="ExpressionAttributeNames")


class TransactGetItemsResponse(BaseModel):
    """Response model for TransactGetItems operation.
    
    Attributes:
        Responses: List of retrieved items in the same order as the request
        ConsumedCapacity: The capacity units consumed
    """
    model_config = {"populate_by_name": True}
    
    responses: list[dict[str, Any]] = Field(default_factory=list, alias="Responses")
    consumed_capacity: Optional[list[ConsumedCapacity]] = Field(None, alias="ConsumedCapacity")


# =============================================================================
# TransactWriteItems (Data Plane)
# =============================================================================

class TransactWriteItemsRequest(BaseModel):
    """Request model for TransactWriteItems operation.
    
    Performs multiple write operations in a single atomic transaction.
    
    Attributes:
        TransactItems: A list of write operations (up to 100) (required)
        ReturnConsumedCapacity: Whether to return consumed capacity
        ReturnItemCollectionMetrics: Whether to return item collection metrics
        ClientRequestToken: Token for idempotency
    """
    model_config = {"populate_by_name": True}
    
    transact_items: list["TransactWriteItem"] = Field(..., alias="TransactItems")
    return_consumed_capacity: Optional[str] = Field(None, alias="ReturnConsumedCapacity")
    return_item_collection_metrics: Optional[str] = Field(None, alias="ReturnItemCollectionMetrics")
    client_request_token: Optional[str] = Field(None, alias="ClientRequestToken")


class TransactWriteItem(BaseModel):
    """Single write operation within a TransactWriteItems transaction.
    
    Attributes:
        ConditionCheck: A condition check operation
        Put: A put operation
        Delete: A delete operation
        Update: An update operation
    """
    model_config = {"populate_by_name": True}
    
    condition_check: Optional["TransactConditionCheck"] = Field(None, alias="ConditionCheck")
    put: Optional["TransactPut"] = Field(None, alias="Put")
    delete: Optional["TransactDelete"] = Field(None, alias="Delete")
    update: Optional["TransactUpdate"] = Field(None, alias="Update")


class TransactConditionCheck(BaseModel):
    """Condition check operation within a transaction.
    
    Attributes:
        TableName: The name of the table (required)
        Key: The primary key of the item (required)
        ConditionExpression: The condition to evaluate (required)
        ExpressionAttributeNames: Substitution tokens for attribute names
        ExpressionAttributeValues: Values that can be substituted
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., min_length=1, max_length=1024, alias="TableName")
    key: dict[str, Any] = Field(..., alias="Key")
    condition_expression: str = Field(..., alias="ConditionExpression")
    expression_attribute_names: Optional[dict[str, str]] = Field(None, alias="ExpressionAttributeNames")
    expression_attribute_values: Optional[dict[str, Any]] = Field(None, alias="ExpressionAttributeValues")


class TransactPut(BaseModel):
    """Put operation within a transaction.
    
    Attributes:
        TableName: The name of the table (required)
        Item: The item to put (required)
        ConditionExpression: A condition that must be satisfied
        ExpressionAttributeNames: Substitution tokens for attribute names
        ExpressionAttributeValues: Values that can be substituted
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., min_length=1, max_length=1024, alias="TableName")
    item: dict[str, Any] = Field(..., alias="Item")
    condition_expression: Optional[str] = Field(None, alias="ConditionExpression")
    expression_attribute_names: Optional[dict[str, str]] = Field(None, alias="ExpressionAttributeNames")
    expression_attribute_values: Optional[dict[str, Any]] = Field(None, alias="ExpressionAttributeValues")


class TransactDelete(BaseModel):
    """Delete operation within a transaction.
    
    Attributes:
        TableName: The name of the table (required)
        Key: The primary key of the item to delete (required)
        ConditionExpression: A condition that must be satisfied
        ExpressionAttributeNames: Substitution tokens for attribute names
        ExpressionAttributeValues: Values that can be substituted
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., min_length=1, max_length=1024, alias="TableName")
    key: dict[str, Any] = Field(..., alias="Key")
    condition_expression: Optional[str] = Field(None, alias="ConditionExpression")
    expression_attribute_names: Optional[dict[str, str]] = Field(None, alias="ExpressionAttributeNames")
    expression_attribute_values: Optional[dict[str, Any]] = Field(None, alias="ExpressionAttributeValues")


class TransactUpdate(BaseModel):
    """Update operation within a transaction.
    
    Attributes:
        TableName: The name of the table (required)
        Key: The primary key of the item to update (required)
        UpdateExpression: The update expression (required)
        ConditionExpression: A condition that must be satisfied
        ExpressionAttributeNames: Substitution tokens for attribute names
        ExpressionAttributeValues: Values that can be substituted
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., min_length=1, max_length=1024, alias="TableName")
    key: dict[str, Any] = Field(..., alias="Key")
    update_expression: str = Field(..., alias="UpdateExpression")
    condition_expression: Optional[str] = Field(None, alias="ConditionExpression")
    expression_attribute_names: Optional[dict[str, str]] = Field(None, alias="ExpressionAttributeNames")
    expression_attribute_values: Optional[dict[str, Any]] = Field(None, alias="ExpressionAttributeValues")


class TransactWriteItemsResponse(BaseModel):
    """Response model for TransactWriteItems operation.
    
    Attributes:
        ConsumedCapacity: The capacity units consumed
        ItemCollectionMetrics: Information about item collections
    """
    model_config = {"populate_by_name": True}
    
    consumed_capacity: Optional[list[ConsumedCapacity]] = Field(None, alias="ConsumedCapacity")
    item_collection_metrics: Optional[dict[str, Any]] = Field(None, alias="ItemCollectionMetrics")



# =============================================================================
# Tagging Operations
# =============================================================================

class TagResourceRequest(BaseModel):
    """Request model for TagResource operation.
    
    Assigns tags to a resource (table).
    
    Attributes:
        ResourceArn: The Amazon Resource Name (ARN) of the resource
        Tags: A list of tags to assign to the resource
    """
    model_config = {"populate_by_name": True}
    
    resource_arn: str = Field(..., alias="ResourceArn")
    tags: list[dict[str, str]] = Field(..., alias="Tags")  # List of {Key: str, Value: str}


class TagResourceResponse(BaseModel):
    """Response model for TagResource operation.
    
    Empty response on success.
    """
    model_config = {"populate_by_name": True}


class UntagResourceRequest(BaseModel):
    """Request model for UntagResource operation.
    
    Removes tags from a resource.
    
    Attributes:
        ResourceArn: The Amazon Resource Name (ARN) of the resource
        TagKeys: A list of tag keys to remove
    """
    model_config = {"populate_by_name": True}
    
    resource_arn: str = Field(..., alias="ResourceArn")
    tag_keys: list[str] = Field(..., alias="TagKeys")


class UntagResourceResponse(BaseModel):
    """Response model for UntagResource operation.
    
    Empty response on success.
    """
    model_config = {"populate_by_name": True}


class ListTagsOfResourceRequest(BaseModel):
    """Request model for ListTagsOfResource operation.
    
    Lists all tags on a resource.
    
    Attributes:
        ResourceArn: The Amazon Resource Name (ARN) of the resource
        NextToken: A token to retrieve the next page of results
    """
    model_config = {"populate_by_name": True}
    
    resource_arn: str = Field(..., alias="ResourceArn")
    next_token: Optional[str] = Field(None, alias="NextToken")


class ListTagsOfResourceResponse(BaseModel):
    """Response model for ListTagsOfResource operation.
    
    Attributes:
        Tags: A list of tags assigned to the resource
        NextToken: A token for retrieving the next page of results
    """
    model_config = {"populate_by_name": True}
    
    tags: list[dict[str, str]] = Field(default_factory=list, alias="Tags")
    next_token: Optional[str] = Field(None, alias="NextToken")



# =============================================================================
# Time-to-Live (TTL) Operations
# =============================================================================

class TimeToLiveSpecification(BaseModel):
    """Represents the TTL configuration for a table.
    
    Attributes:
        AttributeName: The name of the TTL attribute (required)
        Enabled: Whether TTL is enabled (required)
    """
    model_config = {"populate_by_name": True}
    
    attribute_name: str = Field(..., alias="AttributeName")
    enabled: bool = Field(..., alias="Enabled")


class UpdateTimeToLiveRequest(BaseModel):
    """Request model for UpdateTimeToLive operation.
    
    Enables or disables TTL on a table.
    
    Attributes:
        TableName: The name of the table (required)
        TimeToLiveSpecification: The TTL configuration (required)
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., alias="TableName")
    time_to_live_specification: TimeToLiveSpecification = Field(..., alias="TimeToLiveSpecification")


class TimeToLiveDescription(BaseModel):
    """Describes the TTL configuration of a table.
    
    Attributes:
        AttributeName: The name of the TTL attribute
        TimeToLiveStatus: The status of TTL (ENABLING, DISABLING, ENABLED, DISABLED)
    """
    model_config = {"populate_by_name": True}
    
    attribute_name: Optional[str] = Field(None, alias="AttributeName")
    time_to_live_status: str = Field(..., alias="TimeToLiveStatus")


class UpdateTimeToLiveResponse(BaseModel):
    """Response model for UpdateTimeToLive operation.
    
    Attributes:
        TimeToLiveSpecification: The updated TTL configuration
    """
    model_config = {"populate_by_name": True}
    
    time_to_live_specification: TimeToLiveSpecification = Field(..., alias="TimeToLiveSpecification")


class DescribeTimeToLiveRequest(BaseModel):
    """Request model for DescribeTimeToLive operation.
    
    Describes the TTL configuration of a table.
    
    Attributes:
        TableName: The name of the table (required)
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., alias="TableName")


class DescribeTimeToLiveResponse(BaseModel):
    """Response model for DescribeTimeToLive operation.
    
    Attributes:
        TimeToLiveDescription: The TTL configuration description
    """
    model_config = {"populate_by_name": True}
    
    time_to_live_description: TimeToLiveDescription = Field(..., alias="TimeToLiveDescription")


# =============================================================================
# Backup Operations (M2 Phase 2)
# =============================================================================

class BackupDetails(BaseModel):
    """Contains details about a backup.
    
    Attributes:
        BackupArn: The ARN of the backup
        BackupName: The name of the backup
        BackupSizeBytes: The size of the backup in bytes
        BackupStatus: The status of the backup (CREATING, DELETED, AVAILABLE)
        BackupType: The type of backup (USER, SYSTEM, AWS_BACKUP)
        CreationDateTime: When the backup was created
        TableArn: The ARN of the source table
        TableName: The name of the source table
    """
    model_config = {"populate_by_name": True}
    
    backup_arn: str = Field(..., alias="BackupArn")
    backup_name: str = Field(..., alias="BackupName")
    backup_size_bytes: int = Field(default=0, alias="BackupSizeBytes")
    backup_status: str = Field(default="CREATING", alias="BackupStatus")  # CREATING, DELETED, AVAILABLE
    backup_type: str = Field(default="USER", alias="BackupType")  # USER, SYSTEM, AWS_BACKUP
    creation_date_time: str = Field(..., alias="CreationDateTime")
    table_arn: str = Field(..., alias="TableArn")
    table_name: str = Field(..., alias="TableName")


class CreateBackupRequest(BaseModel):
    """Request model for CreateBackup operation.
    
    Creates a backup of an existing table.
    
    Attributes:
        TableName: The name of the table to back up (required)
        BackupName: The name of the backup (optional, defaults to table name + timestamp)
    """
    model_config = {"populate_by_name": True}
    
    table_name: str = Field(..., alias="TableName")
    backup_name: Optional[str] = Field(default=None, alias="BackupName")


class CreateBackupResponse(BaseModel):
    """Response model for CreateBackup operation.
    
    Attributes:
        BackupDetails: Details about the created backup
    """
    model_config = {"populate_by_name": True}
    
    backup_details: BackupDetails = Field(..., alias="BackupDetails")


class RestoreTableFromBackupRequest(BaseModel):
    """Request model for RestoreTableFromBackup operation.
    
    Creates a new table from an existing backup.
    
    Attributes:
        BackupArn: The ARN of the backup to restore from (required)
        TargetTableName: The name of the new table to create (required)
        BillingModeOverride: Overrides the billing mode for the restored table
        GlobalSecondaryIndexOverride: GSI definitions for the restored table
        LocalSecondaryIndexOverride: LSI definitions for the restored table
        ProvisionedThroughputOverride: Provisioned throughput for the restored table
        SSESpecificationOverride: SSE settings for the restored table
    """
    model_config = {"populate_by_name": True}
    
    backup_arn: str = Field(..., alias="BackupArn")
    target_table_name: str = Field(..., alias="TargetTableName")
    billing_mode_override: Optional[str] = Field(default=None, alias="BillingModeOverride")
    global_secondary_index_override: Optional[List[Dict[str, Any]]] = Field(default=None, alias="GlobalSecondaryIndexOverride")
    local_secondary_index_override: Optional[List[Dict[str, Any]]] = Field(default=None, alias="LocalSecondaryIndexOverride")
    provisioned_throughput_override: Optional[Dict[str, Any]] = Field(default=None, alias="ProvisionedThroughputOverride")
    sse_specification_override: Optional[Dict[str, Any]] = Field(default=None, alias="SSESpecificationOverride")


class RestoreTableFromBackupResponse(BaseModel):
    """Response model for RestoreTableFromBackup operation.
    
    Attributes:
        TableDescription: Details about the restored table
    """
    model_config = {"populate_by_name": True}
    
    table_description: TableMetadata = Field(..., alias="TableDescription")


class ListBackupsRequest(BaseModel):
    """Request model for ListBackups operation.
    
    Lists all backups for the account.
    
    Attributes:
        TableName: Filter by table name
        Limit: Maximum number of backups to return
        TimeRangeLowerBound: Filter backups created after this time
        TimeRangeUpperBound: Filter backups created before this time
        BackupType: Filter by backup type (USER, SYSTEM, AWS_BACKUP, ALL)
        ExclusiveStartBackupArn: For pagination
    """
    model_config = {"populate_by_name": True}
    
    table_name: Optional[str] = Field(default=None, alias="TableName")
    limit: Optional[int] = Field(default=None, alias="Limit")
    time_range_lower_bound: Optional[str] = Field(default=None, alias="TimeRangeLowerBound")
    time_range_upper_bound: Optional[str] = Field(default=None, alias="TimeRangeUpperBound")
    backup_type: Optional[str] = Field(default="ALL", alias="BackupType")
    exclusive_start_backup_arn: Optional[str] = Field(default=None, alias="ExclusiveStartBackupArn")


class ListBackupsResponse(BaseModel):
    """Response model for ListBackups operation.
    
    Attributes:
        BackupSummaries: List of backup summaries
        LastEvaluatedBackupArn: For pagination
    """
    model_config = {"populate_by_name": True}
    
    backup_summaries: List[BackupDetails] = Field(default_factory=list, alias="BackupSummaries")
    last_evaluated_backup_arn: Optional[str] = Field(default=None, alias="LastEvaluatedBackupArn")


class DeleteBackupRequest(BaseModel):
    """Request model for DeleteBackup operation.
    
    Deletes an existing backup.
    
    Attributes:
        BackupArn: The ARN of the backup to delete (required)
    """
    model_config = {"populate_by_name": True}
    
    backup_arn: str = Field(..., alias="BackupArn")


class DeleteBackupResponse(BaseModel):
    """Response model for DeleteBackup operation.
    
    Attributes:
        BackupDescription: Details about the deleted backup
    """
    model_config = {"populate_by_name": True}
    
    backup_description: Optional[BackupDetails] = Field(default=None, alias="BackupDescription")
