// Package storage provides tests for ListTables pagination.
package storage

import (
	"os"
	"testing"

	"github.com/e6qu/dyscount/internal/models"
)

func TestTableManager_ListTablesWithPagination(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-listtables-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	// Create multiple test tables
	tableNames := []string{"TableA", "TableB", "TableC", "TableD", "TableE"}
	for _, name := range tableNames {
		req := &models.DynamoDBRequest{
			TableName: name,
			KeySchema: []models.KeySchemaElement{
				{AttributeName: "pk", KeyType: "HASH"},
			},
			AttributeDefinitions: []models.AttributeDefinition{
				{AttributeName: "pk", AttributeType: "S"},
			},
		}
		_, err := tm.CreateTable(req)
		if err != nil {
			t.Fatalf("Failed to create table %s: %v", name, err)
		}
	}

	t.Run("List All Tables Without Pagination", func(t *testing.T) {
		tables, lastTable, err := tm.ListTablesWithPagination(0, "")
		if err != nil {
			t.Fatalf("Failed to list tables: %v", err)
		}

		if len(tables) != 5 {
			t.Errorf("Expected 5 tables, got %d", len(tables))
		}

		if lastTable != "" {
			t.Errorf("Expected no last table, got %s", lastTable)
		}
	})

	t.Run("List Tables With Limit", func(t *testing.T) {
		tables, lastTable, err := tm.ListTablesWithPagination(2, "")
		if err != nil {
			t.Fatalf("Failed to list tables: %v", err)
		}

		if len(tables) != 2 {
			t.Errorf("Expected 2 tables, got %d", len(tables))
		}

		if lastTable == "" {
			t.Error("Expected last table to be set")
		}

		// Tables should be sorted alphabetically
		if tables[0] != "TableA" {
			t.Errorf("Expected first table to be TableA, got %s", tables[0])
		}
		if tables[1] != "TableB" {
			t.Errorf("Expected second table to be TableB, got %s", tables[1])
		}
	})

	t.Run("List Tables With Pagination", func(t *testing.T) {
		// First page
		tables1, lastTable1, err := tm.ListTablesWithPagination(2, "")
		if err != nil {
			t.Fatalf("Failed to list tables (page 1): %v", err)
		}

		if len(tables1) != 2 {
			t.Fatalf("Expected 2 tables on page 1, got %d", len(tables1))
		}

		if lastTable1 == "" {
			t.Fatal("Expected last table on page 1")
		}

		// Second page using last table from first page
		tables2, lastTable2, err := tm.ListTablesWithPagination(2, lastTable1)
		if err != nil {
			t.Fatalf("Failed to list tables (page 2): %v", err)
		}

		if len(tables2) != 2 {
			t.Errorf("Expected 2 tables on page 2, got %d", len(tables2))
		}

		if lastTable2 == "" {
			t.Error("Expected last table on page 2")
		}

		// Third page
		tables3, lastTable3, err := tm.ListTablesWithPagination(2, lastTable2)
		if err != nil {
			t.Fatalf("Failed to list tables (page 3): %v", err)
		}

		if len(tables3) != 1 {
			t.Errorf("Expected 1 table on page 3, got %d", len(tables3))
		}

		if lastTable3 != "" {
			t.Error("Expected no last table on final page")
		}

		// Verify all tables are different
		allTables := append(append(tables1, tables2...), tables3...)
		if len(allTables) != 5 {
			t.Errorf("Expected 5 total tables, got %d", len(allTables))
		}

		tableMap := make(map[string]bool)
		for _, name := range allTables {
			if tableMap[name] {
				t.Errorf("Table %s appears multiple times", name)
			}
			tableMap[name] = true
		}
	})

	t.Run("List Tables Empty Directory", func(t *testing.T) {
		// Create new empty directory
		emptyDir, err := os.MkdirTemp("", "dyscount-empty-test-*")
		if err != nil {
			t.Fatalf("Failed to create empty temp dir: %v", err)
		}
		defer os.RemoveAll(emptyDir)

		tm2, err := NewTableManager(emptyDir, "default")
		if err != nil {
			t.Fatalf("Failed to create table manager: %v", err)
		}

		tables, lastTable, err := tm2.ListTablesWithPagination(0, "")
		if err != nil {
			t.Fatalf("Failed to list tables: %v", err)
		}

		if len(tables) != 0 {
			t.Errorf("Expected 0 tables, got %d", len(tables))
		}

		if lastTable != "" {
			t.Errorf("Expected no last table, got %s", lastTable)
		}
	})

	t.Run("List Tables With NonExistent Start", func(t *testing.T) {
		// Use a table name that doesn't exist as exclusive start
		tables, lastTable, err := tm.ListTablesWithPagination(0, "NonExistentTable")
		if err != nil {
			t.Fatalf("Failed to list tables: %v", err)
		}

		// When exclusive start is not found, return empty (DynamoDB behavior)
		if len(tables) != 0 {
			t.Errorf("Expected 0 tables when start not found, got %d", len(tables))
		}

		if lastTable != "" {
			t.Errorf("Expected no last table, got %s", lastTable)
		}
	})

	t.Run("List Tables Pagination Loop", func(t *testing.T) {
		var allTables []string
		var exclusiveStartTableName string
		pageCount := 0

		for {
			pageCount++
			if pageCount > 10 {
				t.Fatal("Too many pages, possible infinite loop")
			}

			tables, lastTable, err := tm.ListTablesWithPagination(2, exclusiveStartTableName)
			if err != nil {
				t.Fatalf("Failed to list tables: %v", err)
			}

			allTables = append(allTables, tables...)

			if lastTable == "" {
				break
			}
			exclusiveStartTableName = lastTable
		}

		if len(allTables) != 5 {
			t.Errorf("Expected 5 total tables, got %d", len(allTables))
		}

		if pageCount != 3 {
			t.Errorf("Expected 3 pages, got %d", pageCount)
		}
	})
}
