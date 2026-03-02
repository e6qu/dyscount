// Package storage provides SQLite-backed storage for DynamoDB tables.
package storage

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	_ "github.com/mattn/go-sqlite3"
	"github.com/google/uuid"

	"github.com/e6qu/dyscount/internal/models"
)

// TableManager manages DynamoDB tables in SQLite.
type TableManager struct {
	dataDirectory string
	namespace     string
}

// NewTableManager creates a new TableManager.
func NewTableManager(dataDirectory, namespace string) (*TableManager, error) {
	// Ensure data directory exists
	nsPath := filepath.Join(dataDirectory, namespace)
	if err := os.MkdirAll(nsPath, 0755); err != nil {
		return nil, fmt.Errorf("failed to create namespace directory: %w", err)
	}

	return &TableManager{
		dataDirectory: dataDirectory,
		namespace:     namespace,
	}, nil
}

// getDBPath returns the SQLite database file path for a table.
func (tm *TableManager) getDBPath(tableName string) string {
	return filepath.Join(tm.dataDirectory, tm.namespace, fmt.Sprintf("%s.db", tableName))
}

// CreateTable creates a new table.
func (tm *TableManager) CreateTable(req *models.DynamoDBRequest) (*models.TableMetadata, error) {
	dbPath := tm.getDBPath(req.TableName)

	// Check if table already exists
	if _, err := os.Stat(dbPath); err == nil {
		return nil, fmt.Errorf("table already exists: %s", req.TableName)
	}

	// Create database
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to create database: %w", err)
	}
	defer db.Close()

	// Create items table
	if _, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS items (
			pk TEXT NOT NULL,
			sk TEXT,
			data BLOB NOT NULL,
			created_at INTEGER NOT NULL,
			updated_at INTEGER NOT NULL,
			PRIMARY KEY (pk, sk)
		)
	`); err != nil {
		return nil, fmt.Errorf("failed to create items table: %w", err)
	}

	// Create metadata table
	if _, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS __table_metadata (
			key TEXT PRIMARY KEY,
			value BLOB
		)
	`); err != nil {
		return nil, fmt.Errorf("failed to create metadata table: %w", err)
	}

	// Create index metadata table
	if _, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS __index_metadata (
			index_name TEXT PRIMARY KEY,
			index_type TEXT NOT NULL,
			key_schema BLOB NOT NULL,
			projection_type TEXT NOT NULL,
			projected_attributes BLOB,
			index_status TEXT,
			backfilling INTEGER,
			provisioned_throughput BLOB
		)
	`); err != nil {
		return nil, fmt.Errorf("failed to create index metadata table: %w", err)
	}

	// Generate table metadata
	now := time.Now().UTC()
	tableID := uuid.New().String()

	billingMode := req.BillingMode
	if billingMode == "" {
		billingMode = "PROVISIONED"
	}

	provisionedThroughput := req.ProvisionedThroughput
	if provisionedThroughput == nil && billingMode == "PROVISIONED" {
		provisionedThroughput = &models.ProvisionedThroughput{
			ReadCapacityUnits:  5,
			WriteCapacityUnits: 5,
		}
	}

	metadata := &models.TableMetadata{
		TableName:   req.TableName,
		TableARN:    fmt.Sprintf("arn:aws:dynamodb:local:%s:table/%s", tm.namespace, req.TableName),
		TableID:     tableID,
		TableStatus: "ACTIVE",
		KeySchema:   req.KeySchema,
		AttributeDefinitions: req.AttributeDefinitions,
		CreationDateTime: now,
		BillingModeSummary: &models.BillingModeSummary{
			BillingMode: billingMode,
		},
		ProvisionedThroughput:  provisionedThroughput,
		GlobalSecondaryIndexes: req.GlobalSecondaryIndexes,
		LocalSecondaryIndexes:  req.LocalSecondaryIndexes,
		Tags: req.Tags,
	}

	// Store metadata
	if err := tm.storeMetadata(db, metadata); err != nil {
		return nil, fmt.Errorf("failed to store metadata: %w", err)
	}

	// Store GSI metadata
	for _, gsi := range metadata.GlobalSecondaryIndexes {
		if err := tm.storeIndexMetadata(db, gsi, "GSI"); err != nil {
			return nil, fmt.Errorf("failed to store GSI metadata: %w", err)
		}
	}

	// Store LSI metadata
	for _, lsi := range metadata.LocalSecondaryIndexes {
		if err := tm.storeIndexMetadata(db, lsi, "LSI"); err != nil {
			return nil, fmt.Errorf("failed to store LSI metadata: %w", err)
		}
	}

	return metadata, nil
}

// DeleteTable deletes a table.
func (tm *TableManager) DeleteTable(tableName string) (*models.TableMetadata, error) {
	dbPath := tm.getDBPath(tableName)

	// Check if table exists
	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		return nil, nil
	}

	// Get metadata before deletion
	metadata, err := tm.DescribeTable(tableName)
	if err != nil {
		return nil, err
	}

	// Delete database file
	if err := os.Remove(dbPath); err != nil {
		return nil, fmt.Errorf("failed to delete database: %w", err)
	}

	return metadata, nil
}

// ListTables lists all tables.
func (tm *TableManager) ListTables() ([]string, error) {
	nsPath := filepath.Join(tm.dataDirectory, tm.namespace)
	entries, err := os.ReadDir(nsPath)
	if err != nil {
		if os.IsNotExist(err) {
			return []string{}, nil
		}
		return nil, fmt.Errorf("failed to read namespace directory: %w", err)
	}

	var tables []string
	for _, entry := range entries {
		if !entry.IsDir() && filepath.Ext(entry.Name()) == ".db" {
			tableName := entry.Name()[:len(entry.Name())-3] // Remove .db
			tables = append(tables, tableName)
		}
	}

	return tables, nil
}

// DescribeTable returns table metadata.
func (tm *TableManager) DescribeTable(tableName string) (*models.TableMetadata, error) {
	dbPath := tm.getDBPath(tableName)

	// Check if table exists
	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		return nil, fmt.Errorf("table not found: %s", tableName)
	}

	// Open database
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}
	defer db.Close()

	// Load metadata
	return tm.loadMetadata(db, tableName)
}

// storeMetadata stores table metadata in the database.
func (tm *TableManager) storeMetadata(db *sql.DB, metadata *models.TableMetadata) error {
	// Store full metadata
	metadataJSON, err := json.Marshal(metadata)
	if err != nil {
		return fmt.Errorf("failed to marshal metadata: %w", err)
	}

	_, err = db.Exec(
		"INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
		"full_metadata", metadataJSON,
	)
	if err != nil {
		return fmt.Errorf("failed to store metadata: %w", err)
	}

	return nil
}

// loadMetadata loads table metadata from the database.
func (tm *TableManager) loadMetadata(db *sql.DB, tableName string) (*models.TableMetadata, error) {
	var metadataJSON []byte
	err := db.QueryRow(
		"SELECT value FROM __table_metadata WHERE key = ?",
		"full_metadata",
	).Scan(&metadataJSON)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("metadata not found for table: %s", tableName)
		}
		return nil, fmt.Errorf("failed to load metadata: %w", err)
	}

	var metadata models.TableMetadata
	if err := json.Unmarshal(metadataJSON, &metadata); err != nil {
		return nil, fmt.Errorf("failed to unmarshal metadata: %w", err)
	}

	return &metadata, nil
}

// storeIndexMetadata stores index metadata in the database.
func (tm *TableManager) storeIndexMetadata(db *sql.DB, index interface{}, indexType string) error {
	var indexName string
	var keySchema []models.KeySchemaElement
	var projection models.Projection
	var provisionedThroughput *models.ProvisionedThroughput

	switch idx := index.(type) {
	case models.GlobalSecondaryIndex:
		indexName = idx.IndexName
		keySchema = idx.KeySchema
		projection = idx.Projection
		provisionedThroughput = idx.ProvisionedThroughput
	case models.LocalSecondaryIndex:
		indexName = idx.IndexName
		keySchema = idx.KeySchema
		projection = idx.Projection
	default:
		return fmt.Errorf("unknown index type")
	}

	keySchemaJSON, _ := json.Marshal(keySchema)
	projectedAttrsJSON, _ := json.Marshal(projection.NonKeyAttributes)
	var provisionedThroughputJSON []byte
	if provisionedThroughput != nil {
		provisionedThroughputJSON, _ = json.Marshal(provisionedThroughput)
	}

	_, err := db.Exec(`
		INSERT INTO __index_metadata (
			index_name, index_type, key_schema, projection_type,
			projected_attributes, index_status, backfilling, provisioned_throughput
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	`,
		indexName, indexType, keySchemaJSON, projection.ProjectionType,
		projectedAttrsJSON, "ACTIVE", 0, provisionedThroughputJSON,
	)

	return err
}
