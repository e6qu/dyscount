// Package models provides DynamoDB operation request/response models.
package models

// DynamoDBRequest represents a generic DynamoDB API request.
type DynamoDBRequest struct {
	TableName                     string                        `json:"TableName,omitempty"`
	Key                           map[string]interface{}        `json:"Key,omitempty"`
	Item                          map[string]interface{}        `json:"Item,omitempty"`
	AttributeDefinitions          []AttributeDefinition         `json:"AttributeDefinitions,omitempty"`
	KeySchema                     []KeySchemaElement            `json:"KeySchema,omitempty"`
	BillingMode                   string                        `json:"BillingMode,omitempty"`
	ProvisionedThroughput         *ProvisionedThroughput        `json:"ProvisionedThroughput,omitempty"`
	GlobalSecondaryIndexes        []GlobalSecondaryIndex        `json:"GlobalSecondaryIndexes,omitempty"`
	LocalSecondaryIndexes         []LocalSecondaryIndex         `json:"LocalSecondaryIndexes,omitempty"`
	GlobalSecondaryIndexUpdates   []GlobalSecondaryIndexUpdate  `json:"GlobalSecondaryIndexUpdates,omitempty"`
	StreamSpecification           *StreamSpecification          `json:"StreamSpecification,omitempty"`
	SSESpecification              *SSESpecification             `json:"SSESpecification,omitempty"`
	DeletionProtectionEnabled     bool                          `json:"DeletionProtectionEnabled,omitempty"`
	Tags                          []Tag                         `json:"Tags,omitempty"`
	ResourceARN                   string                        `json:"ResourceArn,omitempty"`
	TagKeys                       []string                      `json:"TagKeys,omitempty"`
}

// DynamoDBResponse represents a generic DynamoDB API response.
type DynamoDBResponse struct {
	TableDescription *TableMetadata `json:"TableDescription,omitempty"`
	TableNames       []string       `json:"TableNames,omitempty"`
	LastEvaluatedTableName string   `json:"LastEvaluatedTableName,omitempty"`
	Tags             []Tag          `json:"Tags,omitempty"`
	Endpoints        []Endpoint     `json:"Endpoints,omitempty"`
}

// GlobalSecondaryIndexUpdate represents a GSI update operation.
type GlobalSecondaryIndexUpdate struct {
	Create *CreateGlobalSecondaryIndexAction `json:"Create,omitempty"`
	Update *UpdateGlobalSecondaryIndexAction `json:"Update,omitempty"`
	Delete *DeleteGlobalSecondaryIndexAction `json:"Delete,omitempty"`
}

// CreateGlobalSecondaryIndexAction represents a create GSI action.
type CreateGlobalSecondaryIndexAction struct {
	IndexName             string                 `json:"IndexName"`
	KeySchema             []KeySchemaElement     `json:"KeySchema"`
	Projection            Projection             `json:"Projection"`
	ProvisionedThroughput *ProvisionedThroughput `json:"ProvisionedThroughput,omitempty"`
}

// UpdateGlobalSecondaryIndexAction represents an update GSI action.
type UpdateGlobalSecondaryIndexAction struct {
	IndexName             string                 `json:"IndexName"`
	ProvisionedThroughput *ProvisionedThroughput `json:"ProvisionedThroughput,omitempty"`
}

// DeleteGlobalSecondaryIndexAction represents a delete GSI action.
type DeleteGlobalSecondaryIndexAction struct {
	IndexName string `json:"IndexName"`
}

// StreamSpecification represents stream configuration.
type StreamSpecification struct {
	StreamEnabled  bool   `json:"StreamEnabled"`
	StreamViewType string `json:"StreamViewType,omitempty"` // "NEW_IMAGE", "OLD_IMAGE", "NEW_AND_OLD_IMAGES", "KEYS_ONLY"
}

// SSESpecification represents server-side encryption configuration.
type SSESpecification struct {
	Enabled        bool   `json:"Enabled,omitempty"`
	SSEType        string `json:"SSEType,omitempty"`        // "AES256" or "KMS"
	KMSMasterKeyID string `json:"KMSMasterKeyId,omitempty"`
}

// Endpoint represents a service endpoint.
type Endpoint struct {
	Address               string `json:"Address"`
	CachePeriodInMinutes  int64  `json:"CachePeriodInMinutes"`
}

// ErrorResponse represents a DynamoDB error response.
type ErrorResponse struct {
	Type    string `json:"__type"`
	Message string `json:"message"`
}
