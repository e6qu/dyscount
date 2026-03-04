//! DynamoDB-compatible data models

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// DynamoDB attribute value with type information
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum AttributeValue {
    /// String attribute
    S { s: String },
    /// Number attribute (stored as string for precision)
    N { n: String },
    /// Binary attribute (base64 encoded)
    B { b: String },
    /// String set
    SS { ss: Vec<String> },
    /// Number set
    NS { ns: Vec<String> },
    /// Binary set
    BS { bs: Vec<String> },
    /// List attribute
    L { l: Vec<AttributeValue> },
    /// Map attribute
    M { m: HashMap<String, AttributeValue> },
    /// Boolean attribute
    BOOL { bool: bool },
    /// Null attribute
    NULL { null: bool },
}

impl AttributeValue {
    /// Create a string attribute
    pub fn s(value: impl Into<String>) -> Self {
        AttributeValue::S { s: value.into() }
    }

    /// Create a number attribute
    pub fn n(value: impl Into<String>) -> Self {
        AttributeValue::N { n: value.into() }
    }

    /// Create a binary attribute
    pub fn b(value: impl Into<String>) -> Self {
        AttributeValue::B { b: value.into() }
    }

    /// Create a boolean attribute
    pub fn bool(value: bool) -> Self {
        AttributeValue::BOOL { bool: value }
    }

    /// Create a null attribute
    pub fn null() -> Self {
        AttributeValue::NULL { null: true }
    }

    /// Create a list attribute
    pub fn l(value: Vec<AttributeValue>) -> Self {
        AttributeValue::L { l: value }
    }

    /// Create a map attribute
    pub fn m(value: HashMap<String, AttributeValue>) -> Self {
        AttributeValue::M { m: value }
    }

    /// Get string value if this is a string attribute
    pub fn as_s(&self) -> Option<&str> {
        match self {
            AttributeValue::S { s } => Some(s),
            _ => None,
        }
    }

    /// Get number value if this is a number attribute
    pub fn as_n(&self) -> Option<&str> {
        match self {
            AttributeValue::N { n } => Some(n),
            _ => None,
        }
    }

    /// Get boolean value if this is a boolean attribute
    pub fn as_bool(&self) -> Option<bool> {
        match self {
            AttributeValue::BOOL { bool } => Some(*bool),
            _ => None,
        }
    }

    /// Check if this is a null attribute
    pub fn is_null(&self) -> bool {
        matches!(self, AttributeValue::NULL { null: true })
    }
}

/// DynamoDB item (map of attribute names to attribute values)
pub type Item = HashMap<String, AttributeValue>;

/// Key schema element
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct KeySchemaElement {
    #[serde(rename = "AttributeName")]
    pub attribute_name: String,
    #[serde(rename = "KeyType")]
    pub key_type: String, // "HASH" or "RANGE"
}

impl KeySchemaElement {
    pub fn hash(attribute_name: impl Into<String>) -> Self {
        Self {
            attribute_name: attribute_name.into(),
            key_type: "HASH".to_string(),
        }
    }

    pub fn range(attribute_name: impl Into<String>) -> Self {
        Self {
            attribute_name: attribute_name.into(),
            key_type: "RANGE".to_string(),
        }
    }
}

/// Attribute definition
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AttributeDefinition {
    #[serde(rename = "AttributeName")]
    pub attribute_name: String,
    #[serde(rename = "AttributeType")]
    pub attribute_type: String, // "S", "N", or "B"
}

impl AttributeDefinition {
    pub fn s(attribute_name: impl Into<String>) -> Self {
        Self {
            attribute_name: attribute_name.into(),
            attribute_type: "S".to_string(),
        }
    }

    pub fn n(attribute_name: impl Into<String>) -> Self {
        Self {
            attribute_name: attribute_name.into(),
            attribute_type: "N".to_string(),
        }
    }

    pub fn b(attribute_name: impl Into<String>) -> Self {
        Self {
            attribute_name: attribute_name.into(),
            attribute_type: "B".to_string(),
        }
    }
}

/// Provisioned throughput settings
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProvisionedThroughput {
    pub read_capacity_units: i64,
    pub write_capacity_units: i64,
}

impl Default for ProvisionedThroughput {
    fn default() -> Self {
        Self {
            read_capacity_units: 5,
            write_capacity_units: 5,
        }
    }
}

/// Billing mode summary
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BillingModeSummary {
    pub billing_mode: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_update_to_pay_per_request_date_time: Option<DateTime<Utc>>,
}

/// Projection for secondary indexes
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Projection {
    pub projection_type: String, // "ALL", "KEYS_ONLY", "INCLUDE"
    #[serde(skip_serializing_if = "Option::is_none")]
    pub non_key_attributes: Option<Vec<String>>,
}

/// Global secondary index
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GlobalSecondaryIndex {
    pub index_name: String,
    pub key_schema: Vec<KeySchemaElement>,
    pub projection: Projection,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provisioned_throughput: Option<ProvisionedThroughput>,
}

/// Local secondary index
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LocalSecondaryIndex {
    pub index_name: String,
    pub key_schema: Vec<KeySchemaElement>,
    pub projection: Projection,
}

/// Tag
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Tag {
    pub key: String,
    pub value: String,
}

/// Key condition for Query operations
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Condition {
    #[serde(rename = "ComparisonOperator")]
    pub comparison_operator: String,
    #[serde(rename = "AttributeValueList")]
    pub attribute_value_list: Vec<AttributeValue>,
}

/// Table metadata
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TableMetadata {
    pub table_name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub table_arn: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub table_id: Option<String>,
    pub table_status: String,
    pub key_schema: Vec<KeySchemaElement>,
    pub attribute_definitions: Vec<AttributeDefinition>,
    pub item_count: i64,
    pub table_size_bytes: i64,
    pub creation_date_time: DateTime<Utc>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub billing_mode_summary: Option<BillingModeSummary>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provisioned_throughput: Option<ProvisionedThroughput>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub global_secondary_indexes: Option<Vec<GlobalSecondaryIndex>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub local_secondary_indexes: Option<Vec<LocalSecondaryIndex>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<Tag>>,
}

/// DynamoDB API error response
#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    #[serde(rename = "__type")]
    pub error_type: String,
    pub message: String,
}

impl ErrorResponse {
    pub fn new(error_type: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            error_type: error_type.into(),
            message: message.into(),
        }
    }

    pub fn validation_exception(message: impl Into<String>) -> Self {
        Self::new(
            "com.amazonaws.dynamodb.v20120810#ValidationException",
            message,
        )
    }

    pub fn resource_not_found(message: impl Into<String>) -> Self {
        Self::new(
            "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
            message,
        )
    }

    pub fn resource_in_use(message: impl Into<String>) -> Self {
        Self::new(
            "com.amazonaws.dynamodb.v20120810#ResourceInUseException",
            message,
        )
    }

    pub fn internal_server_error(message: impl Into<String>) -> Self {
        Self::new(
            "com.amazonaws.dynamodb.v20120810#InternalServerError",
            message,
        )
    }

    pub fn conditional_check_failed(message: impl Into<String>) -> Self {
        Self::new(
            "com.amazonaws.dynamodb.v20120810#ConditionalCheckFailedException",
            message,
        )
    }
}

/// DynamoDB request wrapper
#[derive(Debug, Clone, Deserialize)]
pub struct DynamoDBRequest {
    // Table operations
    #[serde(rename = "TableName")]
    pub table_name: Option<String>,
    #[serde(rename = "KeySchema")]
    pub key_schema: Option<Vec<KeySchemaElement>>,
    #[serde(rename = "AttributeDefinitions")]
    pub attribute_definitions: Option<Vec<AttributeDefinition>>,
    #[serde(rename = "BillingMode")]
    pub billing_mode: Option<String>,
    #[serde(rename = "GlobalSecondaryIndexes")]
    pub global_secondary_indexes: Option<Vec<GlobalSecondaryIndex>>,
    #[serde(rename = "LocalSecondaryIndexes")]
    pub local_secondary_indexes: Option<Vec<LocalSecondaryIndex>>,
    #[serde(rename = "ProvisionedThroughput")]
    pub provisioned_throughput: Option<ProvisionedThroughput>,
    #[serde(rename = "Tags")]
    pub tags: Option<Vec<Tag>>,
    #[serde(rename = "ResourceArn")]
    pub resource_arn: Option<String>,
    #[serde(rename = "TagKeys")]
    pub tag_keys: Option<Vec<String>>,

    // Item operations
    #[serde(rename = "Key")]
    pub key: Option<Item>,
    #[serde(rename = "Item")]
    pub item: Option<Item>,
    #[serde(rename = "IndexName")]
    pub index_name: Option<String>,
    #[serde(rename = "ConsistentRead")]
    pub consistent_read: Option<bool>,
    #[serde(rename = "ExclusiveStartKey")]
    pub exclusive_start_key: Option<Item>,
    #[serde(rename = "ExpressionAttributeNames")]
    pub expression_attribute_names: Option<HashMap<String, String>>,
    #[serde(rename = "ExpressionAttributeValues")]
    pub expression_attribute_values: Option<HashMap<String, AttributeValue>>,
    #[serde(rename = "FilterExpression")]
    pub filter_expression: Option<String>,
    #[serde(rename = "KeyConditionExpression")]
    pub key_condition_expression: Option<String>,
    #[serde(rename = "Limit")]
    pub limit: Option<i32>,
    #[serde(rename = "ProjectionExpression")]
    pub projection_expression: Option<String>,
    #[serde(rename = "ReturnConsumedCapacity")]
    pub return_consumed_capacity: Option<String>,
    #[serde(rename = "ReturnValues")]
    pub return_values: Option<String>,
    #[serde(rename = "ScanIndexForward")]
    pub scan_index_forward: Option<bool>,
    #[serde(rename = "Select")]
    pub select: Option<String>,
    #[serde(rename = "UpdateExpression")]
    pub update_expression: Option<String>,
    #[serde(rename = "ConditionExpression")]
    pub condition_expression: Option<String>,

    // Stream operations
    #[serde(rename = "StreamSpecification")]
    pub stream_specification: Option<StreamSpecification>,
}

/// DynamoDB response wrapper
#[derive(Debug, Serialize, Default)]
pub struct DynamoDBResponse {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub table_description: Option<TableMetadata>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub table_names: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub table: Option<TableMetadata>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<Tag>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub endpoints: Option<Vec<Endpoint>>,

    // Global Tables fields
    #[serde(skip_serializing_if = "Option::is_none", rename = "GlobalTableDescription")]
    pub global_table_description: Option<GlobalTableDescription>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "GlobalTables")]
    pub global_tables: Option<Vec<GlobalTableSummary>>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "LastEvaluatedGlobalTableName")]
    pub last_evaluated_global_table_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "ReplicaSettings")]
    pub replica_settings: Option<Vec<ReplicaSettingsDescription>>,

    // Limits fields
    #[serde(skip_serializing_if = "Option::is_none", rename = "AccountMaxReadCapacityUnits")]
    pub account_max_read_capacity_units: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "AccountMaxWriteCapacityUnits")]
    pub account_max_write_capacity_units: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "TableMaxReadCapacityUnits")]
    pub table_max_read_capacity_units: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "TableMaxWriteCapacityUnits")]
    pub table_max_write_capacity_units: Option<i64>,

    // Backup fields
    #[serde(skip_serializing_if = "Option::is_none", rename = "BackupDescription")]
    pub backup_description: Option<BackupDescription>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "BackupSummaries")]
    pub backup_summaries: Option<Vec<BackupSummary>>,

    // Item operation fields
    #[serde(skip_serializing_if = "Option::is_none", rename = "Item")]
    pub item: Option<Item>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "Attributes")]
    pub attributes: Option<Item>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "Items")]
    pub items: Option<Vec<Item>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub count: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub scanned_count: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "LastEvaluatedKey")]
    pub last_evaluated_key: Option<Item>,

    // Batch operation fields
    #[serde(skip_serializing_if = "Option::is_none", rename = "Responses")]
    pub batch_responses: Option<HashMap<String, Vec<Item>>>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "UnprocessedKeys")]
    pub unprocessed_keys: Option<HashMap<String, KeysAndAttributes>>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "UnprocessedItems")]
    pub unprocessed_items: Option<HashMap<String, Vec<WriteRequest>>>,

    // Transaction operation fields
    #[serde(skip_serializing_if = "Option::is_none", rename = "Responses")]
    pub item_responses: Option<Vec<ItemResponse>>,

    // Time to live fields
    #[serde(skip_serializing_if = "Option::is_none", rename = "TimeToLiveDescription")]
    pub time_to_live_description: Option<TimeToLiveDescription>,

    // PITR fields
    #[serde(skip_serializing_if = "Option::is_none", rename = "ContinuousBackupsDescription")]
    pub continuous_backups_description: Option<ContinuousBackupsDescription>,

    // Import/Export fields
    #[serde(skip_serializing_if = "Option::is_none", rename = "ExportDescription")]
    pub export_description: Option<ExportDescription>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "ExportSummaries")]
    pub export_summaries: Option<Vec<ExportSummary>>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "ImportDescription")]
    pub import_description: Option<ImportDescription>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "ImportSummaries")]
    pub import_summaries: Option<Vec<ImportSummary>>,

    // Streams fields
    #[serde(skip_serializing_if = "Option::is_none", rename = "Streams")]
    pub streams: Option<Vec<Stream>>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "StreamDescription")]
    pub stream_description: Option<StreamDescription>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "ShardIterator")]
    pub shard_iterator: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "Records")]
    pub records: Option<Vec<Record>>,
}

/// Endpoint information
#[derive(Debug, Serialize)]
pub struct Endpoint {
    pub address: String,
    pub cache_period_in_minutes: i64,
}

// ============== Batch Operations ==============

/// Keys and attributes for batch get
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeysAndAttributes {
    #[serde(rename = "Keys")]
    pub keys: Vec<Item>,
    #[serde(rename = "AttributesToGet")]
    pub attributes_to_get: Option<Vec<String>>,
    #[serde(rename = "ConsistentRead")]
    pub consistent_read: Option<bool>,
    #[serde(rename = "ExpressionAttributeNames")]
    pub expression_attribute_names: Option<HashMap<String, String>>,
    #[serde(rename = "ProjectionExpression")]
    pub projection_expression: Option<String>,
}

/// Batch get item request
#[derive(Debug, Clone, Deserialize)]
pub struct BatchGetItemRequest {
    #[serde(rename = "RequestItems")]
    pub request_items: HashMap<String, KeysAndAttributes>,
    #[serde(rename = "ReturnConsumedCapacity")]
    pub return_consumed_capacity: Option<String>,
}

/// Batch get item response
#[derive(Debug, Serialize, Default)]
pub struct BatchGetItemResponse {
    #[serde(skip_serializing_if = "Option::is_none", rename = "Responses")]
    pub responses: Option<HashMap<String, Vec<Item>>>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "UnprocessedKeys")]
    pub unprocessed_keys: Option<HashMap<String, KeysAndAttributes>>,
}

/// Put request for batch write
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PutRequest {
    #[serde(rename = "Item")]
    pub item: Item,
}

/// Delete request for batch write
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeleteRequest {
    #[serde(rename = "Key")]
    pub key: Item,
}

/// Write request for batch write (either put or delete)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WriteRequest {
    #[serde(rename = "PutRequest")]
    pub put_request: Option<PutRequest>,
    #[serde(rename = "DeleteRequest")]
    pub delete_request: Option<DeleteRequest>,
}

/// Batch write item request
#[derive(Debug, Clone, Deserialize)]
pub struct BatchWriteItemRequest {
    #[serde(rename = "RequestItems")]
    pub request_items: HashMap<String, Vec<WriteRequest>>,
    #[serde(rename = "ReturnConsumedCapacity")]
    pub return_consumed_capacity: Option<String>,
}

/// Batch write item response
#[derive(Debug, Serialize, Default)]
pub struct BatchWriteItemResponse {
    #[serde(skip_serializing_if = "Option::is_none", rename = "UnprocessedItems")]
    pub unprocessed_items: Option<HashMap<String, Vec<WriteRequest>>>,
}

// ============== Transaction Operations ==============

/// Transact get item
#[derive(Debug, Clone, Deserialize)]
pub struct TransactGet {
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "Key")]
    pub key: Item,
    #[serde(rename = "ProjectionExpression")]
    pub projection_expression: Option<String>,
    #[serde(rename = "ExpressionAttributeNames")]
    pub expression_attribute_names: Option<HashMap<String, String>>,
}

/// Transact get item wrapper
#[derive(Debug, Clone, Deserialize)]
pub struct TransactGetItem {
    #[serde(rename = "Get")]
    pub get: TransactGet,
}

/// Transact get items request
#[derive(Debug, Clone, Deserialize)]
pub struct TransactGetItemsRequest {
    #[serde(rename = "TransactItems")]
    pub transact_items: Vec<TransactGetItem>,
}

/// Item response for transact get
#[derive(Debug, Serialize, Default)]
pub struct ItemResponse {
    #[serde(skip_serializing_if = "Option::is_none", rename = "Item")]
    pub item: Option<Item>,
}

/// Transact get items response
#[derive(Debug, Serialize, Default)]
pub struct TransactGetItemsResponse {
    #[serde(rename = "Responses")]
    pub responses: Vec<ItemResponse>,
}

/// Transact put operation
#[derive(Debug, Clone, Deserialize)]
pub struct TransactPut {
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "Item")]
    pub item: Item,
    #[serde(rename = "ConditionExpression")]
    pub condition_expression: Option<String>,
}

/// Transact update operation
#[derive(Debug, Clone, Deserialize)]
pub struct TransactUpdate {
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "Key")]
    pub key: Item,
    #[serde(rename = "UpdateExpression")]
    pub update_expression: Option<String>,
}

/// Transact delete operation
#[derive(Debug, Clone, Deserialize)]
pub struct TransactDelete {
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "Key")]
    pub key: Item,
    #[serde(rename = "ConditionExpression")]
    pub condition_expression: Option<String>,
}

/// Transact condition check
#[derive(Debug, Clone, Deserialize)]
pub struct TransactConditionCheck {
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "Key")]
    pub key: Item,
    #[serde(rename = "ConditionExpression")]
    pub condition_expression: String,
}

// ============== Standalone ConditionCheck Operation ==============

/// ConditionCheck request (standalone operation)
#[derive(Debug, Clone, Deserialize)]
pub struct ConditionCheckRequest {
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "Key")]
    pub key: Item,
    #[serde(rename = "ConditionExpression")]
    pub condition_expression: String,
    #[serde(rename = "ExpressionAttributeNames", skip_serializing_if = "Option::is_none")]
    pub expression_attribute_names: Option<HashMap<String, String>>,
    #[serde(rename = "ExpressionAttributeValues", skip_serializing_if = "Option::is_none")]
    pub expression_attribute_values: Option<HashMap<String, AttributeValue>>,
}

/// ConditionCheck response (empty on success)
#[derive(Debug, Serialize, Default)]
pub struct ConditionCheckResponse {
}

/// Transact write item (one of put, update, delete, condition check)
#[derive(Debug, Clone, Deserialize)]
pub struct TransactWriteItem {
    #[serde(rename = "Put")]
    pub put: Option<TransactPut>,
    #[serde(rename = "Update")]
    pub update: Option<TransactUpdate>,
    #[serde(rename = "Delete")]
    pub delete: Option<TransactDelete>,
    #[serde(rename = "ConditionCheck")]
    pub condition_check: Option<TransactConditionCheck>,
}

/// Transact write items request
#[derive(Debug, Clone, Deserialize)]
pub struct TransactWriteItemsRequest {
    #[serde(rename = "TransactItems")]
    pub transact_items: Vec<TransactWriteItem>,
}

// ============== UpdateTable Operations ==============

/// Create global secondary index action
#[derive(Debug, Clone, Deserialize)]
pub struct CreateGlobalSecondaryIndexAction {
    #[serde(rename = "IndexName")]
    pub index_name: String,
    #[serde(rename = "KeySchema")]
    pub key_schema: Vec<KeySchemaElement>,
    #[serde(rename = "Projection")]
    pub projection: Projection,
    #[serde(rename = "ProvisionedThroughput")]
    pub provisioned_throughput: Option<ProvisionedThroughput>,
}

/// Update global secondary index action
#[derive(Debug, Clone, Deserialize)]
pub struct UpdateGlobalSecondaryIndexAction {
    #[serde(rename = "IndexName")]
    pub index_name: String,
    #[serde(rename = "ProvisionedThroughput")]
    pub provisioned_throughput: Option<ProvisionedThroughput>,
}

/// Delete global secondary index action
#[derive(Debug, Clone, Deserialize)]
pub struct DeleteGlobalSecondaryIndexAction {
    #[serde(rename = "IndexName")]
    pub index_name: String,
}

/// Global secondary index update
#[derive(Debug, Clone, Deserialize)]
pub struct GlobalSecondaryIndexUpdate {
    #[serde(rename = "Create")]
    pub create: Option<CreateGlobalSecondaryIndexAction>,
    #[serde(rename = "Update")]
    pub update: Option<UpdateGlobalSecondaryIndexAction>,
    #[serde(rename = "Delete")]
    pub delete: Option<DeleteGlobalSecondaryIndexAction>,
}

/// Update table request
#[derive(Debug, Clone, Deserialize)]
pub struct UpdateTableRequest {
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "AttributeDefinitions")]
    pub attribute_definitions: Option<Vec<AttributeDefinition>>,
    #[serde(rename = "BillingMode")]
    pub billing_mode: Option<String>,
    #[serde(rename = "GlobalSecondaryIndexUpdates")]
    pub global_secondary_index_updates: Option<Vec<GlobalSecondaryIndexUpdate>>,
    #[serde(rename = "ProvisionedThroughput")]
    pub provisioned_throughput: Option<ProvisionedThroughput>,
}

/// Update table response
#[derive(Debug, Serialize)]
pub struct UpdateTableResponse {
    #[serde(rename = "TableDescription")]
    pub table_description: TableMetadata,
}

// ============== Time To Live Operations ==============

/// Time to live specification for enabling/disabling TTL
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TimeToLiveSpecification {
    #[serde(rename = "Enabled")]
    pub enabled: bool,
    #[serde(rename = "AttributeName")]
    pub attribute_name: String,
}

/// Time to live description returned by DescribeTimeToLive and UpdateTimeToLive
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TimeToLiveDescription {
    #[serde(rename = "TimeToLiveStatus")]
    pub time_to_live_status: String,
    #[serde(rename = "AttributeName", skip_serializing_if = "Option::is_none")]
    pub attribute_name: Option<String>,
}

/// UpdateTimeToLive request
#[derive(Debug, Clone, Deserialize)]
pub struct UpdateTimeToLiveRequest {
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "TimeToLiveSpecification")]
    pub time_to_live_specification: TimeToLiveSpecification,
}

/// UpdateTimeToLive response
#[derive(Debug, Serialize)]
pub struct UpdateTimeToLiveResponse {
    #[serde(rename = "TimeToLiveDescription")]
    pub time_to_live_description: TimeToLiveDescription,
}

/// DescribeTimeToLive request
#[derive(Debug, Clone, Deserialize)]
pub struct DescribeTimeToLiveRequest {
    #[serde(rename = "TableName")]
    pub table_name: String,
}

/// DescribeTimeToLive response
#[derive(Debug, Serialize)]
pub struct DescribeTimeToLiveResponse {
    #[serde(rename = "TimeToLiveDescription")]
    pub time_to_live_description: TimeToLiveDescription,
}

// ============== Backup/Restore Operations ==============

/// Backup status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum BackupStatus {
    #[serde(rename = "CREATING")]
    Creating,
    #[serde(rename = "AVAILABLE")]
    Available,
    #[serde(rename = "DELETED")]
    Deleted,
}

impl std::fmt::Display for BackupStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            BackupStatus::Creating => write!(f, "CREATING"),
            BackupStatus::Available => write!(f, "AVAILABLE"),
            BackupStatus::Deleted => write!(f, "DELETED"),
        }
    }
}

/// Backup description
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BackupDescription {
    #[serde(rename = "BackupArn")]
    pub backup_arn: String,
    #[serde(rename = "BackupName")]
    pub backup_name: String,
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "TableArn")]
    pub table_arn: Option<String>,
    #[serde(rename = "BackupStatus")]
    pub backup_status: String,
    #[serde(rename = "BackupSizeBytes")]
    pub backup_size_bytes: i64,
    #[serde(rename = "BackupCreationDateTime")]
    pub backup_creation_date_time: DateTime<Utc>,
    #[serde(rename = "BackupExpiryDateTime", skip_serializing_if = "Option::is_none")]
    pub backup_expiry_date_time: Option<DateTime<Utc>>,
}

/// Backup summary for ListBackups
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BackupSummary {
    #[serde(rename = "BackupArn")]
    pub backup_arn: String,
    #[serde(rename = "BackupName")]
    pub backup_name: String,
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "BackupStatus")]
    pub backup_status: String,
    #[serde(rename = "BackupCreationDateTime")]
    pub backup_creation_date_time: DateTime<Utc>,
    #[serde(rename = "BackupSizeBytes", skip_serializing_if = "Option::is_none")]
    pub backup_size_bytes: Option<i64>,
}

/// CreateBackup request
#[derive(Debug, Clone, Deserialize)]
pub struct CreateBackupRequest {
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "BackupName")]
    pub backup_name: Option<String>,
}

/// CreateBackup response
#[derive(Debug, Serialize)]
pub struct CreateBackupResponse {
    #[serde(rename = "BackupDescription")]
    pub backup_description: BackupDescription,
}

/// DescribeBackup request
#[derive(Debug, Clone, Deserialize)]
pub struct DescribeBackupRequest {
    #[serde(rename = "BackupArn")]
    pub backup_arn: String,
}

/// DescribeBackup response
#[derive(Debug, Serialize)]
pub struct DescribeBackupResponse {
    #[serde(rename = "BackupDescription")]
    pub backup_description: BackupDescription,
}

/// ListBackups request
#[derive(Debug, Clone, Deserialize)]
pub struct ListBackupsRequest {
    #[serde(rename = "TableName")]
    pub table_name: Option<String>,
    #[serde(rename = "Limit")]
    pub limit: Option<i32>,
    #[serde(rename = "ExclusiveStartBackupArn")]
    pub exclusive_start_backup_arn: Option<String>,
}

/// ListBackups response
#[derive(Debug, Serialize)]
pub struct ListBackupsResponse {
    #[serde(rename = "BackupSummaries")]
    pub backup_summaries: Vec<BackupSummary>,
    #[serde(rename = "LastEvaluatedBackupArn", skip_serializing_if = "Option::is_none")]
    pub last_evaluated_backup_arn: Option<String>,
}

/// DeleteBackup request
#[derive(Debug, Clone, Deserialize)]
pub struct DeleteBackupRequest {
    #[serde(rename = "BackupArn")]
    pub backup_arn: String,
}

/// DeleteBackup response
#[derive(Debug, Serialize)]
pub struct DeleteBackupResponse {
    #[serde(rename = "BackupDescription")]
    pub backup_description: BackupDescription,
}

/// RestoreTableFromBackup request
#[derive(Debug, Clone, Deserialize)]
pub struct RestoreTableFromBackupRequest {
    #[serde(rename = "TargetTableName")]
    pub target_table_name: String,
    #[serde(rename = "BackupArn")]
    pub backup_arn: String,
}

/// RestoreTableFromBackup response
#[derive(Debug, Serialize)]
pub struct RestoreTableFromBackupResponse {
    #[serde(rename = "TableDescription")]
    pub table_description: TableMetadata,
}

/// Internal backup metadata stored in backups database
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackupMetadata {
    pub backup_id: String,
    pub backup_name: String,
    pub table_name: String,
    pub table_arn: Option<String>,
    pub backup_status: String,
    pub backup_size_bytes: i64,
    pub backup_creation_date_time: DateTime<Utc>,
    pub source_table_metadata: Option<TableMetadata>,
}

// ============== Point-in-Time Recovery (PITR) Operations ==============

/// Point-in-time recovery status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum PointInTimeRecoveryStatus {
    #[serde(rename = "ENABLING")]
    Enabling,
    #[serde(rename = "ENABLED")]
    Enabled,
    #[serde(rename = "DISABLING")]
    Disabling,
    #[serde(rename = "DISABLED")]
    Disabled,
}

impl std::fmt::Display for PointInTimeRecoveryStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PointInTimeRecoveryStatus::Enabling => write!(f, "ENABLING"),
            PointInTimeRecoveryStatus::Enabled => write!(f, "ENABLED"),
            PointInTimeRecoveryStatus::Disabling => write!(f, "DISABLING"),
            PointInTimeRecoveryStatus::Disabled => write!(f, "DISABLED"),
        }
    }
}

/// Point-in-time recovery description
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PointInTimeRecoveryDescription {
    #[serde(rename = "PointInTimeRecoveryStatus")]
    pub point_in_time_recovery_status: PointInTimeRecoveryStatus,
    #[serde(rename = "EarliestRestorableDateTime", skip_serializing_if = "Option::is_none")]
    pub earliest_restorable_date_time: Option<DateTime<Utc>>,
    #[serde(rename = "LatestRestorableDateTime", skip_serializing_if = "Option::is_none")]
    pub latest_restorable_date_time: Option<DateTime<Utc>>,
}

/// Continuous backups status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ContinuousBackupsStatus {
    #[serde(rename = "ENABLED")]
    Enabled,
    #[serde(rename = "DISABLED")]
    Disabled,
}

impl std::fmt::Display for ContinuousBackupsStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ContinuousBackupsStatus::Enabled => write!(f, "ENABLED"),
            ContinuousBackupsStatus::Disabled => write!(f, "DISABLED"),
        }
    }
}

/// Continuous backups description
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ContinuousBackupsDescription {
    #[serde(rename = "ContinuousBackupsStatus")]
    pub continuous_backups_status: ContinuousBackupsStatus,
    #[serde(rename = "PointInTimeRecoveryDescription", skip_serializing_if = "Option::is_none")]
    pub point_in_time_recovery_description: Option<PointInTimeRecoveryDescription>,
}

/// Point-in-time recovery specification
#[derive(Debug, Clone, Deserialize)]
pub struct PointInTimeRecoverySpecification {
    #[serde(rename = "PointInTimeRecoveryEnabled")]
    pub point_in_time_recovery_enabled: bool,
}

/// UpdateContinuousBackups request
#[derive(Debug, Clone, Deserialize)]
pub struct UpdateContinuousBackupsRequest {
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "PointInTimeRecoverySpecification")]
    pub point_in_time_recovery_specification: PointInTimeRecoverySpecification,
}

/// UpdateContinuousBackups response
#[derive(Debug, Serialize)]
pub struct UpdateContinuousBackupsResponse {
    #[serde(rename = "ContinuousBackupsDescription")]
    pub continuous_backups_description: ContinuousBackupsDescription,
}

/// DescribeContinuousBackups request
#[derive(Debug, Clone, Deserialize)]
pub struct DescribeContinuousBackupsRequest {
    #[serde(rename = "TableName")]
    pub table_name: String,
}

/// DescribeContinuousBackups response
#[derive(Debug, Serialize)]
pub struct DescribeContinuousBackupsResponse {
    #[serde(rename = "ContinuousBackupsDescription")]
    pub continuous_backups_description: ContinuousBackupsDescription,
}

/// RestoreTableToPointInTime request
#[derive(Debug, Clone, Deserialize)]
pub struct RestoreTableToPointInTimeRequest {
    #[serde(rename = "SourceTableName")]
    pub source_table_name: String,
    #[serde(rename = "TargetTableName")]
    pub target_table_name: String,
    #[serde(rename = "UseLatestRestorableTime", skip_serializing_if = "Option::is_none")]
    pub use_latest_restorable_time: Option<bool>,
    #[serde(rename = "RestoreDateTime", skip_serializing_if = "Option::is_none")]
    pub restore_date_time: Option<DateTime<Utc>>,
}

/// RestoreTableToPointInTime response
#[derive(Debug, Serialize)]
pub struct RestoreTableToPointInTimeResponse {
    #[serde(rename = "TableDescription")]
    pub table_description: TableMetadata,
}

/// Internal PITR configuration stored in table metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PitrConfiguration {
    pub enabled: bool,
    pub enabled_at: Option<DateTime<Utc>>,
}

// ============== PartiQL Operations ==============

/// A single PartiQL statement for batch execution
#[derive(Debug, Clone, Deserialize)]
pub struct PartiQLStatement {
    /// The PartiQL statement (e.g., "SELECT * FROM table WHERE pk = ?")
    #[serde(rename = "Statement")]
    pub statement: String,
    /// Optional parameters to substitute for ? placeholders
    #[serde(rename = "Parameters", skip_serializing_if = "Option::is_none")]
    pub parameters: Option<Vec<AttributeValue>>,
    /// Optional consistent read setting
    #[serde(rename = "ConsistentRead", skip_serializing_if = "Option::is_none")]
    pub consistent_read: Option<bool>,
}

/// Response for a single PartiQL statement in a batch
#[derive(Debug, Clone, Serialize, Default)]
pub struct PartiQLResponse {
    /// The item returned by INSERT or UPDATE (if ReturnValues was specified)
    #[serde(rename = "Item", skip_serializing_if = "Option::is_none")]
    pub item: Option<Item>,
    /// Items returned by SELECT
    #[serde(rename = "Items", skip_serializing_if = "Option::is_none")]
    pub items: Option<Vec<Item>>,
    /// Error if the statement failed
    #[serde(rename = "Error", skip_serializing_if = "Option::is_none")]
    pub error: Option<PartiQLError>,
}

/// PartiQL error details
#[derive(Debug, Clone, Serialize)]
pub struct PartiQLError {
    /// Error code
    #[serde(rename = "Code")]
    pub code: String,
    /// Error message
    #[serde(rename = "Message")]
    pub message: String,
}

/// ExecuteStatement request
#[derive(Debug, Clone, Deserialize)]
pub struct ExecuteStatementRequest {
    /// The PartiQL statement to execute
    #[serde(rename = "Statement")]
    pub statement: String,
    /// Optional parameters for ? placeholders
    #[serde(rename = "Parameters", skip_serializing_if = "Option::is_none")]
    pub parameters: Option<Vec<AttributeValue>>,
    /// Optional consistent read setting
    #[serde(rename = "ConsistentRead", skip_serializing_if = "Option::is_none")]
    pub consistent_read: Option<bool>,
    /// Optional next token for pagination
    #[serde(rename = "NextToken", skip_serializing_if = "Option::is_none")]
    pub next_token: Option<String>,
}

/// ExecuteStatement response
#[derive(Debug, Clone, Serialize, Default)]
pub struct ExecuteStatementResponse {
    /// Items returned by SELECT
    #[serde(rename = "Items", skip_serializing_if = "Option::is_none")]
    pub items: Option<Vec<Item>>,
    /// The item returned by INSERT or UPDATE
    #[serde(rename = "Item", skip_serializing_if = "Option::is_none")]
    pub item: Option<Item>,
    /// Next token for pagination
    #[serde(rename = "NextToken", skip_serializing_if = "Option::is_none")]
    pub next_token: Option<String>,
}

/// BatchExecuteStatement request
#[derive(Debug, Clone, Deserialize)]
pub struct BatchExecuteStatementRequest {
    /// List of PartiQL statements to execute
    #[serde(rename = "Statements")]
    pub statements: Vec<PartiQLStatement>,
}

/// BatchExecuteStatement response
#[derive(Debug, Clone, Serialize, Default)]
pub struct BatchExecuteStatementResponse {
    /// Responses for each statement
    #[serde(rename = "Responses")]
    pub responses: Vec<PartiQLResponse>,
}

// ============== Import/Export Operations ==============

/// Export format
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ExportFormat {
    #[serde(rename = "DYNAMODB_JSON")]
    DynamoDbJson,
}

impl Default for ExportFormat {
    fn default() -> Self {
        ExportFormat::DynamoDbJson
    }
}

/// Export status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ExportStatus {
    #[serde(rename = "IN_PROGRESS")]
    InProgress,
    #[serde(rename = "COMPLETED")]
    Completed,
    #[serde(rename = "FAILED")]
    Failed,
}

impl std::fmt::Display for ExportStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ExportStatus::InProgress => write!(f, "IN_PROGRESS"),
            ExportStatus::Completed => write!(f, "COMPLETED"),
            ExportStatus::Failed => write!(f, "FAILED"),
        }
    }
}

/// Import status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ImportStatus {
    #[serde(rename = "IN_PROGRESS")]
    InProgress,
    #[serde(rename = "COMPLETED")]
    Completed,
    #[serde(rename = "FAILED")]
    Failed,
    #[serde(rename = "CANCELLED")]
    Cancelled,
}

impl std::fmt::Display for ImportStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ImportStatus::InProgress => write!(f, "IN_PROGRESS"),
            ImportStatus::Completed => write!(f, "COMPLETED"),
            ImportStatus::Failed => write!(f, "FAILED"),
            ImportStatus::Cancelled => write!(f, "CANCELLED"),
        }
    }
}

/// Export description
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ExportDescription {
    #[serde(rename = "ExportArn")]
    pub export_arn: String,
    #[serde(rename = "ExportStatus")]
    pub export_status: String,
    #[serde(rename = "TableArn", skip_serializing_if = "Option::is_none")]
    pub table_arn: Option<String>,
    #[serde(rename = "S3Bucket")]
    pub s3_bucket: String,
    #[serde(rename = "S3Prefix", skip_serializing_if = "Option::is_none")]
    pub s3_prefix: Option<String>,
    #[serde(rename = "ExportFormat")]
    pub export_format: String,
    #[serde(rename = "ItemCount", skip_serializing_if = "Option::is_none")]
    pub item_count: Option<i64>,
    #[serde(rename = "ExportTime", skip_serializing_if = "Option::is_none")]
    pub export_time: Option<DateTime<Utc>>,
    #[serde(rename = "StartTime", skip_serializing_if = "Option::is_none")]
    pub start_time: Option<DateTime<Utc>>,
    #[serde(rename = "EndTime", skip_serializing_if = "Option::is_none")]
    pub end_time: Option<DateTime<Utc>>,
    #[serde(rename = "FailureCode", skip_serializing_if = "Option::is_none")]
    pub failure_code: Option<String>,
    #[serde(rename = "FailureMessage", skip_serializing_if = "Option::is_none")]
    pub failure_message: Option<String>,
}

/// Import description
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ImportDescription {
    #[serde(rename = "ImportArn")]
    pub import_arn: String,
    #[serde(rename = "ImportStatus")]
    pub import_status: String,
    #[serde(rename = "TableArn", skip_serializing_if = "Option::is_none")]
    pub table_arn: Option<String>,
    #[serde(rename = "S3BucketSource")]
    pub s3_bucket_source: S3BucketSource,
    #[serde(rename = "InputFormat")]
    pub input_format: String,
    #[serde(rename = "ProcessedItemCount", skip_serializing_if = "Option::is_none")]
    pub processed_item_count: Option<i64>,
    #[serde(rename = "ImportedItemCount", skip_serializing_if = "Option::is_none")]
    pub imported_item_count: Option<i64>,
    #[serde(rename = "ErrorCount", skip_serializing_if = "Option::is_none")]
    pub error_count: Option<i64>,
    #[serde(rename = "StartTime", skip_serializing_if = "Option::is_none")]
    pub start_time: Option<DateTime<Utc>>,
    #[serde(rename = "EndTime", skip_serializing_if = "Option::is_none")]
    pub end_time: Option<DateTime<Utc>>,
    #[serde(rename = "FailureCode", skip_serializing_if = "Option::is_none")]
    pub failure_code: Option<String>,
    #[serde(rename = "FailureMessage", skip_serializing_if = "Option::is_none")]
    pub failure_message: Option<String>,
}

/// S3 bucket source for import
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct S3BucketSource {
    #[serde(rename = "S3Bucket")]
    pub s3_bucket: String,
    #[serde(rename = "S3KeyPrefix", skip_serializing_if = "Option::is_none")]
    pub s3_key_prefix: Option<String>,
}

/// Export summary for ListExports
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ExportSummary {
    #[serde(rename = "ExportArn")]
    pub export_arn: String,
    #[serde(rename = "ExportStatus")]
    pub export_status: String,
    #[serde(rename = "TableArn", skip_serializing_if = "Option::is_none")]
    pub table_arn: Option<String>,
}

/// Import summary for ListImports
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ImportSummary {
    #[serde(rename = "ImportArn")]
    pub import_arn: String,
    #[serde(rename = "ImportStatus")]
    pub import_status: String,
    #[serde(rename = "TableArn", skip_serializing_if = "Option::is_none")]
    pub table_arn: Option<String>,
}

/// ExportTableToPointInTime request
#[derive(Debug, Clone, Deserialize)]
pub struct ExportTableToPointInTimeRequest {
    #[serde(rename = "TableArn")]
    pub table_arn: String,
    #[serde(rename = "S3Bucket")]
    pub s3_bucket: String,
    #[serde(rename = "S3Prefix", skip_serializing_if = "Option::is_none")]
    pub s3_prefix: Option<String>,
    #[serde(rename = "ExportFormat", skip_serializing_if = "Option::is_none")]
    pub export_format: Option<String>,
}

/// ExportTableToPointInTime response
#[derive(Debug, Serialize)]
pub struct ExportTableToPointInTimeResponse {
    #[serde(rename = "ExportDescription")]
    pub export_description: ExportDescription,
}

/// DescribeExport request
#[derive(Debug, Clone, Deserialize)]
pub struct DescribeExportRequest {
    #[serde(rename = "ExportArn")]
    pub export_arn: String,
}

/// DescribeExport response
#[derive(Debug, Serialize)]
pub struct DescribeExportResponse {
    #[serde(rename = "ExportDescription")]
    pub export_description: ExportDescription,
}

/// ListExports request
#[derive(Debug, Clone, Deserialize)]
pub struct ListExportsRequest {
    #[serde(rename = "MaxResults", skip_serializing_if = "Option::is_none")]
    pub max_results: Option<i32>,
    #[serde(rename = "NextToken", skip_serializing_if = "Option::is_none")]
    pub next_token: Option<String>,
    #[serde(rename = "TableArn", skip_serializing_if = "Option::is_none")]
    pub table_arn: Option<String>,
}

/// ListExports response
#[derive(Debug, Serialize)]
pub struct ListExportsResponse {
    #[serde(rename = "ExportSummaries")]
    pub export_summaries: Vec<ExportSummary>,
    #[serde(rename = "NextToken", skip_serializing_if = "Option::is_none")]
    pub next_token: Option<String>,
}

/// ImportTable request
#[derive(Debug, Clone, Deserialize)]
pub struct ImportTableRequest {
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "S3BucketSource")]
    pub s3_bucket_source: S3BucketSource,
    #[serde(rename = "InputFormat", skip_serializing_if = "Option::is_none")]
    pub input_format: Option<String>,
    #[serde(rename = "KeySchema", skip_serializing_if = "Option::is_none")]
    pub key_schema: Option<Vec<KeySchemaElement>>,
    #[serde(rename = "AttributeDefinitions", skip_serializing_if = "Option::is_none")]
    pub attribute_definitions: Option<Vec<AttributeDefinition>>,
}

/// ImportTable response
#[derive(Debug, Serialize)]
pub struct ImportTableResponse {
    #[serde(rename = "ImportDescription")]
    pub import_description: ImportDescription,
}

/// DescribeImport request
#[derive(Debug, Clone, Deserialize)]
pub struct DescribeImportRequest {
    #[serde(rename = "ImportArn")]
    pub import_arn: String,
}

/// DescribeImport response
#[derive(Debug, Serialize)]
pub struct DescribeImportResponse {
    #[serde(rename = "ImportDescription")]
    pub import_description: ImportDescription,
}

/// ListImports request
#[derive(Debug, Clone, Deserialize)]
pub struct ListImportsRequest {
    #[serde(rename = "MaxResults", skip_serializing_if = "Option::is_none")]
    pub max_results: Option<i32>,
    #[serde(rename = "NextToken", skip_serializing_if = "Option::is_none")]
    pub next_token: Option<String>,
    #[serde(rename = "TableArn", skip_serializing_if = "Option::is_none")]
    pub table_arn: Option<String>,
}

/// ListImports response
#[derive(Debug, Serialize)]
pub struct ListImportsResponse {
    #[serde(rename = "ImportSummaries")]
    pub import_summaries: Vec<ImportSummary>,
    #[serde(rename = "NextToken", skip_serializing_if = "Option::is_none")]
    pub next_token: Option<String>,
}

/// Internal export metadata stored in database
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExportMetadata {
    pub export_id: String,
    pub export_arn: String,
    pub export_status: String,
    pub table_arn: Option<String>,
    pub table_name: String,
    pub s3_bucket: String,
    pub s3_prefix: Option<String>,
    pub export_format: String,
    pub item_count: i64,
    pub start_time: DateTime<Utc>,
    pub end_time: Option<DateTime<Utc>>,
    pub failure_code: Option<String>,
    pub failure_message: Option<String>,
}

/// Internal import metadata stored in database
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImportMetadata {
    pub import_id: String,
    pub import_arn: String,
    pub import_status: String,
    pub table_arn: Option<String>,
    pub table_name: String,
    pub s3_bucket: String,
    pub s3_key_prefix: Option<String>,
    pub input_format: String,
    pub processed_item_count: i64,
    pub imported_item_count: i64,
    pub error_count: i64,
    pub start_time: DateTime<Utc>,
    pub end_time: Option<DateTime<Utc>>,
    pub failure_code: Option<String>,
    pub failure_message: Option<String>,
}

// ============== DynamoDB Streams Operations ==============

/// Stream status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum StreamStatus {
    #[serde(rename = "ENABLING")]
    Enabling,
    #[serde(rename = "ENABLED")]
    Enabled,
    #[serde(rename = "DISABLING")]
    Disabling,
    #[serde(rename = "DISABLED")]
    Disabled,
}

impl std::fmt::Display for StreamStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            StreamStatus::Enabling => write!(f, "ENABLING"),
            StreamStatus::Enabled => write!(f, "ENABLED"),
            StreamStatus::Disabling => write!(f, "DISABLING"),
            StreamStatus::Disabled => write!(f, "DISABLED"),
        }
    }
}

/// Stream view type - determines what data is captured in stream records
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum StreamViewType {
    #[serde(rename = "NEW_IMAGE")]
    NewImage,
    #[serde(rename = "OLD_IMAGE")]
    OldImage,
    #[serde(rename = "NEW_AND_OLD_IMAGES")]
    NewAndOldImages,
    #[serde(rename = "KEYS_ONLY")]
    KeysOnly,
}

impl std::fmt::Display for StreamViewType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            StreamViewType::NewImage => write!(f, "NEW_IMAGE"),
            StreamViewType::OldImage => write!(f, "OLD_IMAGE"),
            StreamViewType::NewAndOldImages => write!(f, "NEW_AND_OLD_IMAGES"),
            StreamViewType::KeysOnly => write!(f, "KEYS_ONLY"),
        }
    }
}

/// Stream specification for creating/updating tables with streams
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct StreamSpecification {
    #[serde(rename = "StreamEnabled")]
    pub stream_enabled: bool,
    #[serde(rename = "StreamViewType")]
    pub stream_view_type: Option<StreamViewType>,
}

/// Stream record summary (used in ListStreams response)
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Stream {
    #[serde(rename = "StreamArn")]
    pub stream_arn: String,
    #[serde(rename = "StreamLabel")]
    pub stream_label: String,
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "StreamStatus")]
    pub stream_status: String,
}

/// Sequence number range for a shard
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SequenceNumberRange {
    #[serde(rename = "StartingSequenceNumber")]
    pub starting_sequence_number: String,
    #[serde(rename = "EndingSequenceNumber", skip_serializing_if = "Option::is_none")]
    pub ending_sequence_number: Option<String>,
}

/// Shard - a partition of a stream
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Shard {
    #[serde(rename = "ShardId")]
    pub shard_id: String,
    #[serde(rename = "ParentShardId", skip_serializing_if = "Option::is_none")]
    pub parent_shard_id: Option<String>,
    #[serde(rename = "SequenceNumberRange")]
    pub sequence_number_range: SequenceNumberRange,
}

/// Stream description
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct StreamDescription {
    #[serde(rename = "StreamArn")]
    pub stream_arn: String,
    #[serde(rename = "StreamLabel")]
    pub stream_label: String,
    #[serde(rename = "TableName")]
    pub table_name: String,
    #[serde(rename = "StreamStatus")]
    pub stream_status: String,
    #[serde(rename = "StreamViewType")]
    pub stream_view_type: StreamViewType,
    #[serde(rename = "CreationDateTime")]
    pub creation_date_time: DateTime<Utc>,
    #[serde(rename = "Shards", skip_serializing_if = "Option::is_none")]
    pub shards: Option<Vec<Shard>>,
}

/// Stream record data (the DynamoDB portion)
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct StreamRecord {
    #[serde(rename = "ApproximateCreationDateTime")]
    pub approximate_creation_date_time: DateTime<Utc>,
    #[serde(rename = "Keys")]
    pub keys: Item,
    #[serde(rename = "NewImage", skip_serializing_if = "Option::is_none")]
    pub new_image: Option<Item>,
    #[serde(rename = "OldImage", skip_serializing_if = "Option::is_none")]
    pub old_image: Option<Item>,
    #[serde(rename = "SequenceNumber")]
    pub sequence_number: String,
    #[serde(rename = "SizeBytes")]
    pub size_bytes: i64,
    #[serde(rename = "StreamViewType")]
    pub stream_view_type: StreamViewType,
}

/// Stream record wrapper (includes metadata)
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Record {
    #[serde(rename = "eventID")]
    pub event_id: String,
    #[serde(rename = "eventName")]
    pub event_name: String, // INSERT, MODIFY, REMOVE
    #[serde(rename = "eventVersion")]
    pub event_version: String,
    #[serde(rename = "awsRegion")]
    pub aws_region: String,
    #[serde(rename = "dynamodb")]
    pub dynamodb: StreamRecord,
    #[serde(rename = "eventSource")]
    pub event_source: String,
}

/// Shard iterator type
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ShardIteratorType {
    #[serde(rename = "TRIM_HORIZON")]
    TrimHorizon,
    #[serde(rename = "LATEST")]
    Latest,
    #[serde(rename = "AT_SEQUENCE_NUMBER")]
    AtSequenceNumber,
    #[serde(rename = "AFTER_SEQUENCE_NUMBER")]
    AfterSequenceNumber,
    #[serde(rename = "AT_TIMESTAMP")]
    AtTimestamp,
}

/// ListStreams request
#[derive(Debug, Clone, Deserialize)]
pub struct ListStreamsRequest {
    #[serde(rename = "TableName", skip_serializing_if = "Option::is_none")]
    pub table_name: Option<String>,
    #[serde(rename = "ExclusiveStartStreamArn", skip_serializing_if = "Option::is_none")]
    pub exclusive_start_stream_arn: Option<String>,
    #[serde(rename = "Limit", skip_serializing_if = "Option::is_none")]
    pub limit: Option<i32>,
}

/// ListStreams response
#[derive(Debug, Serialize)]
pub struct ListStreamsResponse {
    #[serde(rename = "Streams")]
    pub streams: Vec<Stream>,
    #[serde(rename = "LastEvaluatedStreamArn", skip_serializing_if = "Option::is_none")]
    pub last_evaluated_stream_arn: Option<String>,
}

/// DescribeStream request
#[derive(Debug, Clone, Deserialize)]
pub struct DescribeStreamRequest {
    #[serde(rename = "StreamArn")]
    pub stream_arn: String,
    #[serde(rename = "ExclusiveStartShardId", skip_serializing_if = "Option::is_none")]
    pub exclusive_start_shard_id: Option<String>,
    #[serde(rename = "Limit", skip_serializing_if = "Option::is_none")]
    pub limit: Option<i32>,
}

/// DescribeStream response
#[derive(Debug, Serialize)]
pub struct DescribeStreamResponse {
    #[serde(rename = "StreamDescription")]
    pub stream_description: StreamDescription,
}

/// GetShardIterator request
#[derive(Debug, Clone, Deserialize)]
pub struct GetShardIteratorRequest {
    #[serde(rename = "StreamArn")]
    pub stream_arn: String,
    #[serde(rename = "ShardId")]
    pub shard_id: String,
    #[serde(rename = "ShardIteratorType")]
    pub shard_iterator_type: ShardIteratorType,
    #[serde(rename = "SequenceNumber", skip_serializing_if = "Option::is_none")]
    pub sequence_number: Option<String>,
    #[serde(rename = "Timestamp", skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<DateTime<Utc>>,
}

/// GetShardIterator response
#[derive(Debug, Serialize)]
pub struct GetShardIteratorResponse {
    #[serde(rename = "ShardIterator", skip_serializing_if = "Option::is_none")]
    pub shard_iterator: Option<String>,
}

/// GetRecords request
#[derive(Debug, Clone, Deserialize)]
pub struct GetRecordsRequest {
    #[serde(rename = "ShardIterator")]
    pub shard_iterator: String,
    #[serde(rename = "Limit", skip_serializing_if = "Option::is_none")]
    pub limit: Option<i32>,
}

/// GetRecords response
#[derive(Debug, Serialize)]
pub struct GetRecordsResponse {
    #[serde(rename = "Records")]
    pub records: Vec<Record>,
    #[serde(rename = "NextShardIterator", skip_serializing_if = "Option::is_none")]
    pub next_shard_iterator: Option<String>,
}

/// Internal stream metadata stored in table metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamMetadata {
    pub stream_arn: String,
    pub stream_label: String,
    pub table_name: String,
    pub stream_status: String,
    pub stream_view_type: StreamViewType,
    pub creation_date_time: DateTime<Utc>,
}

/// Internal stream record stored in database
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamRecordInternal {
    pub sequence_number: String,
    pub event_id: String,
    pub event_name: String,
    pub table_name: String,
    pub stream_view_type: StreamViewType,
    pub approximate_creation_date_time: DateTime<Utc>,
    pub keys: Item,
    pub new_image: Option<Item>,
    pub old_image: Option<Item>,
    pub size_bytes: i64,
}

// ============== Global Tables Operations ==============

/// Global table status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum GlobalTableStatus {
    #[serde(rename = "CREATING")]
    Creating,
    #[serde(rename = "ACTIVE")]
    Active,
    #[serde(rename = "DELETING")]
    Deleting,
    #[serde(rename = "UPDATING")]
    Updating,
}

impl std::fmt::Display for GlobalTableStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            GlobalTableStatus::Creating => write!(f, "CREATING"),
            GlobalTableStatus::Active => write!(f, "ACTIVE"),
            GlobalTableStatus::Deleting => write!(f, "DELETING"),
            GlobalTableStatus::Updating => write!(f, "UPDATING"),
        }
    }
}

/// Replica status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ReplicaStatus {
    #[serde(rename = "CREATING")]
    Creating,
    #[serde(rename = "CREATION_FAILED")]
    CreationFailed,
    #[serde(rename = "ACTIVE")]
    Active,
    #[serde(rename = "DELETING")]
    Deleting,
    #[serde(rename = "DELETION_FAILED")]
    DeletionFailed,
}

impl std::fmt::Display for ReplicaStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ReplicaStatus::Creating => write!(f, "CREATING"),
            ReplicaStatus::CreationFailed => write!(f, "CREATION_FAILED"),
            ReplicaStatus::Active => write!(f, "ACTIVE"),
            ReplicaStatus::Deleting => write!(f, "DELETING"),
            ReplicaStatus::DeletionFailed => write!(f, "DELETION_FAILED"),
        }
    }
}

/// Replica definition (for create/update)
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Replica {
    #[serde(rename = "RegionName")]
    pub region_name: String,
}

/// Replica description (for describe/list responses)
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ReplicaDescription {
    #[serde(rename = "RegionName")]
    pub region_name: String,
    #[serde(rename = "ReplicaStatus")]
    pub replica_status: String,
    #[serde(rename = "KMSMasterKeyId", skip_serializing_if = "Option::is_none")]
    pub kms_master_key_id: Option<String>,
}

/// Global table (simplified representation)
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GlobalTable {
    #[serde(rename = "GlobalTableName")]
    pub global_table_name: String,
    #[serde(rename = "ReplicationGroup")]
    pub replication_group: Vec<Replica>,
}

/// Global table description
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GlobalTableDescription {
    #[serde(rename = "GlobalTableName")]
    pub global_table_name: String,
    #[serde(rename = "GlobalTableStatus")]
    pub global_table_status: String,
    #[serde(rename = "GlobalTableArn", skip_serializing_if = "Option::is_none")]
    pub global_table_arn: Option<String>,
    #[serde(rename = "CreationDateTime")]
    pub creation_date_time: DateTime<Utc>,
    #[serde(rename = "ReplicationGroup")]
    pub replication_group: Vec<ReplicaDescription>,
}

/// CreateGlobalTable request
#[derive(Debug, Clone, Deserialize)]
pub struct CreateGlobalTableRequest {
    #[serde(rename = "GlobalTableName")]
    pub global_table_name: String,
    #[serde(rename = "ReplicationGroup")]
    pub replication_group: Vec<Replica>,
}

/// CreateGlobalTable response
#[derive(Debug, Serialize)]
pub struct CreateGlobalTableResponse {
    #[serde(rename = "GlobalTableDescription")]
    pub global_table_description: GlobalTableDescription,
}

/// UpdateGlobalTable request
#[derive(Debug, Clone, Deserialize)]
pub struct UpdateGlobalTableRequest {
    #[serde(rename = "GlobalTableName")]
    pub global_table_name: String,
    #[serde(rename = "ReplicaUpdates")]
    pub replica_updates: Vec<ReplicaUpdate>,
}

/// UpdateGlobalTable response
#[derive(Debug, Serialize)]
pub struct UpdateGlobalTableResponse {
    #[serde(rename = "GlobalTableDescription")]
    pub global_table_description: GlobalTableDescription,
}

/// DescribeGlobalTable request
#[derive(Debug, Clone, Deserialize)]
pub struct DescribeGlobalTableRequest {
    #[serde(rename = "GlobalTableName")]
    pub global_table_name: String,
}

/// DescribeGlobalTable response
#[derive(Debug, Serialize)]
pub struct DescribeGlobalTableResponse {
    #[serde(rename = "GlobalTableDescription")]
    pub global_table_description: GlobalTableDescription,
}

/// ListGlobalTables request
#[derive(Debug, Clone, Deserialize)]
pub struct ListGlobalTablesRequest {
    #[serde(rename = "ExclusiveStartGlobalTableName", skip_serializing_if = "Option::is_none")]
    pub exclusive_start_global_table_name: Option<String>,
    #[serde(rename = "Limit", skip_serializing_if = "Option::is_none")]
    pub limit: Option<i32>,
}

/// Global table summary for ListGlobalTables
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GlobalTableSummary {
    #[serde(rename = "GlobalTableName")]
    pub global_table_name: String,
    #[serde(rename = "ReplicationGroup")]
    pub replication_group: Vec<Replica>,
}

/// ListGlobalTables response
#[derive(Debug, Serialize)]
pub struct ListGlobalTablesResponse {
    #[serde(rename = "GlobalTables")]
    pub global_tables: Vec<GlobalTableSummary>,
    #[serde(rename = "LastEvaluatedGlobalTableName", skip_serializing_if = "Option::is_none")]
    pub last_evaluated_global_table_name: Option<String>,
}

/// DeleteGlobalTable request
#[derive(Debug, Clone, Deserialize)]
pub struct DeleteGlobalTableRequest {
    #[serde(rename = "GlobalTableName")]
    pub global_table_name: String,
}

/// DeleteGlobalTable response
#[derive(Debug, Serialize)]
pub struct DeleteGlobalTableResponse {
    #[serde(rename = "GlobalTableDescription")]
    pub global_table_description: GlobalTableDescription,
}

/// UpdateGlobalTableSettings request
#[derive(Debug, Clone, Deserialize)]
pub struct UpdateGlobalTableSettingsRequest {
    #[serde(rename = "GlobalTableName")]
    pub global_table_name: String,
    #[serde(rename = "GlobalTableBillingMode", skip_serializing_if = "Option::is_none")]
    pub global_table_billing_mode: Option<String>,
    #[serde(rename = "GlobalTableProvisionedWriteCapacityUnits", skip_serializing_if = "Option::is_none")]
    pub global_table_provisioned_write_capacity: Option<i64>,
    #[serde(rename = "GlobalTableProvisionedReadCapacityUnits", skip_serializing_if = "Option::is_none")]
    pub global_table_provisioned_read_capacity: Option<i64>,
}

/// UpdateGlobalTableSettings response
#[derive(Debug, Serialize)]
pub struct UpdateGlobalTableSettingsResponse {
    #[serde(rename = "GlobalTableDescription")]
    pub global_table_description: GlobalTableDescription,
}

/// Replica settings description for DescribeGlobalTableSettings
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ReplicaSettingsDescription {
    #[serde(rename = "RegionName")]
    pub region_name: String,
    #[serde(rename = "ReplicaStatus")]
    pub replica_status: String,
    #[serde(rename = "ReplicaBillingModeSummary", skip_serializing_if = "Option::is_none")]
    pub replica_billing_mode_summary: Option<BillingModeSummary>,
    #[serde(rename = "ReplicaProvisionedReadCapacityUnits", skip_serializing_if = "Option::is_none")]
    pub replica_provisioned_read_capacity: Option<i64>,
    #[serde(rename = "ReplicaProvisionedWriteCapacityUnits", skip_serializing_if = "Option::is_none")]
    pub replica_provisioned_write_capacity: Option<i64>,
}

/// DescribeGlobalTableSettings request
#[derive(Debug, Clone, Deserialize)]
pub struct DescribeGlobalTableSettingsRequest {
    #[serde(rename = "GlobalTableName")]
    pub global_table_name: String,
}

/// DescribeGlobalTableSettings response
#[derive(Debug, Serialize)]
pub struct DescribeGlobalTableSettingsResponse {
    #[serde(rename = "GlobalTableName")]
    pub global_table_name: String,
    #[serde(rename = "ReplicaSettings")]
    pub replica_settings: Vec<ReplicaSettingsDescription>,
}

/// Replica update for UpdateReplication
#[derive(Debug, Clone, Deserialize)]
pub struct ReplicaUpdateForReplication {
    #[serde(rename = "Create", skip_serializing_if = "Option::is_none")]
    pub create: Option<CreateReplicaAction>,
    #[serde(rename = "Delete", skip_serializing_if = "Option::is_none")]
    pub delete: Option<DeleteReplicaAction>,
    #[serde(rename = "Update", skip_serializing_if = "Option::is_none")]
    pub update: Option<UpdateReplicaAction>,
}

/// Update replica action
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct UpdateReplicaAction {
    #[serde(rename = "RegionName")]
    pub region_name: String,
    #[serde(rename = "KMSMasterKeyId", skip_serializing_if = "Option::is_none")]
    pub kms_master_key_id: Option<String>,
}

/// UpdateReplication request
#[derive(Debug, Clone, Deserialize)]
pub struct UpdateReplicationRequest {
    #[serde(rename = "GlobalTableName")]
    pub global_table_name: String,
    #[serde(rename = "ReplicaUpdates")]
    pub replica_updates: Vec<ReplicaUpdateForReplication>,
}

/// UpdateReplication response
#[derive(Debug, Serialize)]
pub struct UpdateReplicationResponse {
    #[serde(rename = "GlobalTableDescription")]
    pub global_table_description: GlobalTableDescription,
}

/// DescribeLimits request (empty - no parameters)
#[derive(Debug, Clone, Deserialize)]
pub struct DescribeLimitsRequest {}

/// DescribeLimits response
#[derive(Debug, Serialize)]
pub struct DescribeLimitsResponse {
    #[serde(rename = "AccountMaxReadCapacityUnits")]
    pub account_max_read_capacity_units: i64,
    #[serde(rename = "AccountMaxWriteCapacityUnits")]
    pub account_max_write_capacity_units: i64,
    #[serde(rename = "TableMaxReadCapacityUnits")]
    pub table_max_read_capacity_units: i64,
    #[serde(rename = "TableMaxWriteCapacityUnits")]
    pub table_max_write_capacity_units: i64,
}

impl Default for DescribeLimitsResponse {
    fn default() -> Self {
        Self {
            account_max_read_capacity_units: 100000,
            account_max_write_capacity_units: 100000,
            table_max_read_capacity_units: 100000,
            table_max_write_capacity_units: 100000,
        }
    }
}

/// Replica update for UpdateGlobalTable
#[derive(Debug, Clone, Deserialize)]
pub struct ReplicaUpdate {
    #[serde(rename = "Create", skip_serializing_if = "Option::is_none")]
    pub create: Option<CreateReplicaAction>,
    #[serde(rename = "Delete", skip_serializing_if = "Option::is_none")]
    pub delete: Option<DeleteReplicaAction>,
}

/// Create replica action
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CreateReplicaAction {
    #[serde(rename = "RegionName")]
    pub region_name: String,
}

/// Delete replica action
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DeleteReplicaAction {
    #[serde(rename = "RegionName")]
    pub region_name: String,
}

/// Internal global table metadata stored in database
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GlobalTableMetadata {
    pub global_table_id: String,
    pub global_table_name: String,
    pub global_table_arn: String,
    pub global_table_status: String,
    pub creation_date_time: DateTime<Utc>,
    pub replicas: Vec<ReplicaDescription>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_attribute_value_creation() {
        let s = AttributeValue::s("test");
        assert_eq!(s.as_s(), Some("test"));

        let n = AttributeValue::n("123");
        assert_eq!(n.as_n(), Some("123"));

        let b = AttributeValue::bool(true);
        assert_eq!(b.as_bool(), Some(true));

        let null = AttributeValue::null();
        assert!(null.is_null());
    }

    #[test]
    fn test_attribute_value_serialization() {
        let attr = AttributeValue::s("hello");
        let json = serde_json::to_string(&attr).unwrap();
        assert!(json.contains("\"s\":\"hello\""));
    }

    #[test]
    fn test_key_schema_element() {
        let hash = KeySchemaElement::hash("pk");
        assert_eq!(hash.attribute_name, "pk");
        assert_eq!(hash.key_type, "HASH");

        let range = KeySchemaElement::range("sk");
        assert_eq!(range.attribute_name, "sk");
        assert_eq!(range.key_type, "RANGE");
    }

    #[test]
    fn test_error_response() {
        let err = ErrorResponse::validation_exception("test error");
        assert!(err.error_type.contains("ValidationException"));
        assert_eq!(err.message, "test error");
    }
}
