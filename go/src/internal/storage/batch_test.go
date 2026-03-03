// Package storage provides tests for batch operations.
package storage

import (
	"os"
	"testing"

	"github.com/e6qu/dyscount/internal/models"
)

func TestItemManager_BatchGetItem(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-batch-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	im := NewItemManager(tm)

	// Create test table
	req := &models.DynamoDBRequest{
		TableName: "TestTable",
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

	// Put some test items
	items := []models.Item{
		{"pk": models.NewStringAttribute("key1"), "data": models.NewStringAttribute("value1")},
		{"pk": models.NewStringAttribute("key2"), "data": models.NewStringAttribute("value2")},
		{"pk": models.NewStringAttribute("key3"), "data": models.NewStringAttribute("value3")},
	}

	for _, item := range items {
		_, err := im.PutItem("TestTable", item, false)
		if err != nil {
			t.Fatalf("Failed to put item: %v", err)
		}
	}

	tests := []struct {
		name            string
		requests        map[string]models.KeysAndAttributes
		expectedCount   int
		unprocessedKeys int
	}{
		{
			name: "Get existing items",
			requests: map[string]models.KeysAndAttributes{
				"TestTable": {
					Keys: []models.Item{
						{"pk": models.NewStringAttribute("key1")},
						{"pk": models.NewStringAttribute("key2")},
					},
				},
			},
			expectedCount:   2,
			unprocessedKeys: 0,
		},
		{
			name: "Get mix of existing and non-existing",
			requests: map[string]models.KeysAndAttributes{
				"TestTable": {
					Keys: []models.Item{
						{"pk": models.NewStringAttribute("key1")},
						{"pk": models.NewStringAttribute("nonexistent")},
					},
				},
			},
			expectedCount:   1,
			unprocessedKeys: 0,
		},
		{
			name: "Get from non-existent table",
			requests: map[string]models.KeysAndAttributes{
				"NonExistentTable": {
					Keys: []models.Item{
						{"pk": models.NewStringAttribute("key1")},
					},
				},
			},
			expectedCount:   0,
			unprocessedKeys: 1,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			responses, unprocessed, err := im.BatchGetItem(tt.requests)
			if err != nil {
				t.Errorf("Unexpected error: %v", err)
				return
			}

			// Count total items returned
			totalItems := 0
			for _, items := range responses {
				totalItems += len(items)
			}

			if totalItems != tt.expectedCount {
				t.Errorf("Expected %d items, got %d", tt.expectedCount, totalItems)
			}

			if len(unprocessed) != tt.unprocessedKeys {
				t.Errorf("Expected %d unprocessed keys, got %d", tt.unprocessedKeys, len(unprocessed))
			}
		})
	}
}

func TestItemManager_BatchWriteItem(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-batch-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	im := NewItemManager(tm)

	// Create test table
	req := &models.DynamoDBRequest{
		TableName: "TestTable",
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

	// Pre-populate with an item to delete
	_, err = im.PutItem("TestTable", models.Item{
		"pk":   models.NewStringAttribute("delete_me"),
		"data": models.NewStringAttribute("to_delete"),
	}, false)
	if err != nil {
		t.Fatalf("Failed to put item: %v", err)
	}

	tests := []struct {
		name              string
		requests          map[string][]models.WriteRequest
		expectedProcessed int
		expectedUnproc    int
	}{
		{
			name: "Put multiple items",
			requests: map[string][]models.WriteRequest{
				"TestTable": {
					{PutRequest: &models.PutRequest{Item: models.Item{
						"pk":   models.NewStringAttribute("new1"),
						"data": models.NewStringAttribute("value1"),
					}}},
					{PutRequest: &models.PutRequest{Item: models.Item{
						"pk":   models.NewStringAttribute("new2"),
						"data": models.NewStringAttribute("value2"),
					}}},
				},
			},
			expectedProcessed: 2,
			expectedUnproc:    0,
		},
		{
			name: "Delete items",
			requests: map[string][]models.WriteRequest{
				"TestTable": {
					{DeleteRequest: &models.DeleteRequest{Key: models.Item{
						"pk": models.NewStringAttribute("delete_me"),
					}}},
				},
			},
			expectedProcessed: 1,
			expectedUnproc:    0,
		},
		{
			name: "Mixed put and delete",
			requests: map[string][]models.WriteRequest{
				"TestTable": {
					{PutRequest: &models.PutRequest{Item: models.Item{
						"pk":   models.NewStringAttribute("mixed1"),
						"data": models.NewStringAttribute("value1"),
					}}},
					{DeleteRequest: &models.DeleteRequest{Key: models.Item{
						"pk": models.NewStringAttribute("mixed1"),
					}}},
				},
			},
			expectedProcessed: 2,
			expectedUnproc:    0,
		},
		{
			name: "Write to non-existent table",
			requests: map[string][]models.WriteRequest{
				"NonExistentTable": {
					{PutRequest: &models.PutRequest{Item: models.Item{
						"pk":   models.NewStringAttribute("new1"),
						"data": models.NewStringAttribute("value1"),
					}}},
				},
			},
			expectedProcessed: 0,
			expectedUnproc:    1,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			unprocessed, err := im.BatchWriteItem(tt.requests)
			if err != nil {
				t.Errorf("Unexpected error: %v", err)
				return
			}

			// Count total unprocessed items
			totalUnprocessed := 0
			for _, items := range unprocessed {
				totalUnprocessed += len(items)
			}

			if totalUnprocessed != tt.expectedUnproc {
				t.Errorf("Expected %d unprocessed items, got %d", tt.expectedUnproc, totalUnprocessed)
			}
		})
	}
}

func TestItemManager_BatchWriteItem_ExceedsLimit(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-batch-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	im := NewItemManager(tm)

	// Create test table
	req := &models.DynamoDBRequest{
		TableName: "TestTable",
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

	// Create 30 put requests (exceeds limit of 25)
	var writeRequests []models.WriteRequest
	for i := 0; i < 30; i++ {
		writeRequests = append(writeRequests, models.WriteRequest{
			PutRequest: &models.PutRequest{Item: models.Item{
				"pk": models.NewStringAttribute("key" + string(rune('a'+i%26))),
			}},
		})
	}

	requests := map[string][]models.WriteRequest{
		"TestTable": writeRequests,
	}

	_, err = im.BatchWriteItem(requests)
	if err == nil {
		t.Error("Expected error for batch exceeding limit")
	}
}
