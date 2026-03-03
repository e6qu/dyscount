// Package storage provides SQLite-backed storage for DynamoDB tables.
package storage

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
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

// GetDataDirectory returns the data directory.
func (tm *TableManager) GetDataDirectory() string {
	return tm.dataDirectory
}

// GetNamespace returns the namespace.
func (tm *TableManager) GetNamespace() string {
	return tm.namespace
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

// ListTablesWithPagination lists tables with pagination support.
func (tm *TableManager) ListTablesWithPagination(limit int, exclusiveStartTableName string) ([]string, string, error) {
	nsPath := filepath.Join(tm.dataDirectory, tm.namespace)
	entries, err := os.ReadDir(nsPath)
	if err != nil {
		if os.IsNotExist(err) {
			return []string{}, "", nil
		}
		return nil, "", fmt.Errorf("failed to read namespace directory: %w", err)
	}

	var tables []string
	for _, entry := range entries {
		if !entry.IsDir() && filepath.Ext(entry.Name()) == ".db" {
			tableName := entry.Name()[:len(entry.Name())-3] // Remove .db
			tables = append(tables, tableName)
		}
	}

	// Sort tables for consistent pagination
	sort.Strings(tables)

	// Handle exclusive start
	if exclusiveStartTableName != "" {
		startIdx := -1
		for i, name := range tables {
			if name == exclusiveStartTableName {
				startIdx = i
				break
			}
		}
		if startIdx != -1 && startIdx < len(tables)-1 {
			tables = tables[startIdx+1:]
		} else {
			tables = []string{}
		}
	}

	// Apply limit
	var lastEvaluatedTableName string
	if limit > 0 && len(tables) > limit {
		tables = tables[:limit]
		lastEvaluatedTableName = tables[len(tables)-1]
	}

	return tables, lastEvaluatedTableName, nil
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

// UpdateTable updates a table's configuration.
func (tm *TableManager) UpdateTable(req *models.UpdateTableRequest) (*models.TableMetadata, error) {
	dbPath := tm.getDBPath(req.TableName)

	// Check if table exists
	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		return nil, fmt.Errorf("table not found: %s", req.TableName)
	}

	// Open database
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}
	defer db.Close()

	// Get current metadata
	metadata, err := tm.DescribeTable(req.TableName)
	if err != nil {
		return nil, err
	}

	// Update provisioned throughput if provided
	if req.ProvisionedThroughput != nil {
		metadata.ProvisionedThroughput = req.ProvisionedThroughput
	}

	// Update billing mode if provided
	if req.BillingMode != "" {
		if metadata.BillingModeSummary == nil {
			metadata.BillingModeSummary = &models.BillingModeSummary{}
		}
		metadata.BillingModeSummary.BillingMode = req.BillingMode
		metadata.BillingModeSummary.LastUpdateToPayPerRequestDateTime = time.Now().UTC()
	}

	// Process GSI updates
	for _, gsiUpdate := range req.GlobalSecondaryIndexUpdates {
		if gsiUpdate.Create != nil {
			if err := tm.createGSI(db, metadata, gsiUpdate.Create); err != nil {
				return nil, fmt.Errorf("failed to create GSI: %w", err)
			}
		}
		if gsiUpdate.Update != nil {
			if err := tm.updateGSI(db, gsiUpdate.Update); err != nil {
				return nil, fmt.Errorf("failed to update GSI: %w", err)
			}
		}
		if gsiUpdate.Delete != nil {
			if err := tm.deleteGSI(db, metadata, gsiUpdate.Delete); err != nil {
				return nil, fmt.Errorf("failed to delete GSI: %w", err)
			}
		}
	}

	// Update attribute definitions if provided
	if len(req.AttributeDefinitions) > 0 {
		// Merge new attribute definitions with existing ones
		existingAttrs := make(map[string]models.AttributeDefinition)
		for _, attr := range metadata.AttributeDefinitions {
			existingAttrs[attr.AttributeName] = attr
		}
		for _, attr := range req.AttributeDefinitions {
			existingAttrs[attr.AttributeName] = attr
		}

		// Convert back to slice
		metadata.AttributeDefinitions = make([]models.AttributeDefinition, 0, len(existingAttrs))
		for _, attr := range existingAttrs {
			metadata.AttributeDefinitions = append(metadata.AttributeDefinitions, attr)
		}
	}

	// Store updated metadata
	if err := tm.storeTableMetadata(db, metadata); err != nil {
		return nil, fmt.Errorf("failed to store metadata: %w", err)
	}

	return metadata, nil
}

// createGSI creates a new Global Secondary Index.
func (tm *TableManager) createGSI(db *sql.DB, metadata *models.TableMetadata, create *models.CreateGlobalSecondaryIndexAction) error {
	// Check if GSI already exists
	for _, gsi := range metadata.GlobalSecondaryIndexes {
		if gsi.IndexName == create.IndexName {
			return fmt.Errorf("GSI already exists: %s", create.IndexName)
		}
	}

	// Create GSI table
	gsiTableName := fmt.Sprintf("gsi_%s", create.IndexName)
	_, err := db.Exec(fmt.Sprintf(`
		CREATE TABLE IF NOT EXISTS "%s" (
			gsi_pk TEXT NOT NULL,
			gsi_sk TEXT,
			pk TEXT NOT NULL,
			sk TEXT,
			PRIMARY KEY (gsi_pk, gsi_sk)
		)
	`, gsiTableName))
	if err != nil {
		return fmt.Errorf("failed to create GSI table: %w", err)
	}

	// Create index on gsi_pk for faster lookups
	_, err = db.Exec(fmt.Sprintf(`
		CREATE INDEX IF NOT EXISTS "idx_%s_gsi_pk" ON "%s"(gsi_pk)
	`, gsiTableName, gsiTableName))
	if err != nil {
		return fmt.Errorf("failed to create GSI index: %w", err)
	}

	// Add GSI to metadata
	gsi := models.GlobalSecondaryIndex{
		IndexName:             create.IndexName,
		KeySchema:             create.KeySchema,
		Projection:            create.Projection,
		ProvisionedThroughput: create.ProvisionedThroughput,
	}
	metadata.GlobalSecondaryIndexes = append(metadata.GlobalSecondaryIndexes, gsi)

	// Store index metadata
	if err := tm.storeIndexMetadata(db, gsi, "GSI"); err != nil {
		return fmt.Errorf("failed to store GSI metadata: %w", err)
	}

	return nil
}

// updateGSI updates an existing Global Secondary Index.
func (tm *TableManager) updateGSI(db *sql.DB, update *models.UpdateGlobalSecondaryIndexAction) error {
	// Update provisioned throughput in index metadata
	provisionedThroughputJSON, _ := json.Marshal(update.ProvisionedThroughput)
	_, err := db.Exec(`
		UPDATE __index_metadata 
		SET provisioned_throughput = ?
		WHERE index_name = ? AND index_type = 'GSI'
	`, provisionedThroughputJSON, update.IndexName)

	if err != nil {
		return fmt.Errorf("failed to update GSI: %w", err)
	}

	return nil
}

// deleteGSI deletes a Global Secondary Index.
func (tm *TableManager) deleteGSI(db *sql.DB, metadata *models.TableMetadata, del *models.DeleteGlobalSecondaryIndexAction) error {
	// Find and remove GSI from metadata
	found := false
	newGSIs := make([]models.GlobalSecondaryIndex, 0, len(metadata.GlobalSecondaryIndexes))
	for _, gsi := range metadata.GlobalSecondaryIndexes {
		if gsi.IndexName == del.IndexName {
			found = true
			continue
		}
		newGSIs = append(newGSIs, gsi)
	}
	if !found {
		return fmt.Errorf("GSI not found: %s", del.IndexName)
	}
	metadata.GlobalSecondaryIndexes = newGSIs

	// Drop GSI table
	gsiTableName := fmt.Sprintf("gsi_%s", del.IndexName)
	_, err := db.Exec(fmt.Sprintf(`DROP TABLE IF EXISTS "%s"`, gsiTableName))
	if err != nil {
		return fmt.Errorf("failed to drop GSI table: %w", err)
	}

	// Remove index metadata
	_, err = db.Exec(`DELETE FROM __index_metadata WHERE index_name = ? AND index_type = 'GSI'`, del.IndexName)
	if err != nil {
		return fmt.Errorf("failed to delete GSI metadata: %w", err)
	}

	return nil
}

// storeTableMetadata stores table metadata in the database.
func (tm *TableManager) storeTableMetadata(db *sql.DB, metadata *models.TableMetadata) error {
	metadataJSON, err := json.Marshal(metadata)
	if err != nil {
		return fmt.Errorf("failed to marshal metadata: %w", err)
	}

	_, err = db.Exec(
		"INSERT OR REPLACE INTO __table_metadata (key, value) VALUES (?, ?)",
		"table_metadata", metadataJSON,
	)
	return err
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


// UpdateTimeToLive updates the TTL configuration for a table.
func (tm *TableManager) UpdateTimeToLive(req *models.UpdateTimeToLiveRequest) (*models.TimeToLiveDescription, error) {
	dbPath := tm.getDBPath(req.TableName)

	// Check if table exists
	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		return nil, fmt.Errorf("table not found: %s", req.TableName)
	}

	// Open database
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}
	defer db.Close()

	// Create TTL metadata table if not exists
	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS __ttl_metadata (
			attribute_name TEXT PRIMARY KEY,
			enabled INTEGER NOT NULL,
			status TEXT NOT NULL
		)
	`)
	if err != nil {
		return nil, fmt.Errorf("failed to create TTL metadata table: %w", err)
	}

	// Determine status
	status := "ENABLED"
	if !req.TimeToLiveSpecification.Enabled {
		status = "DISABLED"
	}

	// Store TTL configuration
	_, err = db.Exec(`
		INSERT OR REPLACE INTO __ttl_metadata (attribute_name, enabled, status)
		VALUES (?, ?, ?)
	`, req.TimeToLiveSpecification.AttributeName, req.TimeToLiveSpecification.Enabled, status)
	if err != nil {
		return nil, fmt.Errorf("failed to store TTL configuration: %w", err)
	}

	return &models.TimeToLiveDescription{
		AttributeName:    req.TimeToLiveSpecification.AttributeName,
		TimeToLiveStatus: status,
	}, nil
}

// DescribeTimeToLive returns the TTL configuration for a table.
func (tm *TableManager) DescribeTimeToLive(tableName string) (*models.TimeToLiveDescription, error) {
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

	// Check if TTL metadata table exists
	var exists bool
	err = db.QueryRow(`
		SELECT 1 FROM sqlite_master WHERE type='table' AND name='__ttl_metadata'
	`).Scan(&exists)
	if err != nil || !exists {
		// TTL not configured
		return &models.TimeToLiveDescription{
			TimeToLiveStatus: "DISABLED",
		}, nil
	}

	// Get TTL configuration
	var attributeName string
	var enabled bool
	var status string
	err = db.QueryRow(`
		SELECT attribute_name, enabled, status FROM __ttl_metadata LIMIT 1
	`).Scan(&attributeName, &enabled, &status)
	if err != nil {
		if err == sql.ErrNoRows {
			return &models.TimeToLiveDescription{
				TimeToLiveStatus: "DISABLED",
			}, nil
		}
		return nil, fmt.Errorf("failed to get TTL configuration: %w", err)
	}

	return &models.TimeToLiveDescription{
		AttributeName:    attributeName,
		TimeToLiveStatus: status,
	}, nil
}


// CreateBackup creates a backup of a table.
func (tm *TableManager) CreateBackup(req *models.CreateBackupRequest) (*models.BackupDescription, error) {
	sourceDBPath := tm.getDBPath(req.TableName)

	// Check if table exists
	if _, err := os.Stat(sourceDBPath); os.IsNotExist(err) {
		return nil, fmt.Errorf("table not found: %s", req.TableName)
	}

	// Auto-generate backup name if not provided
	backupName := req.BackupName
	if backupName == "" {
		backupName = fmt.Sprintf("%s_backup_%d", req.TableName, time.Now().Unix())
	}

	// Generate backup ARN
	backupArn := fmt.Sprintf("arn:aws:dynamodb:local:000000000000:table/%s/backup/%s-%d",
		req.TableName, backupName, time.Now().Unix())

	// Create backup directory
	backupDir := filepath.Join(tm.dataDirectory, tm.namespace, "backups")
	if err := os.MkdirAll(backupDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create backup directory: %w", err)
	}

	// Copy database file
	backupFileName := fmt.Sprintf("%s_%s.db", req.TableName, backupName)
	backupPath := filepath.Join(backupDir, backupFileName)

	if err := tm.copyFile(sourceDBPath, backupPath); err != nil {
		return nil, fmt.Errorf("failed to create backup: %w", err)
	}

	// Get file size
	fileInfo, err := os.Stat(backupPath)
	if err != nil {
		return nil, fmt.Errorf("failed to get backup size: %w", err)
	}

	// Store backup metadata
	metadata := models.BackupDescription{
		BackupArn:       backupArn,
		BackupName:      backupName,
		BackupStatus:    "AVAILABLE",
		BackupType:      "USER",
		BackupSizeBytes: fileInfo.Size(),
		CreationDate:    time.Now().Unix(),
		TableArn:        fmt.Sprintf("arn:aws:dynamodb:local:000000000000:table/%s", req.TableName),
		TableName:       req.TableName,
	}

	if err := tm.storeBackupMetadata(metadata); err != nil {
		return nil, fmt.Errorf("failed to store backup metadata: %w", err)
	}

	return &metadata, nil
}

// ListBackups lists all backups.
func (tm *TableManager) ListBackups(req *models.ListBackupsRequest) ([]models.BackupDescription, error) {
	backups, err := tm.loadBackupMetadata()
	if err != nil {
		return nil, err
	}

	// Filter by table name if specified
	var filtered []models.BackupDescription
	for _, backup := range backups {
		if req.TableName != "" && backup.TableName != req.TableName {
			continue
		}
		if req.BackupType != "" && req.BackupType != "ALL" && backup.BackupType != req.BackupType {
			continue
		}
		filtered = append(filtered, backup)
	}

	// Apply limit
	if req.Limit > 0 && len(filtered) > req.Limit {
		filtered = filtered[:req.Limit]
	}

	return filtered, nil
}

// DescribeBackup describes a backup.
func (tm *TableManager) DescribeBackup(backupArn string) (*models.BackupDescription, error) {
	backups, err := tm.loadBackupMetadata()
	if err != nil {
		return nil, err
	}

	// Find backup by ARN
	for i := range backups {
		if backups[i].BackupArn == backupArn {
			return &backups[i], nil
		}
	}

	return nil, fmt.Errorf("backup not found: %s", backupArn)
}

// DeleteBackup deletes a backup.
func (tm *TableManager) DeleteBackup(backupArn string) (*models.BackupDescription, error) {
	// Find backup metadata
	backups, err := tm.loadBackupMetadata()
	if err != nil {
		return nil, err
	}

	var backup *models.BackupDescription
	var index int
	for i, b := range backups {
		if b.BackupArn == backupArn {
			backup = &backups[i]
			index = i
			break
		}
	}

	if backup == nil {
		return nil, fmt.Errorf("backup not found: %s", backupArn)
	}

	// Delete backup file
	backupDir := filepath.Join(tm.dataDirectory, tm.namespace, "backups")
	backupFileName := fmt.Sprintf("%s_%s.db", backup.TableName, backup.BackupName)
	backupPath := filepath.Join(backupDir, backupFileName)

	if err := os.Remove(backupPath); err != nil && !os.IsNotExist(err) {
		return nil, fmt.Errorf("failed to delete backup file: %w", err)
	}

	// Update metadata
	backup.BackupStatus = "DELETED"

	// Remove from list
	backups = append(backups[:index], backups[index+1:]...)
	if err := tm.saveBackupMetadata(backups); err != nil {
		return nil, err
	}

	return backup, nil
}

// RestoreTableFromBackup restores a table from a backup.
func (tm *TableManager) RestoreTableFromBackup(req *models.RestoreTableFromBackupRequest) (*models.TableMetadata, error) {
	// Find backup
	backups, err := tm.loadBackupMetadata()
	if err != nil {
		return nil, err
	}

	var backup *models.BackupDescription
	for i, b := range backups {
		if b.BackupArn == req.BackupArn {
			backup = &backups[i]
			break
		}
	}

	if backup == nil {
		return nil, fmt.Errorf("backup not found: %s", req.BackupArn)
	}

	// Check if target table exists
	targetDBPath := tm.getDBPath(req.TargetTableName)
	if _, err := os.Stat(targetDBPath); err == nil {
		return nil, fmt.Errorf("target table already exists: %s", req.TargetTableName)
	}

	// Copy backup to new table
	backupDir := filepath.Join(tm.dataDirectory, tm.namespace, "backups")
	backupFileName := fmt.Sprintf("%s_%s.db", backup.TableName, backup.BackupName)
	backupPath := filepath.Join(backupDir, backupFileName)

	if err := tm.copyFile(backupPath, targetDBPath); err != nil {
		return nil, fmt.Errorf("failed to restore table: %w", err)
	}

	// Get metadata from restored table
	metadata, err := tm.DescribeTable(req.TargetTableName)
	if err != nil {
		return nil, fmt.Errorf("failed to get restored table metadata: %w", err)
	}

	// Update table name in metadata
	metadata.TableName = req.TargetTableName
	metadata.TableARN = fmt.Sprintf("arn:aws:dynamodb:local:%s:table/%s", tm.namespace, req.TargetTableName)

	// Store updated metadata
	db, err := sql.Open("sqlite3", targetDBPath)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	if err := tm.storeTableMetadata(db, metadata); err != nil {
		return nil, err
	}

	return metadata, nil
}

// copyFile copies a file from source to destination.
func (tm *TableManager) copyFile(src, dst string) error {
	sourceFile, err := os.Open(src)
	if err != nil {
		return err
	}
	defer sourceFile.Close()

	destFile, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer destFile.Close()

	_, err = destFile.ReadFrom(sourceFile)
	return err
}

// storeBackupMetadata stores backup metadata.
func (tm *TableManager) storeBackupMetadata(backup models.BackupDescription) error {
	backups, err := tm.loadBackupMetadata()
	if err != nil {
		backups = []models.BackupDescription{}
	}

	backups = append(backups, backup)
	return tm.saveBackupMetadata(backups)
}

// loadBackupMetadata loads all backup metadata.
func (tm *TableManager) loadBackupMetadata() ([]models.BackupDescription, error) {
	metadataPath := filepath.Join(tm.dataDirectory, tm.namespace, "backups", "metadata.json")

	data, err := os.ReadFile(metadataPath)
	if err != nil {
		if os.IsNotExist(err) {
			return []models.BackupDescription{}, nil
		}
		return nil, err
	}

	var backups []models.BackupDescription
	if err := json.Unmarshal(data, &backups); err != nil {
		return nil, err
	}

	return backups, nil
}

// saveBackupMetadata saves all backup metadata.
func (tm *TableManager) saveBackupMetadata(backups []models.BackupDescription) error {
	backupDir := filepath.Join(tm.dataDirectory, tm.namespace, "backups")
	if err := os.MkdirAll(backupDir, 0755); err != nil {
		return err
	}

	metadataPath := filepath.Join(backupDir, "metadata.json")
	data, err := json.Marshal(backups)
	if err != nil {
		return err
	}

	return os.WriteFile(metadataPath, data, 0644)
}
