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

    // Time to live fields
    #[serde(skip_serializing_if = "Option::is_none", rename = "TimeToLiveDescription")]
    pub time_to_live_description: Option<TimeToLiveDescription>,
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
