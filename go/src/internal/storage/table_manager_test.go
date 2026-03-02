package storage

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/e6qu/dyscount/internal/models"
)

func TestTableManager(t *testing.T) {
	// Create temporary directory for test data
	tempDir, err := os.MkdirTemp("", "dyscount-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	// Create table manager
	tm, err := NewTableManager(tempDir, "test")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	t.Run("CreateTable", func(t *testing.T) {
		req := &models.DynamoDBRequest{
			TableName: "TestTable",
			KeySchema: []models.KeySchemaElement{
				{AttributeName: "pk", KeyType: "HASH"},
			},
			AttributeDefinitions: []models.AttributeDefinition{
				{AttributeName: "pk", AttributeType: "S"},
			},
		}

		metadata, err := tm.CreateTable(req)
		if err != nil {
			t.Fatalf("Failed to create table: %v", err)
		}

		if metadata.TableName != "TestTable" {
			t.Errorf("Expected table name TestTable, got %s", metadata.TableName)
		}

		if metadata.TableStatus != "ACTIVE" {
			t.Errorf("Expected status ACTIVE, got %s", metadata.TableStatus)
		}
	})

	t.Run("CreateTable_Duplicate", func(t *testing.T) {
		req := &models.DynamoDBRequest{
			TableName: "TestTable",
			KeySchema: []models.KeySchemaElement{
				{AttributeName: "pk", KeyType: "HASH"},
			},
			AttributeDefinitions: []models.AttributeDefinition{
				{AttributeName: "pk", AttributeType: "S"},
			},
		}

		_, err := tm.CreateTable(req)
		if err == nil {
			t.Error("Expected error for duplicate table, got nil")
		}
	})

	t.Run("ListTables", func(t *testing.T) {
		tables, err := tm.ListTables()
		if err != nil {
			t.Fatalf("Failed to list tables: %v", err)
		}

		if len(tables) != 1 {
			t.Errorf("Expected 1 table, got %d", len(tables))
		}

		if tables[0] != "TestTable" {
			t.Errorf("Expected table TestTable, got %s", tables[0])
		}
	})

	t.Run("DescribeTable", func(t *testing.T) {
		metadata, err := tm.DescribeTable("TestTable")
		if err != nil {
			t.Fatalf("Failed to describe table: %v", err)
		}

		if metadata.TableName != "TestTable" {
			t.Errorf("Expected table name TestTable, got %s", metadata.TableName)
		}
	})

	t.Run("DescribeTable_NotFound", func(t *testing.T) {
		_, err := tm.DescribeTable("NonExistentTable")
		if err == nil {
			t.Error("Expected error for non-existent table, got nil")
		}
	})

	t.Run("DeleteTable", func(t *testing.T) {
		metadata, err := tm.DeleteTable("TestTable")
		if err != nil {
			t.Fatalf("Failed to delete table: %v", err)
		}

		if metadata == nil {
			t.Error("Expected metadata for deleted table, got nil")
		}

		if metadata.TableName != "TestTable" {
			t.Errorf("Expected table name TestTable, got %s", metadata.TableName)
		}
	})

	t.Run("DeleteTable_NotFound", func(t *testing.T) {
		metadata, err := tm.DeleteTable("NonExistentTable")
		if err != nil {
			t.Fatalf("Unexpected error: %v", err)
		}

		if metadata != nil {
			t.Error("Expected nil metadata for non-existent table")
		}
	})

	t.Run("ListTables_AfterDelete", func(t *testing.T) {
		tables, err := tm.ListTables()
		if err != nil {
			t.Fatalf("Failed to list tables: %v", err)
		}

		if len(tables) != 0 {
			t.Errorf("Expected 0 tables, got %d", len(tables))
		}
	})
}

func TestTableManager_WithGSI(t *testing.T) {
	// Create temporary directory for test data
	tempDir, err := os.MkdirTemp("", "dyscount-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	// Create table manager
	tm, err := NewTableManager(tempDir, "test")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	t.Run("CreateTable_WithGSI", func(t *testing.T) {
		req := &models.DynamoDBRequest{
			TableName: "TestTableWithGSI",
			KeySchema: []models.KeySchemaElement{
				{AttributeName: "pk", KeyType: "HASH"},
			},
			AttributeDefinitions: []models.AttributeDefinition{
				{AttributeName: "pk", AttributeType: "S"},
				{AttributeName: "gsi_pk", AttributeType: "S"},
			},
			GlobalSecondaryIndexes: []models.GlobalSecondaryIndex{
				{
					IndexName: "TestGSI",
					KeySchema: []models.KeySchemaElement{
						{AttributeName: "gsi_pk", KeyType: "HASH"},
					},
					Projection: models.Projection{
						ProjectionType: "ALL",
					},
				},
			},
		}

		metadata, err := tm.CreateTable(req)
		if err != nil {
			t.Fatalf("Failed to create table with GSI: %v", err)
		}

		if len(metadata.GlobalSecondaryIndexes) != 1 {
			t.Errorf("Expected 1 GSI, got %d", len(metadata.GlobalSecondaryIndexes))
		}

		if metadata.GlobalSecondaryIndexes[0].IndexName != "TestGSI" {
			t.Errorf("Expected GSI name TestGSI, got %s", metadata.GlobalSecondaryIndexes[0].IndexName)
		}
	})
}

func TestTableManager_DatabaseFile(t *testing.T) {
	// Create temporary directory for test data
	tempDir, err := os.MkdirTemp("", "dyscount-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	// Create table manager
	tm, err := NewTableManager(tempDir, "test")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	// Create a table
	req := &models.DynamoDBRequest{
		TableName: "FileTestTable",
		KeySchema: []models.KeySchemaElement{
			{AttributeName: "pk", KeyType: "HASH"},
		},
		AttributeDefinitions: []models.AttributeDefinition{
			{AttributeName: "pk", AttributeType: "S"},
		},
	}

	_, err = tm.CreateTable(req)
	if err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Check that database file was created
	dbPath := filepath.Join(tempDir, "test", "FileTestTable.db")
	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		t.Errorf("Database file not created at %s", dbPath)
	}
}
