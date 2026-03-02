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
