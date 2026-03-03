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

// PartiQL Models

// ExecuteStatementRequest represents an ExecuteStatement request.
type ExecuteStatementRequest struct {
	Statement             string                 `json:"Statement" binding:"required"`
	Parameters            []Item                 `json:"Parameters,omitempty"`
	ConsistentRead        bool                   `json:"ConsistentRead,omitempty"`
	NextToken             string                 `json:"NextToken,omitempty"`
	ReturnConsumedCapacity string                `json:"ReturnConsumedCapacity,omitempty"`
	Limit                 int                    `json:"Limit,omitempty"`
}

// ExecuteStatementResponse represents an ExecuteStatement response.
type ExecuteStatementResponse struct {
	Items            []Item            `json:"Items,omitempty"`
	NextToken        string            `json:"NextToken,omitempty"`
	LastEvaluatedKey Item              `json:"LastEvaluatedKey,omitempty"`
}

// BatchStatementRequest represents a single PartiQL statement in a batch.
type BatchStatementRequest struct {
	Statement      string `json:"Statement" binding:"required"`
	Parameters     []Item `json:"Parameters,omitempty"`
	ConsistentRead bool   `json:"ConsistentRead,omitempty"`
}

// BatchStatementResponse represents a response for a single statement in a batch.
type BatchStatementResponse struct {
	Item       Item   `json:"Item,omitempty"`
	TableName  string `json:"TableName,omitempty"`
	Error      *ErrorResponse `json:"Error,omitempty"`
}

// BatchExecuteStatementRequest represents a BatchExecuteStatement request.
type BatchExecuteStatementRequest struct {
	Statements             []BatchStatementRequest `json:"Statements" binding:"required"`
	ReturnConsumedCapacity string                  `json:"ReturnConsumedCapacity,omitempty"`
}

// BatchExecuteStatementResponse represents a BatchExecuteStatement response.
type BatchExecuteStatementResponse struct {
	Responses []BatchStatementResponse `json:"Responses,omitempty"`
}

// Export/Import Models

// ExportFormat represents the export format.
type ExportFormat string

const (
	ExportFormatDynamoDBJSON ExportFormat = "DYNAMODB_JSON"
	ExportFormatION          ExportFormat = "ION"
)

// ExportType represents the export type.
type ExportType string

const (
	ExportTypeFullExport       ExportType = "FULL_EXPORT"
	ExportTypeIncrementalExport ExportType = "INCREMENTAL_EXPORT"
)

// ExportStatus represents the export status.
type ExportStatus string

const (
	ExportStatusInProgress ExportStatus = "IN_PROGRESS"
	ExportStatusCompleted  ExportStatus = "COMPLETED"
	ExportStatusFailed     ExportStatus = "FAILED"
)

// ExportDescription represents an export description.
type ExportDescription struct {
	ExportArn      string       `json:"ExportArn,omitempty"`
	ExportStatus   ExportStatus `json:"ExportStatus,omitempty"`
	ExportTime     int64        `json:"ExportTime,omitempty"`
	TableArn       string       `json:"TableArn,omitempty"`
	TableName      string       `json:"TableName,omitempty"`
	S3Bucket       string       `json:"S3Bucket,omitempty"`
	S3Prefix       string       `json:"S3Prefix,omitempty"`
	ExportFormat   ExportFormat `json:"ExportFormat,omitempty"`
	ExportType     ExportType   `json:"ExportType,omitempty"`
	FailureCode    string       `json:"FailureCode,omitempty"`
	FailureMessage string       `json:"FailureMessage,omitempty"`
	ItemCount      int64        `json:"ItemCount,omitempty"`
	ProcessedBytes int64        `json:"ProcessedBytes,omitempty"`
}

// ExportTableToPointInTimeRequest represents an ExportTableToPointInTime request.
type ExportTableToPointInTimeRequest struct {
	TableArn        string       `json:"TableArn" binding:"required"`
	S3Bucket        string       `json:"S3Bucket" binding:"required"`
	ExportTime      int64        `json:"ExportTime,omitempty"`
	ClientToken     string       `json:"ClientToken,omitempty"`
	S3Prefix        string       `json:"S3Prefix,omitempty"`
	S3BucketOwner   string       `json:"S3BucketOwner,omitempty"`
	ExportFormat    ExportFormat `json:"ExportFormat,omitempty"`
	ExportType      ExportType   `json:"ExportType,omitempty"`
}

// ExportTableToPointInTimeResponse represents an ExportTableToPointInTime response.
type ExportTableToPointInTimeResponse struct {
	ExportDescription ExportDescription `json:"ExportDescription,omitempty"`
}

// DescribeExportRequest represents a DescribeExport request.
type DescribeExportRequest struct {
	ExportArn string `json:"ExportArn" binding:"required"`
}

// DescribeExportResponse represents a DescribeExport response.
type DescribeExportResponse struct {
	ExportDescription ExportDescription `json:"ExportDescription,omitempty"`
}

// ExportSummary represents a summary of an export.
type ExportSummary struct {
	ExportArn    string       `json:"ExportArn,omitempty"`
	ExportStatus ExportStatus `json:"ExportStatus,omitempty"`
	ExportType   ExportType   `json:"ExportType,omitempty"`
}

// ListExportsRequest represents a ListExports request.
type ListExportsRequest struct {
	TableArn   string `json:"TableArn,omitempty"`
	MaxResults int    `json:"MaxResults,omitempty"`
	NextToken  string `json:"NextToken,omitempty"`
}

// ListExportsResponse represents a ListExports response.
type ListExportsResponse struct {
	ExportSummaries []ExportSummary `json:"ExportSummaries,omitempty"`
	NextToken       string          `json:"NextToken,omitempty"`
}

// ImportStatus represents the import status.
type ImportStatus string

const (
	ImportStatusInProgress ImportStatus = "IN_PROGRESS"
	ImportStatusCompleted  ImportStatus = "COMPLETED"
	ImportStatusFailed     ImportStatus = "FAILED"
)

// ImportDescription represents an import description.
type ImportDescription struct {
	ImportArn       string       `json:"ImportArn,omitempty"`
	ImportStatus    ImportStatus `json:"ImportStatus,omitempty"`
	TableArn        string       `json:"TableArn,omitempty"`
	TableName       string       `json:"TableName,omitempty"`
	S3BucketSource  string       `json:"S3BucketSource,omitempty"`
	S3Prefix        string       `json:"S3Prefix,omitempty"`
	ImportFormat    ExportFormat `json:"ImportFormat,omitempty"`
	FailureCode     string       `json:"FailureCode,omitempty"`
	FailureMessage  string       `json:"FailureMessage,omitempty"`
	ItemCount       int64        `json:"ItemCount,omitempty"`
	ProcessedBytes  int64        `json:"ProcessedBytes,omitempty"`
}

// ImportTableRequest represents an ImportTable request.
type ImportTableRequest struct {
	TableName       string       `json:"TableName" binding:"required"`
	S3BucketSource  string       `json:"S3BucketSource" binding:"required"`
	S3Prefix        string       `json:"S3Prefix,omitempty"`
	ImportFormat    ExportFormat `json:"ImportFormat,omitempty"`
	KeySchema       []KeySchemaElement `json:"KeySchema" binding:"required"`
	AttributeDefinitions []AttributeDefinition `json:"AttributeDefinitions" binding:"required"`
}

// ImportTableResponse represents an ImportTable response.
type ImportTableResponse struct {
	ImportDescription ImportDescription `json:"ImportDescription,omitempty"`
}

// DescribeImportRequest represents a DescribeImport request.
type DescribeImportRequest struct {
	ImportArn string `json:"ImportArn" binding:"required"`
}

// DescribeImportResponse represents a DescribeImport response.
type DescribeImportResponse struct {
	ImportDescription ImportDescription `json:"ImportDescription,omitempty"`
}

// ImportSummary represents a summary of an import.
type ImportSummary struct {
	ImportArn    string       `json:"ImportArn,omitempty"`
	ImportStatus ImportStatus `json:"ImportStatus,omitempty"`
}

// ListImportsRequest represents a ListImports request.
type ListImportsRequest struct {
	TableArn   string `json:"TableArn,omitempty"`
	MaxResults int    `json:"MaxResults,omitempty"`
	NextToken  string `json:"NextToken,omitempty"`
}

// ListImportsResponse represents a ListImports response.
type ListImportsResponse struct {
	ImportSummaries []ImportSummary `json:"ImportSummaries,omitempty"`
	NextToken       string          `json:"NextToken,omitempty"`
}


// Streams Models

// StreamStatus represents the status of a stream.
type StreamStatus string

const (
	StreamStatusEnabling  StreamStatus = "ENABLING"
	StreamStatusEnabled   StreamStatus = "ENABLED"
	StreamStatusDisabling StreamStatus = "DISABLING"
	StreamStatusDisabled  StreamStatus = "DISABLED"
)

// StreamViewType represents the type of data written to a stream.
type StreamViewType string

const (
	StreamViewTypeNewImage         StreamViewType = "NEW_IMAGE"
	StreamViewTypeOldImage         StreamViewType = "OLD_IMAGE"
	StreamViewTypeNewAndOldImages StreamViewType = "NEW_AND_OLD_IMAGES"
	StreamViewTypeKeysOnly         StreamViewType = "KEYS_ONLY"
)

// Stream represents a stream.
type Stream struct {
	StreamArn   string       `json:"StreamArn,omitempty"`
	StreamLabel string       `json:"StreamLabel,omitempty"`
	StreamStatus StreamStatus `json:"StreamStatus,omitempty"`
	StreamViewType StreamViewType `json:"StreamViewType,omitempty"`
	TableName   string       `json:"TableName,omitempty"`
	KeySchema   []KeySchemaElement `json:"KeySchema,omitempty"`
}

// StreamDescription represents a stream description.
type StreamDescription struct {
	StreamArn   string       `json:"StreamArn,omitempty"`
	StreamLabel string       `json:"StreamLabel,omitempty"`
	StreamStatus StreamStatus `json:"StreamStatus,omitempty"`
	StreamViewType StreamViewType `json:"StreamViewType,omitempty"`
	TableName   string       `json:"TableName,omitempty"`
	KeySchema   []KeySchemaElement `json:"KeySchema,omitempty"`
	Shards      []Shard      `json:"Shards,omitempty"`
}

// Shard represents a shard in a stream.
type Shard struct {
	ShardId       string `json:"ShardId,omitempty"`
	SequenceNumberRange SequenceNumberRange `json:"SequenceNumberRange,omitempty"`
}

// SequenceNumberRange represents a sequence number range.
type SequenceNumberRange struct {
	StartingSequenceNumber string `json:"StartingSequenceNumber,omitempty"`
	EndingSequenceNumber   string `json:"EndingSequenceNumber,omitempty"`
}

// StreamRecord represents a stream record.
type StreamRecord struct {
	ApproximateCreationDateTime int64          `json:"ApproximateCreationDateTime,omitempty"`
	Keys                        Item           `json:"Keys,omitempty"`
	NewImage                    Item           `json:"NewImage,omitempty"`
	OldImage                    Item           `json:"OldImage,omitempty"`
	SequenceNumber              string         `json:"SequenceNumber,omitempty"`
	SizeBytes                   int64          `json:"SizeBytes,omitempty"`
	StreamViewType              StreamViewType `json:"StreamViewType,omitempty"`
}

// Record represents a record in a stream.
type Record struct {
	AwsRegion      string       `json:"awsRegion,omitempty"`
	Dynamodb       StreamRecord `json:"dynamodb,omitempty"`
	EventID        string       `json:"eventID,omitempty"`
	EventName      string       `json:"eventName,omitempty"`
	EventSource    string       `json:"eventSource,omitempty"`
	EventVersion   string       `json:"eventVersion,omitempty"`
	EventSourceARN string       `json:"eventSourceARN,omitempty"`
}

// ListStreamsRequest represents a ListStreams request.
type ListStreamsRequest struct {
	TableName  string `json:"TableName,omitempty"`
	Limit      int    `json:"Limit,omitempty"`
	ExclusiveStartStreamArn string `json:"ExclusiveStartStreamArn,omitempty"`
}

// ListStreamsResponse represents a ListStreams response.
type ListStreamsResponse struct {
	Streams           []Stream `json:"Streams,omitempty"`
	LastEvaluatedStreamArn string `json:"LastEvaluatedStreamArn,omitempty"`
}

// DescribeStreamRequest represents a DescribeStream request.
type DescribeStreamRequest struct {
	StreamArn string `json:"StreamArn" binding:"required"`
	Limit     int    `json:"Limit,omitempty"`
	ExclusiveStartShardId string `json:"ExclusiveStartShardId,omitempty"`
}

// DescribeStreamResponse represents a DescribeStream response.
type DescribeStreamResponse struct {
	StreamDescription StreamDescription `json:"StreamDescription,omitempty"`
}

// GetShardIteratorRequest represents a GetShardIterator request.
type GetShardIteratorRequest struct {
	StreamArn         string `json:"StreamArn" binding:"required"`
	ShardId           string `json:"ShardId" binding:"required"`
	ShardIteratorType string `json:"ShardIteratorType" binding:"required"`
	SequenceNumber    string `json:"SequenceNumber,omitempty"`
}

// GetShardIteratorResponse represents a GetShardIterator response.
type GetShardIteratorResponse struct {
	ShardIterator string `json:"ShardIterator,omitempty"`
}

// GetRecordsRequest represents a GetRecords request.
type GetRecordsRequest struct {
	ShardIterator string `json:"ShardIterator" binding:"required"`
	Limit         int    `json:"Limit,omitempty"`
}

// GetRecordsResponse represents a GetRecords response.
type GetRecordsResponse struct {
	Records            []Record `json:"Records,omitempty"`
	NextShardIterator  string   `json:"NextShardIterator,omitempty"`
}


// PITR (Point-in-Time Recovery) Models

// PointInTimeRecoveryStatus represents PITR status.
type PointInTimeRecoveryStatus string

const (
	PointInTimeRecoveryStatusEnabled  PointInTimeRecoveryStatus = "ENABLED"
	PointInTimeRecoveryStatusDisabled PointInTimeRecoveryStatus = "DISABLED"
)

// ContinuousBackupsDescription represents continuous backups description.
type ContinuousBackupsDescription struct {
	ContinuousBackupsStatus  PointInTimeRecoveryStatus `json:"ContinuousBackupsStatus,omitempty"`
	PointInTimeRecoveryDescription *PointInTimeRecoveryDescription `json:"PointInTimeRecoveryDescription,omitempty"`
}

// PointInTimeRecoveryDescription represents PITR description.
type PointInTimeRecoveryDescription struct {
	PointInTimeRecoveryStatus PointInTimeRecoveryStatus `json:"PointInTimeRecoveryStatus,omitempty"`
	EarliestRestorableDateTime int64 `json:"EarliestRestorableDateTime,omitempty"`
	LatestRestorableDateTime   int64 `json:"LatestRestorableDateTime,omitempty"`
}

// UpdateContinuousBackupsRequest represents an UpdateContinuousBackups request.
type UpdateContinuousBackupsRequest struct {
	TableName string `json:"TableName" binding:"required"`
	PointInTimeRecoverySpecification *PointInTimeRecoverySpecification `json:"PointInTimeRecoverySpecification,omitempty"`
}

// PointInTimeRecoverySpecification represents PITR specification.
type PointInTimeRecoverySpecification struct {
	PointInTimeRecoveryEnabled bool `json:"PointInTimeRecoveryEnabled,omitempty"`
}

// UpdateContinuousBackupsResponse represents an UpdateContinuousBackups response.
type UpdateContinuousBackupsResponse struct {
	ContinuousBackupsDescription ContinuousBackupsDescription `json:"ContinuousBackupsDescription,omitempty"`
}

// DescribeContinuousBackupsRequest represents a DescribeContinuousBackups request.
type DescribeContinuousBackupsRequest struct {
	TableName string `json:"TableName" binding:"required"`
}

// DescribeContinuousBackupsResponse represents a DescribeContinuousBackups response.
type DescribeContinuousBackupsResponse struct {
	ContinuousBackupsDescription ContinuousBackupsDescription `json:"ContinuousBackupsDescription,omitempty"`
}

// RestoreTableToPointInTimeRequest represents a RestoreTableToPointInTime request.
type RestoreTableToPointInTimeRequest struct {
	SourceTableName string `json:"SourceTableName" binding:"required"`
	TargetTableName string `json:"TargetTableName" binding:"required"`
	UseLatestRestorableTime bool `json:"UseLatestRestorableTime,omitempty"`
	RestoreDateTime int64 `json:"RestoreDateTime,omitempty"`
}

// RestoreTableToPointInTimeResponse represents a RestoreTableToPointInTime response.
type RestoreTableToPointInTimeResponse struct {
	TableDescription TableMetadata `json:"TableDescription,omitempty"`
}

// Global Tables Models

// GlobalTableStatus represents global table status.
type GlobalTableStatus string

const (
	GlobalTableStatusCreating   GlobalTableStatus = "CREATING"
	GlobalTableStatusActive     GlobalTableStatus = "ACTIVE"
	GlobalTableStatusDeleting   GlobalTableStatus = "DELETING"
	GlobalTableStatusUpdating   GlobalTableStatus = "UPDATING"
)

// Replica represents a replica in a global table.
type Replica struct {
	RegionName string `json:"RegionName,omitempty"`
}

// ReplicaDescription represents a replica description.
type ReplicaDescription struct {
	RegionName string `json:"RegionName,omitempty"`
	ReplicaStatus GlobalTableStatus `json:"ReplicaStatus,omitempty"`
}

// GlobalTable represents a global table.
type GlobalTable struct {
	GlobalTableName string `json:"GlobalTableName,omitempty"`
	ReplicationGroup []Replica `json:"ReplicationGroup,omitempty"`
}

// GlobalTableDescription represents a global table description.
type GlobalTableDescription struct {
	GlobalTableName string `json:"GlobalTableName,omitempty"`
	GlobalTableStatus GlobalTableStatus `json:"GlobalTableStatus,omitempty"`
	ReplicationGroup []ReplicaDescription `json:"ReplicationGroup,omitempty"`
}

// CreateGlobalTableRequest represents a CreateGlobalTable request.
type CreateGlobalTableRequest struct {
	GlobalTableName string `json:"GlobalTableName" binding:"required"`
	ReplicationGroup []Replica `json:"ReplicationGroup" binding:"required"`
}

// CreateGlobalTableResponse represents a CreateGlobalTable response.
type CreateGlobalTableResponse struct {
	GlobalTableDescription GlobalTableDescription `json:"GlobalTableDescription,omitempty"`
}

// UpdateGlobalTableRequest represents an UpdateGlobalTable request.
type UpdateGlobalTableRequest struct {
	GlobalTableName string `json:"GlobalTableName" binding:"required"`
	ReplicaUpdates []ReplicaUpdate `json:"ReplicaUpdates" binding:"required"`
}

// ReplicaUpdate represents a replica update.
type ReplicaUpdate struct {
	Create *CreateReplicaAction `json:"Create,omitempty"`
	Delete *DeleteReplicaAction `json:"Delete,omitempty"`
}

// CreateReplicaAction represents a create replica action.
type CreateReplicaAction struct {
	RegionName string `json:"RegionName,omitempty"`
}

// DeleteReplicaAction represents a delete replica action.
type DeleteReplicaAction struct {
	RegionName string `json:"RegionName,omitempty"`
}

// UpdateGlobalTableResponse represents an UpdateGlobalTable response.
type UpdateGlobalTableResponse struct {
	GlobalTableDescription GlobalTableDescription `json:"GlobalTableDescription,omitempty"`
}

// DescribeGlobalTableRequest represents a DescribeGlobalTable request.
type DescribeGlobalTableRequest struct {
	GlobalTableName string `json:"GlobalTableName" binding:"required"`
}

// DescribeGlobalTableResponse represents a DescribeGlobalTable response.
type DescribeGlobalTableResponse struct {
	GlobalTableDescription GlobalTableDescription `json:"GlobalTableDescription,omitempty"`
}

// ListGlobalTablesRequest represents a ListGlobalTables request.
type ListGlobalTablesRequest struct {
	Limit int `json:"Limit,omitempty"`
	ExclusiveStartGlobalTableName string `json:"ExclusiveStartGlobalTableName,omitempty"`
}

// ListGlobalTablesResponse represents a ListGlobalTables response.
type ListGlobalTablesResponse struct {
	GlobalTables []GlobalTable `json:"GlobalTables,omitempty"`
	LastEvaluatedGlobalTableName string `json:"LastEvaluatedGlobalTableName,omitempty"`
}

// UpdateGlobalTableSettingsRequest represents an UpdateGlobalTableSettings request.
type UpdateGlobalTableSettingsRequest struct {
	GlobalTableName string `json:"GlobalTableName" binding:"required"`
	ReplicaSettingsUpdate []ReplicaSettingsUpdate `json:"ReplicaSettingsUpdate,omitempty"`
}

// ReplicaSettingsUpdate represents replica settings update.
type ReplicaSettingsUpdate struct {
	RegionName string `json:"RegionName,omitempty"`
}

// UpdateGlobalTableSettingsResponse represents an UpdateGlobalTableSettings response.
type UpdateGlobalTableSettingsResponse struct {
	GlobalTableDescription GlobalTableDescription `json:"GlobalTableDescription,omitempty"`
}


// Limits Models

// DescribeLimitsRequest represents a DescribeLimits request.
type DescribeLimitsRequest struct {}

// DescribeLimitsResponse represents a DescribeLimits response.
type DescribeLimitsResponse struct {
	AccountMaxReadCapacityUnits  int64 `json:"AccountMaxReadCapacityUnits,omitempty"`
	AccountMaxWriteCapacityUnits int64 `json:"AccountMaxWriteCapacityUnits,omitempty"`
	TableMaxReadCapacityUnits    int64 `json:"TableMaxReadCapacityUnits,omitempty"`
	TableMaxWriteCapacityUnits   int64 `json:"TableMaxWriteCapacityUnits,omitempty"`
}

// DescribeGlobalTableSettingsRequest represents a DescribeGlobalTableSettings request.
type DescribeGlobalTableSettingsRequest struct {
	GlobalTableName string `json:"GlobalTableName" binding:"required"`
}

// DescribeGlobalTableSettingsResponse represents a DescribeGlobalTableSettings response.
type DescribeGlobalTableSettingsResponse struct {
	GlobalTableName string `json:"GlobalTableName,omitempty"`
	ReplicaSettings []ReplicaSettingsDescription `json:"ReplicaSettings,omitempty"`
}

// ReplicaSettingsDescription represents replica settings description.
type ReplicaSettingsDescription struct {
	RegionName string `json:"RegionName,omitempty"`
	ReplicaStatus string `json:"ReplicaStatus,omitempty"`
}

// UpdateReplicationRequest represents an UpdateReplication request.
type UpdateReplicationRequest struct {
	GlobalTableName string `json:"GlobalTableName" binding:"required"`
	ReplicaUpdates []ReplicaUpdate `json:"ReplicaUpdates" binding:"required"`
}

// UpdateReplicationResponse represents an UpdateReplication response.
type UpdateReplicationResponse struct {
	GlobalTableDescription GlobalTableDescription `json:"GlobalTableDescription,omitempty"`
}
