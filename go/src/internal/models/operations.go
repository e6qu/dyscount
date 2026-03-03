// Package models provides DynamoDB-compatible data models.
package models

// GetItemRequest represents a DynamoDB GetItem request.
type GetItemRequest struct {
	TableName                string              `json:"TableName" binding:"required"`
	Key                      Item                `json:"Key" binding:"required"`
	AttributesToGet          []string            `json:"AttributesToGet,omitempty"`
	ConsistentRead           bool                `json:"ConsistentRead,omitempty"`
	ExpressionAttributeNames map[string]string   `json:"ExpressionAttributeNames,omitempty"`
	ProjectionExpression     string              `json:"ProjectionExpression,omitempty"`
	ReturnConsumedCapacity   string              `json:"ReturnConsumedCapacity,omitempty"`
}

// GetItemResponse represents a DynamoDB GetItem response.
type GetItemResponse struct {
	Item             Item              `json:"Item,omitempty"`
	ConsumedCapacity *ConsumedCapacity `json:"ConsumedCapacity,omitempty"`
}

// PutItemRequest represents a DynamoDB PutItem request.
type PutItemRequest struct {
	TableName                   string              `json:"TableName" binding:"required"`
	Item                        Item                `json:"Item" binding:"required"`
	ConditionExpression         string              `json:"ConditionExpression,omitempty"`
	ConditionalOperator         string              `json:"ConditionalOperator,omitempty"`
	Expected                    map[string]ExpectedAttributeValue `json:"Expected,omitempty"`
	ExpressionAttributeNames    map[string]string   `json:"ExpressionAttributeNames,omitempty"`
	ExpressionAttributeValues   map[string]AttributeValue `json:"ExpressionAttributeValues,omitempty"`
	ReturnConsumedCapacity      string              `json:"ReturnConsumedCapacity,omitempty"`
	ReturnItemCollectionMetrics string              `json:"ReturnItemCollectionMetrics,omitempty"`
	ReturnValues                string              `json:"ReturnValues,omitempty"` // NONE, ALL_OLD, UPDATED_OLD, ALL_NEW, UPDATED_NEW
}

// PutItemResponse represents a DynamoDB PutItem response.
type PutItemResponse struct {
	Attributes       Item              `json:"Attributes,omitempty"`
	ConsumedCapacity *ConsumedCapacity `json:"ConsumedCapacity,omitempty"`
	ItemCollectionMetrics *ItemCollectionMetrics `json:"ItemCollectionMetrics,omitempty"`
}

// UpdateItemRequest represents a DynamoDB UpdateItem request.
type UpdateItemRequest struct {
	TableName                   string              `json:"TableName" binding:"required"`
	Key                         Item                `json:"Key" binding:"required"`
	AttributeUpdates            map[string]AttributeUpdate `json:"AttributeUpdates,omitempty"`
	ConditionExpression         string              `json:"ConditionExpression,omitempty"`
	ConditionalOperator         string              `json:"ConditionalOperator,omitempty"`
	Expected                    map[string]ExpectedAttributeValue `json:"Expected,omitempty"`
	ExpressionAttributeNames    map[string]string   `json:"ExpressionAttributeNames,omitempty"`
	ExpressionAttributeValues   map[string]AttributeValue `json:"ExpressionAttributeValues,omitempty"`
	ReturnConsumedCapacity      string              `json:"ReturnConsumedCapacity,omitempty"`
	ReturnItemCollectionMetrics string              `json:"ReturnItemCollectionMetrics,omitempty"`
	ReturnValues                string              `json:"ReturnValues,omitempty"`
	UpdateExpression            string              `json:"UpdateExpression,omitempty"`
}

// UpdateItemResponse represents a DynamoDB UpdateItem response.
type UpdateItemResponse struct {
	Attributes       Item              `json:"Attributes,omitempty"`
	ConsumedCapacity *ConsumedCapacity `json:"ConsumedCapacity,omitempty"`
	ItemCollectionMetrics *ItemCollectionMetrics `json:"ItemCollectionMetrics,omitempty"`
}

// DeleteItemRequest represents a DynamoDB DeleteItem request.
type DeleteItemRequest struct {
	TableName                   string              `json:"TableName" binding:"required"`
	Key                         Item                `json:"Key" binding:"required"`
	ConditionExpression         string              `json:"ConditionExpression,omitempty"`
	ConditionalOperator         string              `json:"ConditionalOperator,omitempty"`
	Expected                    map[string]ExpectedAttributeValue `json:"Expected,omitempty"`
	ExpressionAttributeNames    map[string]string   `json:"ExpressionAttributeNames,omitempty"`
	ExpressionAttributeValues   map[string]AttributeValue `json:"ExpressionAttributeValues,omitempty"`
	ReturnConsumedCapacity      string              `json:"ReturnConsumedCapacity,omitempty"`
	ReturnItemCollectionMetrics string              `json:"ReturnItemCollectionMetrics,omitempty"`
	ReturnValues                string              `json:"ReturnValues,omitempty"`
}

// DeleteItemResponse represents a DynamoDB DeleteItem response.
type DeleteItemResponse struct {
	Attributes       Item              `json:"Attributes,omitempty"`
	ConsumedCapacity *ConsumedCapacity `json:"ConsumedCapacity,omitempty"`
	ItemCollectionMetrics *ItemCollectionMetrics `json:"ItemCollectionMetrics,omitempty"`
}

// QueryRequest represents a DynamoDB Query request.
type QueryRequest struct {
	TableName                      string              `json:"TableName" binding:"required"`
	IndexName                      string              `json:"IndexName,omitempty"`
	AttributesToGet                []string            `json:"AttributesToGet,omitempty"`
	ConditionalOperator            string              `json:"ConditionalOperator,omitempty"`
	ConsistentRead                 bool                `json:"ConsistentRead,omitempty"`
	ExclusiveStartKey              Item                `json:"ExclusiveStartKey,omitempty"`
	ExpressionAttributeNames       map[string]string   `json:"ExpressionAttributeNames,omitempty"`
	ExpressionAttributeValues      map[string]AttributeValue `json:"ExpressionAttributeValues,omitempty"`
	FilterExpression               string              `json:"FilterExpression,omitempty"`
	KeyConditionExpression         string              `json:"KeyConditionExpression,omitempty"`
	KeyConditions                  map[string]Condition `json:"KeyConditions,omitempty"`
	Limit                          int                 `json:"Limit,omitempty"`
	ProjectionExpression           string              `json:"ProjectionExpression,omitempty"`
	ReturnConsumedCapacity         string              `json:"ReturnConsumedCapacity,omitempty"`
	ScanIndexForward               bool                `json:"ScanIndexForward,omitempty"`
	Select                         string              `json:"Select,omitempty"` // ALL_ATTRIBUTES, ALL_PROJECTED_ATTRIBUTES, SPECIFIC_ATTRIBUTES, COUNT
}

// QueryResponse represents a DynamoDB Query response.
type QueryResponse struct {
	ConsumedCapacity *ConsumedCapacity `json:"ConsumedCapacity,omitempty"`
	Count            int               `json:"Count"`
	Items            []Item            `json:"Items"`
	LastEvaluatedKey Item              `json:"LastEvaluatedKey,omitempty"`
	ScannedCount     int               `json:"ScannedCount"`
}

// ScanRequest represents a DynamoDB Scan request.
type ScanRequest struct {
	TableName                      string              `json:"TableName" binding:"required"`
	IndexName                      string              `json:"IndexName,omitempty"`
	AttributesToGet                []string            `json:"AttributesToGet,omitempty"`
	ConsistentRead                 bool                `json:"ConsistentRead,omitempty"`
	ExclusiveStartKey              Item                `json:"ExclusiveStartKey,omitempty"`
	ExpressionAttributeNames       map[string]string   `json:"ExpressionAttributeNames,omitempty"`
	ExpressionAttributeValues      map[string]AttributeValue `json:"ExpressionAttributeValues,omitempty"`
	FilterExpression               string              `json:"FilterExpression,omitempty"`
	Limit                          int                 `json:"Limit,omitempty"`
	ProjectionExpression           string              `json:"ProjectionExpression,omitempty"`
	ReturnConsumedCapacity         string              `json:"ReturnConsumedCapacity,omitempty"`
	Segment                        int                 `json:"Segment,omitempty"`
	Select                         string              `json:"Select,omitempty"`
	TotalSegments                  int                 `json:"TotalSegments,omitempty"`
}

// ScanResponse represents a DynamoDB Scan response.
type ScanResponse struct {
	ConsumedCapacity *ConsumedCapacity `json:"ConsumedCapacity,omitempty"`
	Count            int               `json:"Count"`
	Items            []Item            `json:"Items"`
	LastEvaluatedKey Item              `json:"LastEvaluatedKey,omitempty"`
	ScannedCount     int               `json:"ScannedCount"`
}

// Condition represents a key condition for Query operations.
type Condition struct {
	AttributeValueList []AttributeValue `json:"AttributeValueList,omitempty"`
	ComparisonOperator string           `json:"ComparisonOperator,omitempty"` // EQ, LE, LT, GE, GT, BEGINS_WITH, BETWEEN
}

// ExpectedAttributeValue represents an expected attribute value for conditional operations.
type ExpectedAttributeValue struct {
	AttributeValueList []AttributeValue `json:"AttributeValueList,omitempty"`
	ComparisonOperator string           `json:"ComparisonOperator,omitempty"`
	Exists             *bool            `json:"Exists,omitempty"`
	Value              AttributeValue   `json:"Value,omitempty"`
}

// AttributeUpdate represents an attribute update for UpdateItem operations.
type AttributeUpdate struct {
	Action string         `json:"Action,omitempty"` // PUT, DELETE, ADD
	Value  AttributeValue `json:"Value,omitempty"`
}

// ConsumedCapacity represents consumed capacity for an operation.
type ConsumedCapacity struct {
	CapacityUnits float64           `json:"CapacityUnits,omitempty"`
	GlobalSecondaryIndexes map[string]Capacity `json:"GlobalSecondaryIndexes,omitempty"`
	LocalSecondaryIndexes  map[string]Capacity `json:"LocalSecondaryIndexes,omitempty"`
	ReadCapacityUnits  float64 `json:"ReadCapacityUnits,omitempty"`
	Table              Capacity `json:"Table,omitempty"`
	TableName          string   `json:"TableName,omitempty"`
	WriteCapacityUnits float64  `json:"WriteCapacityUnits,omitempty"`
}

// Capacity represents capacity information.
type Capacity struct {
	CapacityUnits float64 `json:"CapacityUnits,omitempty"`
	ReadCapacityUnits float64 `json:"ReadCapacityUnits,omitempty"`
	WriteCapacityUnits float64 `json:"WriteCapacityUnits,omitempty"`
}

// ItemCollectionMetrics represents item collection metrics.
type ItemCollectionMetrics struct {
	ItemCollectionKey   Item                `json:"ItemCollectionKey,omitempty"`
	SizeEstimateRangeGB []float64           `json:"SizeEstimateRangeGB,omitempty"`
}

// ErrorResponse represents a DynamoDB error response.
type ErrorResponse struct {
	__type  string `json:"__type,omitempty"`
	Type    string `json:"-"` // Used for JSON serialization
	Message string `json:"Message"`
}

// MarshalJSON implements custom JSON marshaling for ErrorResponse.
func (e ErrorResponse) MarshalJSON() ([]byte, error) {
	type Alias ErrorResponse
	return marshalJSONWithType(Alias(e), "__type", e.Type)
}

// DynamoDBRequest represents a generic DynamoDB request.
type DynamoDBRequest struct {
	TableName                       string                       `json:"TableName,omitempty"`
	KeySchema                       []KeySchemaElement           `json:"KeySchema,omitempty"`
	AttributeDefinitions            []AttributeDefinition        `json:"AttributeDefinitions,omitempty"`
	BillingMode                     string                       `json:"BillingMode,omitempty"`
	GlobalSecondaryIndexes          []GlobalSecondaryIndex       `json:"GlobalSecondaryIndexes,omitempty"`
	LocalSecondaryIndexes           []LocalSecondaryIndex        `json:"LocalSecondaryIndexes,omitempty"`
	ProvisionedThroughput           *ProvisionedThroughput       `json:"ProvisionedThroughput,omitempty"`
	Tags                            []Tag                        `json:"Tags,omitempty"`
	ResourceARN                     string                       `json:"ResourceArn,omitempty"`
	TagKeys                         []string                     `json:"TagKeys,omitempty"`
	
	// Item operation fields
	Key                             Item                         `json:"Key,omitempty"`
	Item                            Item                         `json:"Item,omitempty"`
	IndexName                       string                       `json:"IndexName,omitempty"`
	AttributesToGet                 []string                     `json:"AttributesToGet,omitempty"`
	ConsistentRead                  bool                         `json:"ConsistentRead,omitempty"`
	ExclusiveStartKey               Item                         `json:"ExclusiveStartKey,omitempty"`
	ExpressionAttributeNames        map[string]string            `json:"ExpressionAttributeNames,omitempty"`
	ExpressionAttributeValues       map[string]AttributeValue    `json:"ExpressionAttributeValues,omitempty"`
	FilterExpression                string                       `json:"FilterExpression,omitempty"`
	KeyConditionExpression          string                       `json:"KeyConditionExpression,omitempty"`
	KeyConditions                   map[string]Condition         `json:"KeyConditions,omitempty"`
	Limit                           int                          `json:"Limit,omitempty"`
	ProjectionExpression            string                       `json:"ProjectionExpression,omitempty"`
	ReturnConsumedCapacity          string                       `json:"ReturnConsumedCapacity,omitempty"`
	ReturnItemCollectionMetrics     string                       `json:"ReturnItemCollectionMetrics,omitempty"`
	ReturnValues                    string                       `json:"ReturnValues,omitempty"`
	ScanIndexForward                bool                         `json:"ScanIndexForward,omitempty"`
	Select                          string                       `json:"Select,omitempty"`
	UpdateExpression                string                       `json:"UpdateExpression,omitempty"`
	ConditionExpression             string                       `json:"ConditionExpression,omitempty"`
	ConditionalOperator             string                       `json:"ConditionalOperator,omitempty"`
	Expected                        map[string]ExpectedAttributeValue `json:"Expected,omitempty"`
	AttributeUpdates                map[string]AttributeUpdate   `json:"AttributeUpdates,omitempty"`
	TotalSegments                   int                          `json:"TotalSegments,omitempty"`
	Segment                         int                          `json:"Segment,omitempty"`
	
	// ListTables specific fields
	ExclusiveStartTableName         string                       `json:"ExclusiveStartTableName,omitempty"`
}

// DynamoDBResponse represents a generic DynamoDB response.
type DynamoDBResponse struct {
	TableDescription    *TableMetadata    `json:"TableDescription,omitempty"`
	TableNames          []string          `json:"TableNames,omitempty"`
	Table               *TableMetadata    `json:"Table,omitempty"`
	Tags                []Tag             `json:"Tags,omitempty"`
	Endpoints           []Endpoint        `json:"Endpoints,omitempty"`
	
	// Item operation fields
	Item                Item              `json:"Item,omitempty"`
	Attributes          Item              `json:"Attributes,omitempty"`
	Items               []Item            `json:"Items,omitempty"`
	Count               int               `json:"Count,omitempty"`
	ScannedCount        int               `json:"ScannedCount,omitempty"`
	LastEvaluatedKey    Item              `json:"LastEvaluatedKey,omitempty"`
	ConsumedCapacity    *ConsumedCapacity `json:"ConsumedCapacity,omitempty"`
	ItemCollectionMetrics *ItemCollectionMetrics `json:"ItemCollectionMetrics,omitempty"`
	
	// ListTables specific fields
	LastEvaluatedTableName string          `json:"LastEvaluatedTableName,omitempty"`
}

// Endpoint represents a DynamoDB endpoint.
type Endpoint struct {
	Address              string `json:"Address"`
	CachePeriodInMinutes int64  `json:"CachePeriodInMinutes"`
}

// marshalJSONWithType is a helper function for marshaling with __type field.
func marshalJSONWithType(v interface{}, typeField, typeValue string) ([]byte, error) {
	// This is a simplified version - in production, use proper reflection
	return nil, nil
}

// BatchGetItemRequest represents a BatchGetItem request.
type BatchGetItemRequest struct {
	RequestItems                map[string]KeysAndAttributes `json:"RequestItems" binding:"required"`
	ReturnConsumedCapacity      string                       `json:"ReturnConsumedCapacity,omitempty"`
}

// KeysAndAttributes represents keys and attributes for a table in BatchGetItem.
type KeysAndAttributes struct {
	Keys                     []Item              `json:"Keys" binding:"required"`
	AttributesToGet          []string            `json:"AttributesToGet,omitempty"`
	ConsistentRead           bool                `json:"ConsistentRead,omitempty"`
	ExpressionAttributeNames map[string]string   `json:"ExpressionAttributeNames,omitempty"`
	ProjectionExpression     string              `json:"ProjectionExpression,omitempty"`
}

// BatchGetItemResponse represents a BatchGetItem response.
type BatchGetItemResponse struct {
	Responses       map[string][]Item     `json:"Responses,omitempty"`
	UnprocessedKeys map[string]KeysAndAttributes `json:"UnprocessedKeys,omitempty"`
	ConsumedCapacity []ConsumedCapacity   `json:"ConsumedCapacity,omitempty"`
}

// BatchWriteItemRequest represents a BatchWriteItem request.
type BatchWriteItemRequest struct {
	RequestItems                map[string][]WriteRequest `json:"RequestItems" binding:"required"`
	ReturnConsumedCapacity      string                    `json:"ReturnConsumedCapacity,omitempty"`
	ReturnItemCollectionMetrics string                    `json:"ReturnItemCollectionMetrics,omitempty"`
}

// WriteRequest represents a single write request (Put or Delete).
type WriteRequest struct {
	PutRequest    *PutRequest    `json:"PutRequest,omitempty"`
	DeleteRequest *DeleteRequest `json:"DeleteRequest,omitempty"`
}

// PutRequest represents a PutItem operation in a batch write.
type PutRequest struct {
	Item Item `json:"Item" binding:"required"`
}

// DeleteRequest represents a DeleteItem operation in a batch write.
type DeleteRequest struct {
	Key Item `json:"Key" binding:"required"`
}

// BatchWriteItemResponse represents a BatchWriteItem response.
type BatchWriteItemResponse struct {
	UnprocessedItems map[string][]WriteRequest `json:"UnprocessedItems,omitempty"`
	ItemCollectionMetrics map[string]ItemCollectionMetrics `json:"ItemCollectionMetrics,omitempty"`
	ConsumedCapacity []ConsumedCapacity `json:"ConsumedCapacity,omitempty"`
}

// TransactGetItem represents a single get operation in a transaction.
type TransactGetItem struct {
	Get *TransactGet `json:"Get,omitempty"`
}

// TransactGet represents the Get operation details.
type TransactGet struct {
	TableName                string            `json:"TableName" binding:"required"`
	Key                      Item              `json:"Key" binding:"required"`
	ProjectionExpression     string            `json:"ProjectionExpression,omitempty"`
	ExpressionAttributeNames map[string]string `json:"ExpressionAttributeNames,omitempty"`
}

// TransactGetItemsRequest represents a TransactGetItems request.
type TransactGetItemsRequest struct {
	TransactItems          []TransactGetItem `json:"TransactItems" binding:"required"`
	ReturnConsumedCapacity string            `json:"ReturnConsumedCapacity,omitempty"`
}

// TransactGetItemsResponse represents a TransactGetItems response.
type TransactGetItemsResponse struct {
	Responses        []ItemResponse     `json:"Responses,omitempty"`
	ConsumedCapacity []ConsumedCapacity `json:"ConsumedCapacity,omitempty"`
}

// ItemResponse represents a single item response in TransactGetItems.
type ItemResponse struct {
	Item Item `json:"Item,omitempty"`
}

// TransactWriteItem represents a single write operation in a transaction.
type TransactWriteItem struct {
	Put            *TransactPut            `json:"Put,omitempty"`
	Update         *TransactUpdate         `json:"Update,omitempty"`
	Delete         *TransactDelete         `json:"Delete,omitempty"`
	ConditionCheck *TransactConditionCheck `json:"ConditionCheck,omitempty"`
}

// TransactPut represents a Put operation in a transaction.
type TransactPut struct {
	TableName                   string                       `json:"TableName" binding:"required"`
	Item                        Item                         `json:"Item" binding:"required"`
	ConditionExpression         string                       `json:"ConditionExpression,omitempty"`
	ExpressionAttributeNames    map[string]string            `json:"ExpressionAttributeNames,omitempty"`
	ExpressionAttributeValues   map[string]AttributeValue    `json:"ExpressionAttributeValues,omitempty"`
	ReturnValuesOnConditionCheckFailure string                `json:"ReturnValuesOnConditionCheckFailure,omitempty"`
}

// TransactUpdate represents an Update operation in a transaction.
type TransactUpdate struct {
	TableName                   string                       `json:"TableName" binding:"required"`
	Key                         Item                         `json:"Key" binding:"required"`
	UpdateExpression            string                       `json:"UpdateExpression,omitempty"`
	ConditionExpression         string                       `json:"ConditionExpression,omitempty"`
	ExpressionAttributeNames    map[string]string            `json:"ExpressionAttributeNames,omitempty"`
	ExpressionAttributeValues   map[string]AttributeValue    `json:"ExpressionAttributeValues,omitempty"`
	ReturnValuesOnConditionCheckFailure string                `json:"ReturnValuesOnConditionCheckFailure,omitempty"`
}

// TransactDelete represents a Delete operation in a transaction.
type TransactDelete struct {
	TableName                   string                       `json:"TableName" binding:"required"`
	Key                         Item                         `json:"Key" binding:"required"`
	ConditionExpression         string                       `json:"ConditionExpression,omitempty"`
	ExpressionAttributeNames    map[string]string            `json:"ExpressionAttributeNames,omitempty"`
	ExpressionAttributeValues   map[string]AttributeValue    `json:"ExpressionAttributeValues,omitempty"`
	ReturnValuesOnConditionCheckFailure string                `json:"ReturnValuesOnConditionCheckFailure,omitempty"`
}

// TransactConditionCheck represents a ConditionCheck operation in a transaction.
type TransactConditionCheck struct {
	TableName                   string                       `json:"TableName" binding:"required"`
	Key                         Item                         `json:"Key" binding:"required"`
	ConditionExpression         string                       `json:"ConditionExpression" binding:"required"`
	ExpressionAttributeNames    map[string]string            `json:"ExpressionAttributeNames,omitempty"`
	ExpressionAttributeValues   map[string]AttributeValue    `json:"ExpressionAttributeValues,omitempty"`
	ReturnValuesOnConditionCheckFailure string                `json:"ReturnValuesOnConditionCheckFailure,omitempty"`
}

// TransactWriteItemsRequest represents a TransactWriteItems request.
type TransactWriteItemsRequest struct {
	TransactItems              []TransactWriteItem `json:"TransactItems" binding:"required"`
	ReturnConsumedCapacity      string              `json:"ReturnConsumedCapacity,omitempty"`
	ReturnItemCollectionMetrics string              `json:"ReturnItemCollectionMetrics,omitempty"`
	ClientRequestToken          string              `json:"ClientRequestToken,omitempty"`
}

// TransactWriteItemsResponse represents a TransactWriteItems response.
type TransactWriteItemsResponse struct {
	ConsumedCapacity     []ConsumedCapacity       `json:"ConsumedCapacity,omitempty"`
	ItemCollectionMetrics map[string]ItemCollectionMetrics `json:"ItemCollectionMetrics,omitempty"`
}


// TimeToLiveSpecification represents the TTL specification for a table.
type TimeToLiveSpecification struct {
	AttributeName string `json:"AttributeName" binding:"required"`
	Enabled       bool   `json:"Enabled" binding:"required"`
}

// UpdateTimeToLiveRequest represents an UpdateTimeToLive request.
type UpdateTimeToLiveRequest struct {
	TableName               string                  `json:"TableName" binding:"required"`
	TimeToLiveSpecification TimeToLiveSpecification `json:"TimeToLiveSpecification" binding:"required"`
}

// TimeToLiveDescription represents the TTL description for a table.
type TimeToLiveDescription struct {
	AttributeName   string `json:"AttributeName,omitempty"`
	TimeToLiveStatus string `json:"TimeToLiveStatus,omitempty"` // ENABLING, ENABLED, DISABLING, DISABLED
}

// UpdateTimeToLiveResponse represents an UpdateTimeToLive response.
type UpdateTimeToLiveResponse struct {
	TimeToLiveDescription TimeToLiveDescription `json:"TimeToLiveDescription,omitempty"`
}

// DescribeTimeToLiveRequest represents a DescribeTimeToLive request.
type DescribeTimeToLiveRequest struct {
	TableName string `json:"TableName" binding:"required"`
}

// DescribeTimeToLiveResponse represents a DescribeTimeToLive response.
type DescribeTimeToLiveResponse struct {
	TimeToLiveDescription TimeToLiveDescription `json:"TimeToLiveDescription,omitempty"`
}


// BackupDescription represents a backup description.
type BackupDescription struct {
	BackupArn      string `json:"BackupArn,omitempty"`
	BackupName     string `json:"BackupName,omitempty"`
	BackupStatus   string `json:"BackupStatus,omitempty"` // CREATING, DELETED, AVAILABLE
	BackupType     string `json:"BackupType,omitempty"`   // USER, SYSTEM, AWS_BACKUP
	BackupSizeBytes int64  `json:"BackupSizeBytes,omitempty"`
	CreationDate   int64  `json:"CreationDate,omitempty"` // Unix timestamp in seconds
	TableArn       string `json:"TableArn,omitempty"`
	TableName      string `json:"TableName,omitempty"`
}

// CreateBackupRequest represents a CreateBackup request.
type CreateBackupRequest struct {
	TableName  string `json:"TableName" binding:"required"`
	BackupName string `json:"BackupName" binding:"required"`
}

// CreateBackupResponse represents a CreateBackup response.
type CreateBackupResponse struct {
	BackupDescription BackupDescription `json:"BackupDescription,omitempty"`
}

// DescribeBackupRequest represents a DescribeBackup request.
type DescribeBackupRequest struct {
	BackupArn string `json:"BackupArn" binding:"required"`
}

// DescribeBackupResponse represents a DescribeBackup response.
type DescribeBackupResponse struct {
	BackupDescription BackupDescription `json:"BackupDescription,omitempty"`
}

// DeleteBackupRequest represents a DeleteBackup request.
type DeleteBackupRequest struct {
	BackupArn string `json:"BackupArn" binding:"required"`
}

// DeleteBackupResponse represents a DeleteBackup response.
type DeleteBackupResponse struct {
	BackupDescription BackupDescription `json:"BackupDescription,omitempty"`
}

// ListBackupsRequest represents a ListBackups request.
type ListBackupsRequest struct {
	TableName   string `json:"TableName,omitempty"`
	BackupType  string `json:"BackupType,omitempty"` // USER, SYSTEM, AWS_BACKUP, ALL
	Limit       int    `json:"Limit,omitempty"`
}

// ListBackupsResponse represents a ListBackups response.
type ListBackupsResponse struct {
	BackupSummaries []BackupDescription `json:"BackupSummaries,omitempty"`
}

// RestoreTableFromBackupRequest represents a RestoreTableFromBackup request.
type RestoreTableFromBackupRequest struct {
	BackupArn       string `json:"BackupArn" binding:"required"`
	TargetTableName string `json:"TargetTableName" binding:"required"`
}

// RestoreTableFromBackupResponse represents a RestoreTableFromBackup response.
type RestoreTableFromBackupResponse struct {
	TableDescription TableMetadata `json:"TableDescription,omitempty"`
}
