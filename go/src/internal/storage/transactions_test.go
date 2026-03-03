// Package storage provides tests for transaction operations.
package storage

import (
	"os"
	"testing"

	"github.com/e6qu/dyscount/internal/models"
)

func TestItemManager_TransactGetItems(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-transact-test-*")
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
	}

	for _, item := range items {
		_, err := im.PutItem("TestTable", item, false)
		if err != nil {
			t.Fatalf("Failed to put item: %v", err)
		}
	}

	tests := []struct {
		name          string
		transactItems []models.TransactGetItem
		expectedCount int
		expectError   bool
	}{
		{
			name: "Get existing items",
			transactItems: []models.TransactGetItem{
				{Get: &models.TransactGet{TableName: "TestTable", Key: models.Item{"pk": models.NewStringAttribute("key1")}}},
				{Get: &models.TransactGet{TableName: "TestTable", Key: models.Item{"pk": models.NewStringAttribute("key2")}}},
			},
			expectedCount: 2,
			expectError:   false,
		},
		{
			name: "Get mix of existing and non-existing",
			transactItems: []models.TransactGetItem{
				{Get: &models.TransactGet{TableName: "TestTable", Key: models.Item{"pk": models.NewStringAttribute("key1")}}},
				{Get: &models.TransactGet{TableName: "TestTable", Key: models.Item{"pk": models.NewStringAttribute("nonexistent")}}},
			},
			expectedCount: 2,
			expectError:   false,
		},
		{
			name:          "Empty items",
			transactItems: []models.TransactGetItem{},
			expectedCount: 0,
			expectError:   false, // Empty items returns empty result (validation is in handler)
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			responses, err := im.TransactGetItems(tt.transactItems)

			if tt.expectError {
				if err == nil {
					t.Error("Expected error but got none")
				}
				return
			}

			if err != nil {
				t.Errorf("Unexpected error: %v", err)
				return
			}

			if len(responses) != tt.expectedCount {
				t.Errorf("Expected %d responses, got %d", tt.expectedCount, len(responses))
			}
		})
	}
}

func TestItemManager_TransactWriteItems_Put(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-transact-test-*")
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

	// Test transact put
	transactItems := []models.TransactWriteItem{
		{
			Put: &models.TransactPut{
				TableName: "TestTable",
				Item: models.Item{
					"pk":   models.NewStringAttribute("transact1"),
					"data": models.NewStringAttribute("value1"),
				},
			},
		},
		{
			Put: &models.TransactPut{
				TableName: "TestTable",
				Item: models.Item{
					"pk":   models.NewStringAttribute("transact2"),
					"data": models.NewStringAttribute("value2"),
				},
			},
		},
	}

	err = im.TransactWriteItems(transactItems)
	if err != nil {
		t.Errorf("Unexpected error: %v", err)
	}

	// Verify items were written
	item1, err := im.GetItem("TestTable", models.Item{"pk": models.NewStringAttribute("transact1")}, false)
	if err != nil {
		t.Errorf("Failed to get item1: %v", err)
	}
	if item1 == nil {
		t.Error("Item1 was not written")
	}

	item2, err := im.GetItem("TestTable", models.Item{"pk": models.NewStringAttribute("transact2")}, false)
	if err != nil {
		t.Errorf("Failed to get item2: %v", err)
	}
	if item2 == nil {
		t.Error("Item2 was not written")
	}
}

func TestItemManager_TransactWriteItems_Delete(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-transact-test-*")
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

	// Pre-populate item
	_, err = im.PutItem("TestTable", models.Item{
		"pk":   models.NewStringAttribute("delete_me"),
		"data": models.NewStringAttribute("to_delete"),
	}, false)
	if err != nil {
		t.Fatalf("Failed to put item: %v", err)
	}

	// Test transact delete
	transactItems := []models.TransactWriteItem{
		{
			Delete: &models.TransactDelete{
				TableName: "TestTable",
				Key: models.Item{
					"pk": models.NewStringAttribute("delete_me"),
				},
			},
		},
	}

	err = im.TransactWriteItems(transactItems)
	if err != nil {
		t.Errorf("Unexpected error: %v", err)
	}

	// Verify item was deleted
	item, err := im.GetItem("TestTable", models.Item{"pk": models.NewStringAttribute("delete_me")}, false)
	if err != nil {
		t.Errorf("Failed to get item: %v", err)
	}
	if item != nil {
		t.Error("Item was not deleted")
	}
}

func TestItemManager_TransactWriteItems_ConditionCheck(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-transact-test-*")
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

	// Pre-populate item
	_, err = im.PutItem("TestTable", models.Item{
		"pk":     models.NewStringAttribute("check_me"),
		"status": models.NewStringAttribute("active"),
	}, false)
	if err != nil {
		t.Fatalf("Failed to put item: %v", err)
	}

	// Test transact condition check (passing)
	transactItems := []models.TransactWriteItem{
		{
			ConditionCheck: &models.TransactConditionCheck{
				TableName:              "TestTable",
				Key:                    models.Item{"pk": models.NewStringAttribute("check_me")},
				ConditionExpression:    "#s = :val",
				ExpressionAttributeNames: map[string]string{"#s": "status"},
				ExpressionAttributeValues: map[string]models.AttributeValue{":val": models.NewStringAttribute("active")},
			},
		},
	}

	err = im.TransactWriteItems(transactItems)
	if err != nil {
		t.Errorf("Unexpected error: %v", err)
	}
}

func TestItemManager_TransactWriteItems_Mixed(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-transact-test-*")
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

	// Pre-populate item to delete
	_, err = im.PutItem("TestTable", models.Item{
		"pk":   models.NewStringAttribute("old_item"),
		"data": models.NewStringAttribute("old_value"),
	}, false)
	if err != nil {
		t.Fatalf("Failed to put item: %v", err)
	}

	// Test mixed transact operations
	transactItems := []models.TransactWriteItem{
		{
			Put: &models.TransactPut{
				TableName: "TestTable",
				Item: models.Item{
					"pk":   models.NewStringAttribute("new_item"),
					"data": models.NewStringAttribute("new_value"),
				},
			},
		},
		{
			Delete: &models.TransactDelete{
				TableName: "TestTable",
				Key: models.Item{
					"pk": models.NewStringAttribute("old_item"),
				},
			},
		},
	}

	err = im.TransactWriteItems(transactItems)
	if err != nil {
		t.Errorf("Unexpected error: %v", err)
	}

	// Verify new item exists
	newItem, err := im.GetItem("TestTable", models.Item{"pk": models.NewStringAttribute("new_item")}, false)
	if err != nil {
		t.Errorf("Failed to get new item: %v", err)
	}
	if newItem == nil {
		t.Error("New item was not written")
	}

	// Verify old item deleted
	oldItem, err := im.GetItem("TestTable", models.Item{"pk": models.NewStringAttribute("old_item")}, false)
	if err != nil {
		t.Errorf("Failed to get old item: %v", err)
	}
	if oldItem != nil {
		t.Error("Old item was not deleted")
	}
}

func TestItemManager_TransactWriteItems_ExceedsLimit(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-transact-test-*")
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
	var transactItems []models.TransactWriteItem
	for i := 0; i < 30; i++ {
		transactItems = append(transactItems, models.TransactWriteItem{
			Put: &models.TransactPut{
				TableName: "TestTable",
				Item: models.Item{
					"pk": models.NewStringAttribute("key" + string(rune('a'+i%26))),
				},
			},
		})
	}

	err = im.TransactWriteItems(transactItems)
	if err == nil {
		t.Error("Expected error for transaction exceeding limit")
	}
}

func TestItemManager_TransactWriteItems_NonExistentTable(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-transact-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	im := NewItemManager(tm)

	// Test transact write to non-existent table
	transactItems := []models.TransactWriteItem{
		{
			Put: &models.TransactPut{
				TableName: "NonExistentTable",
				Item: models.Item{
					"pk":   models.NewStringAttribute("item1"),
					"data": models.NewStringAttribute("value1"),
				},
			},
		},
	}

	err = im.TransactWriteItems(transactItems)
	if err == nil {
		t.Error("Expected error for non-existent table")
	}
}
