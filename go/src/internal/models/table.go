// Package models provides DynamoDB-compatible data models.
package models

import (
	"time"
)

// TableMetadata represents the metadata for a DynamoDB table.
type TableMetadata struct {
	TableName             string                 `json:"TableName"`
	TableARN              string                 `json:"TableArn,omitempty"`
	TableID               string                 `json:"TableId,omitempty"`
	TableStatus           string                 `json:"TableStatus"`
	KeySchema             []KeySchemaElement     `json:"KeySchema"`
	AttributeDefinitions  []AttributeDefinition  `json:"AttributeDefinitions"`
	ItemCount             int64                  `json:"ItemCount"`
	TableSizeBytes        int64                  `json:"TableSizeBytes"`
	CreationDateTime      time.Time              `json:"CreationDateTime"`
	BillingModeSummary    *BillingModeSummary    `json:"BillingModeSummary,omitempty"`
	ProvisionedThroughput *ProvisionedThroughput `json:"ProvisionedThroughput,omitempty"`
	GlobalSecondaryIndexes []GlobalSecondaryIndex `json:"GlobalSecondaryIndexes,omitempty"`
	LocalSecondaryIndexes  []LocalSecondaryIndex  `json:"LocalSecondaryIndexes,omitempty"`
	Tags                  []Tag                  `json:"Tags,omitempty"`
}

// KeySchemaElement represents a key schema element.
type KeySchemaElement struct {
	AttributeName string `json:"AttributeName"`
	KeyType       string `json:"KeyType"` // "HASH" or "RANGE"
}

// AttributeDefinition represents an attribute definition.
type AttributeDefinition struct {
	AttributeName string `json:"AttributeName"`
	AttributeType string `json:"AttributeType"` // "S", "N", or "B"
}

// BillingModeSummary represents the billing mode summary.
type BillingModeSummary struct {
	BillingMode   string `json:"BillingMode"`
	LastUpdateToPayPerRequestDateTime time.Time `json:"LastUpdateToPayPerRequestDateTime,omitempty"`
}

// ProvisionedThroughput represents provisioned throughput settings.
type ProvisionedThroughput struct {
	ReadCapacityUnits  int64 `json:"ReadCapacityUnits"`
	WriteCapacityUnits int64 `json:"WriteCapacityUnits"`
}

// GlobalSecondaryIndex represents a global secondary index.
type GlobalSecondaryIndex struct {
	IndexName             string                 `json:"IndexName"`
	KeySchema             []KeySchemaElement     `json:"KeySchema"`
	Projection            Projection             `json:"Projection"`
	ProvisionedThroughput *ProvisionedThroughput `json:"ProvisionedThroughput,omitempty"`
}

// LocalSecondaryIndex represents a local secondary index.
type LocalSecondaryIndex struct {
	IndexName  string             `json:"IndexName"`
	KeySchema  []KeySchemaElement `json:"KeySchema"`
	Projection Projection         `json:"Projection"`
}

// Projection represents the projection type for an index.
type Projection struct {
	ProjectionType   string   `json:"ProjectionType"` // "ALL", "KEYS_ONLY", or "INCLUDE"
	NonKeyAttributes []string `json:"NonKeyAttributes,omitempty"`
}

// Tag represents a resource tag.
type Tag struct {
	Key   string `json:"Key"`
	Value string `json:"Value"`
}

// UpdateTableRequest represents an UpdateTable request.
type UpdateTableRequest struct {
	TableName                       string                         `json:"TableName" binding:"required"`
	AttributeDefinitions            []AttributeDefinition          `json:"AttributeDefinitions,omitempty"`
	BillingMode                     string                         `json:"BillingMode,omitempty"`
	GlobalSecondaryIndexUpdates     []GlobalSecondaryIndexUpdate   `json:"GlobalSecondaryIndexUpdates,omitempty"`
	ProvisionedThroughput           *ProvisionedThroughput         `json:"ProvisionedThroughput,omitempty"`
	ReplicaUpdates                  []ReplicaUpdate                `json:"ReplicaUpdates,omitempty"`
	SSESpecification                *SSESpecification              `json:"SSESpecification,omitempty"`
	StreamSpecification             *StreamSpecification           `json:"StreamSpecification,omitempty"`
}

// GlobalSecondaryIndexUpdate represents a GSI update operation.
type GlobalSecondaryIndexUpdate struct {
	Create *CreateGlobalSecondaryIndexAction `json:"Create,omitempty"`
	Update *UpdateGlobalSecondaryIndexAction `json:"Update,omitempty"`
	Delete *DeleteGlobalSecondaryIndexAction `json:"Delete,omitempty"`
}

// CreateGlobalSecondaryIndexAction represents creating a GSI.
type CreateGlobalSecondaryIndexAction struct {
	IndexName             string                 `json:"IndexName" binding:"required"`
	KeySchema             []KeySchemaElement     `json:"KeySchema" binding:"required"`
	Projection            Projection             `json:"Projection" binding:"required"`
	ProvisionedThroughput *ProvisionedThroughput `json:"ProvisionedThroughput,omitempty"`
}

// UpdateGlobalSecondaryIndexAction represents updating a GSI.
type UpdateGlobalSecondaryIndexAction struct {
	IndexName             string                 `json:"IndexName" binding:"required"`
	ProvisionedThroughput *ProvisionedThroughput `json:"ProvisionedThroughput,omitempty"`
}

// DeleteGlobalSecondaryIndexAction represents deleting a GSI.
type DeleteGlobalSecondaryIndexAction struct {
	IndexName string `json:"IndexName" binding:"required"`
}

// ReplicaUpdate represents a replica update (placeholder).
type ReplicaUpdate struct {
	// Placeholder for replica updates
}

// SSESpecification represents server-side encryption settings.
type SSESpecification struct {
	Enabled        bool   `json:"Enabled,omitempty"`
	SSEType        string `json:"SSEType,omitempty"`
	KMSMasterKeyID string `json:"KMSMasterKeyId,omitempty"`
}

// StreamSpecification represents stream settings.
type StreamSpecification struct {
	StreamEnabled  bool           `json:"StreamEnabled,omitempty"`
	StreamViewType StreamViewType `json:"StreamViewType,omitempty"`
}

// UpdateTableResponse represents an UpdateTable response.
type UpdateTableResponse struct {
	TableDescription TableMetadata `json:"TableDescription"`
}
