package storage

import (
	"fmt"
	"os"
	"testing"

	"github.com/e6qu/dyscount/internal/models"
)

// setupTestItemManager creates a temporary table manager and item manager for testing.
func setupTestItemManager(t *testing.T) (*ItemManager, *TableManager, func()) {
	tmpDir, err := os.MkdirTemp("", "dyscount_item_test")
	if err != nil {
		t.Fatalf("Failed to create temp directory: %v", err)
	}

	tm, err := NewTableManager(tmpDir, "test")
	if err != nil {
		os.RemoveAll(tmpDir)
		t.Fatalf("Failed to create table manager: %v", err)
	}

	im := NewItemManager(tm)

	cleanup := func() {
		os.RemoveAll(tmpDir)
	}

	return im, tm, cleanup
}

// createTestTable creates a simple test table with the specified name and key schema.
func createTestTable(tm *TableManager, name string, hashKey string, rangeKey string) error {
	req := &models.DynamoDBRequest{
		TableName: name,
		KeySchema: []models.KeySchemaElement{
			{AttributeName: hashKey, KeyType: "HASH"},
		},
		AttributeDefinitions: []models.AttributeDefinition{
			{AttributeName: hashKey, AttributeType: "S"},
		},
	}

	if rangeKey != "" {
		req.KeySchema = append(req.KeySchema, models.KeySchemaElement{
			AttributeName: rangeKey, KeyType: "RANGE",
		})
		req.AttributeDefinitions = append(req.AttributeDefinitions, models.AttributeDefinition{
			AttributeName: rangeKey, AttributeType: "S",
		})
	}

	_, err := tm.CreateTable(req)
	return err
}

func TestItemManager_PutItem(t *testing.T) {
	im, tm, cleanup := setupTestItemManager(t)
	defer cleanup()

	// Create test table
	if err := createTestTable(tm, "TestTable", "pk", "sk"); err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	t.Run("PutItem New Item", func(t *testing.T) {
		item := models.Item{
			"pk": models.NewStringAttribute("user1"),
			"sk": models.NewStringAttribute("profile"),
			"name": models.NewStringAttribute("John Doe"),
			"age": models.NewNumberAttribute("30"),
		}

		oldItem, err := im.PutItem("TestTable", item, false)
		if err != nil {
			t.Fatalf("PutItem failed: %v", err)
		}
		if oldItem != nil {
			t.Error("Expected nil old item for new item")
		}
	})

	t.Run("PutItem Update Existing", func(t *testing.T) {
		// First put
		item := models.Item{
			"pk": models.NewStringAttribute("user2"),
			"sk": models.NewStringAttribute("profile"),
			"name": models.NewStringAttribute("Original Name"),
		}
		im.PutItem("TestTable", item, false)

		// Update with return old
		updatedItem := models.Item{
			"pk": models.NewStringAttribute("user2"),
			"sk": models.NewStringAttribute("profile"),
			"name": models.NewStringAttribute("Updated Name"),
		}

		oldItem, err := im.PutItem("TestTable", updatedItem, true)
		if err != nil {
			t.Fatalf("PutItem failed: %v", err)
		}
		if oldItem == nil {
			t.Fatal("Expected old item")
		}
		if name, ok := oldItem["name"].GetString(); !ok || name != "Original Name" {
			t.Errorf("Expected old name 'Original Name', got %v", name)
		}
	})

	t.Run("PutItem Non-existent Table", func(t *testing.T) {
		item := models.Item{
			"pk": models.NewStringAttribute("user1"),
			"sk": models.NewStringAttribute("profile"),
		}

		_, err := im.PutItem("NonExistentTable", item, false)
		if err == nil {
			t.Error("Expected error for non-existent table")
		}
	})
}

func TestItemManager_GetItem(t *testing.T) {
	im, tm, cleanup := setupTestItemManager(t)
	defer cleanup()

	// Create test table
	if err := createTestTable(tm, "TestTable", "pk", "sk"); err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Insert test item
	testItem := models.Item{
		"pk": models.NewStringAttribute("user1"),
		"sk": models.NewStringAttribute("profile"),
		"name": models.NewStringAttribute("John Doe"),
		"age": models.NewNumberAttribute("30"),
	}
	im.PutItem("TestTable", testItem, false)

	t.Run("GetItem Existing", func(t *testing.T) {
		key := models.Item{
			"pk": models.NewStringAttribute("user1"),
			"sk": models.NewStringAttribute("profile"),
		}

		item, err := im.GetItem("TestTable", key, true)
		if err != nil {
			t.Fatalf("GetItem failed: %v", err)
		}
		if item == nil {
			t.Fatal("Expected item, got nil")
		}

		if name, ok := item["name"].GetString(); !ok || name != "John Doe" {
			t.Errorf("Expected name 'John Doe', got %v", name)
		}
	})

	t.Run("GetItem Non-existent", func(t *testing.T) {
		key := models.Item{
			"pk": models.NewStringAttribute("nonexistent"),
			"sk": models.NewStringAttribute("profile"),
		}

		item, err := im.GetItem("TestTable", key, true)
		if err != nil {
			t.Fatalf("GetItem failed: %v", err)
		}
		if item != nil {
			t.Error("Expected nil for non-existent item")
		}
	})

	t.Run("GetItem Hash Only Table", func(t *testing.T) {
		// Create hash-only table
		if err := createTestTable(tm, "HashOnlyTable", "id", ""); err != nil {
			t.Fatalf("Failed to create hash-only table: %v", err)
		}

		hashItem := models.Item{
			"id": models.NewStringAttribute("item1"),
			"data": models.NewStringAttribute("some data"),
		}
		im.PutItem("HashOnlyTable", hashItem, false)

		key := models.Item{
			"id": models.NewStringAttribute("item1"),
		}

		item, err := im.GetItem("HashOnlyTable", key, true)
		if err != nil {
			t.Fatalf("GetItem failed: %v", err)
		}
		if item == nil {
			t.Fatal("Expected item, got nil")
		}

		if data, ok := item["data"].GetString(); !ok || data != "some data" {
			t.Errorf("Expected data 'some data', got %v", data)
		}
	})
}

func TestItemManager_DeleteItem(t *testing.T) {
	im, tm, cleanup := setupTestItemManager(t)
	defer cleanup()

	// Create test table
	if err := createTestTable(tm, "TestTable", "pk", "sk"); err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Insert test item
	testItem := models.Item{
		"pk": models.NewStringAttribute("user1"),
		"sk": models.NewStringAttribute("profile"),
		"name": models.NewStringAttribute("John Doe"),
	}
	im.PutItem("TestTable", testItem, false)

	t.Run("DeleteItem Existing", func(t *testing.T) {
		key := models.Item{
			"pk": models.NewStringAttribute("user1"),
			"sk": models.NewStringAttribute("profile"),
		}

		_, err := im.DeleteItem("TestTable", key, false)
		if err != nil {
			t.Fatalf("DeleteItem failed: %v", err)
		}

		// Verify item is deleted
		item, _ := im.GetItem("TestTable", key, true)
		if item != nil {
			t.Error("Expected item to be deleted")
		}
	})

	t.Run("DeleteItem Return Old", func(t *testing.T) {
		// Insert item
		item := models.Item{
			"pk": models.NewStringAttribute("user2"),
			"sk": models.NewStringAttribute("profile"),
			"name": models.NewStringAttribute("Jane Doe"),
		}
		im.PutItem("TestTable", item, false)

		key := models.Item{
			"pk": models.NewStringAttribute("user2"),
			"sk": models.NewStringAttribute("profile"),
		}

		oldItem, err := im.DeleteItem("TestTable", key, true)
		if err != nil {
			t.Fatalf("DeleteItem failed: %v", err)
		}
		if oldItem == nil {
			t.Fatal("Expected old item")
		}

		if name, ok := oldItem["name"].GetString(); !ok || name != "Jane Doe" {
			t.Errorf("Expected name 'Jane Doe', got %v", name)
		}
	})
}

func TestItemManager_UpdateItem(t *testing.T) {
	im, tm, cleanup := setupTestItemManager(t)
	defer cleanup()

	// Create test table
	if err := createTestTable(tm, "TestTable", "pk", "sk"); err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Insert test item
	testItem := models.Item{
		"pk": models.NewStringAttribute("user1"),
		"sk": models.NewStringAttribute("profile"),
		"name": models.NewStringAttribute("John Doe"),
		"age": models.NewNumberAttribute("30"),
	}
	im.PutItem("TestTable", testItem, false)

	t.Run("UpdateItem SET Expression", func(t *testing.T) {
		key := models.Item{
			"pk": models.NewStringAttribute("user1"),
			"sk": models.NewStringAttribute("profile"),
		}

		updateExpr := "SET name = :newName, age = :newAge"
		exprValues := map[string]models.AttributeValue{
			"newName": models.NewStringAttribute("John Updated"),
			"newAge":  models.NewNumberAttribute("31"),
		}

		newItem, oldItem, err := im.UpdateItem("TestTable", key, updateExpr, exprValues, true)
		if err != nil {
			t.Fatalf("UpdateItem failed: %v", err)
		}

		if oldItem == nil {
			t.Error("Expected old item")
		}
		if newItem == nil {
			t.Fatal("Expected new item")
		}

		// Check new values
		if name, ok := newItem["name"].GetString(); !ok || name != "John Updated" {
			t.Errorf("Expected updated name 'John Updated', got %v", name)
		}
		if age, ok := newItem["age"].GetNumber(); !ok || age != "31" {
			t.Errorf("Expected updated age '31', got %v", age)
		}

		// Verify pk and sk are preserved
		if pk, ok := newItem["pk"].GetString(); !ok || pk != "user1" {
			t.Errorf("Expected pk 'user1', got %v", pk)
		}
	})

	t.Run("UpdateItem Create New", func(t *testing.T) {
		key := models.Item{
			"pk": models.NewStringAttribute("user3"),
			"sk": models.NewStringAttribute("profile"),
		}

		updateExpr := "SET name = :name"
		exprValues := map[string]models.AttributeValue{
			"name": models.NewStringAttribute("New User"),
		}

		newItem, _, err := im.UpdateItem("TestTable", key, updateExpr, exprValues, false)
		if err != nil {
			t.Fatalf("UpdateItem failed: %v", err)
		}

		if newItem == nil {
			t.Fatal("Expected new item")
		}

		if name, ok := newItem["name"].GetString(); !ok || name != "New User" {
			t.Errorf("Expected name 'New User', got %v", name)
		}

		// Verify key attributes are set
		if pk, ok := newItem["pk"].GetString(); !ok || pk != "user3" {
			t.Errorf("Expected pk 'user3', got %v", pk)
		}
	})
}

func TestItemManager_Query(t *testing.T) {
	im, tm, cleanup := setupTestItemManager(t)
	defer cleanup()

	// Create test table with composite key
	if err := createTestTable(tm, "TestTable", "pk", "sk"); err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Insert multiple items with same partition key
	items := []models.Item{
		{
			"pk": models.NewStringAttribute("user1"),
			"sk": models.NewStringAttribute("a"),
			"data": models.NewStringAttribute("item_a"),
		},
		{
			"pk": models.NewStringAttribute("user1"),
			"sk": models.NewStringAttribute("b"),
			"data": models.NewStringAttribute("item_b"),
		},
		{
			"pk": models.NewStringAttribute("user1"),
			"sk": models.NewStringAttribute("c"),
			"data": models.NewStringAttribute("item_c"),
		},
		{
			"pk": models.NewStringAttribute("user2"),
			"sk": models.NewStringAttribute("x"),
			"data": models.NewStringAttribute("user2_item"),
		},
	}

	for _, item := range items {
		if _, err := im.PutItem("TestTable", item, false); err != nil {
			t.Fatalf("Failed to put item: %v", err)
		}
	}

	t.Run("Query All Items for Partition", func(t *testing.T) {
		keyConditions := map[string]models.Condition{
			"pk": {
				ComparisonOperator: "EQ",
				AttributeValueList: []models.AttributeValue{models.NewStringAttribute("user1")},
			},
		}

		results, lastKey, err := im.Query("TestTable", "", "user1", keyConditions, true, 0, nil)
		if err != nil {
			t.Fatalf("Query failed: %v", err)
		}

		if len(results) != 3 {
			t.Errorf("Expected 3 items, got %d", len(results))
		}

		if lastKey != nil {
			t.Error("Expected no last key")
		}
	})

	t.Run("Query With Limit", func(t *testing.T) {
		keyConditions := map[string]models.Condition{
			"pk": {
				ComparisonOperator: "EQ",
				AttributeValueList: []models.AttributeValue{models.NewStringAttribute("user1")},
			},
		}

		results, lastKey, err := im.Query("TestTable", "", "user1", keyConditions, true, 2, nil)
		if err != nil {
			t.Fatalf("Query failed: %v", err)
		}

		if len(results) != 2 {
			t.Errorf("Expected 2 items, got %d", len(results))
		}

		if lastKey == nil {
			t.Error("Expected last key for pagination")
		}
	})

	t.Run("Query Different User", func(t *testing.T) {
		keyConditions := map[string]models.Condition{
			"pk": {
				ComparisonOperator: "EQ",
				AttributeValueList: []models.AttributeValue{models.NewStringAttribute("user2")},
			},
		}

		results, _, err := im.Query("TestTable", "", "user2", keyConditions, true, 0, nil)
		if err != nil {
			t.Fatalf("Query failed: %v", err)
		}

		if len(results) != 1 {
			t.Errorf("Expected 1 item, got %d", len(results))
		}

		if data, ok := results[0]["data"].GetString(); !ok || data != "user2_item" {
			t.Errorf("Expected data 'user2_item', got %v", data)
		}
	})
}

func TestItemManager_Scan(t *testing.T) {
	im, tm, cleanup := setupTestItemManager(t)
	defer cleanup()

	// Create test table
	if err := createTestTable(tm, "TestTable", "pk", "sk"); err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Insert multiple items
	items := []models.Item{
		{
			"pk": models.NewStringAttribute("user1"),
			"sk": models.NewStringAttribute("a"),
			"data": models.NewStringAttribute("item1"),
		},
		{
			"pk": models.NewStringAttribute("user2"),
			"sk": models.NewStringAttribute("b"),
			"data": models.NewStringAttribute("item2"),
		},
		{
			"pk": models.NewStringAttribute("user3"),
			"sk": models.NewStringAttribute("c"),
			"data": models.NewStringAttribute("item3"),
		},
	}

	for _, item := range items {
		if _, err := im.PutItem("TestTable", item, false); err != nil {
			t.Fatalf("Failed to put item: %v", err)
		}
	}

	t.Run("Scan All Items", func(t *testing.T) {
		results, lastKey, err := im.Scan("TestTable", "", 0, nil, 0, 0)
		if err != nil {
			t.Fatalf("Scan failed: %v", err)
		}

		if len(results) != 3 {
			t.Errorf("Expected 3 items, got %d", len(results))
		}

		if lastKey != nil {
			t.Error("Expected no last key")
		}
	})

	t.Run("Scan With Limit", func(t *testing.T) {
		results, lastKey, err := im.Scan("TestTable", "", 2, nil, 0, 0)
		if err != nil {
			t.Fatalf("Scan failed: %v", err)
		}

		if len(results) != 2 {
			t.Errorf("Expected 2 items, got %d", len(results))
		}

		if lastKey == nil {
			t.Error("Expected last key for pagination")
		}
	})
}

func TestItemManager_ComplexAttributes(t *testing.T) {
	im, tm, cleanup := setupTestItemManager(t)
	defer cleanup()

	// Create test table
	if err := createTestTable(tm, "TestTable", "pk", "sk"); err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	t.Run("PutItem with List Attribute", func(t *testing.T) {
		item := models.Item{
			"pk": models.NewStringAttribute("list_test"),
			"sk": models.NewStringAttribute("item"),
			"tags": models.NewListAttribute([]models.AttributeValue{
				models.NewStringAttribute("tag1"),
				models.NewStringAttribute("tag2"),
				models.NewStringAttribute("tag3"),
			}),
		}

		_, err := im.PutItem("TestTable", item, false)
		if err != nil {
			t.Fatalf("PutItem failed: %v", err)
		}

		// Retrieve and verify
		key := models.Item{
			"pk": models.NewStringAttribute("list_test"),
			"sk": models.NewStringAttribute("item"),
		}

		retrieved, err := im.GetItem("TestTable", key, true)
		if err != nil {
			t.Fatalf("GetItem failed: %v", err)
		}

		list, ok := retrieved["tags"].GetList()
		if !ok {
			t.Fatal("Expected list attribute")
		}
		if len(list) != 3 {
			t.Errorf("Expected 3 items in list, got %d", len(list))
		}
	})

	t.Run("PutItem with Map Attribute", func(t *testing.T) {
		item := models.Item{
			"pk": models.NewStringAttribute("map_test"),
			"sk": models.NewStringAttribute("item"),
			"address": models.NewMapAttribute(map[string]models.AttributeValue{
				"street": models.NewStringAttribute("123 Main St"),
				"city":   models.NewStringAttribute("Seattle"),
				"zip":    models.NewStringAttribute("98101"),
			}),
		}

		_, err := im.PutItem("TestTable", item, false)
		if err != nil {
			t.Fatalf("PutItem failed: %v", err)
		}

		// Retrieve and verify
		key := models.Item{
			"pk": models.NewStringAttribute("map_test"),
			"sk": models.NewStringAttribute("item"),
		}

		retrieved, err := im.GetItem("TestTable", key, true)
		if err != nil {
			t.Fatalf("GetItem failed: %v", err)
		}

		m, ok := retrieved["address"].GetMap()
		if !ok {
			t.Fatal("Expected map attribute")
		}
		if len(m) != 3 {
			t.Errorf("Expected 3 items in map, got %d", len(m))
		}
	})

	t.Run("PutItem with Boolean and Null", func(t *testing.T) {
		item := models.Item{
			"pk":      models.NewStringAttribute("bool_test"),
			"sk":      models.NewStringAttribute("item"),
			"active":  models.NewBoolAttribute(true),
			"deleted": models.NewNullAttribute(),
		}

		_, err := im.PutItem("TestTable", item, false)
		if err != nil {
			t.Fatalf("PutItem failed: %v", err)
		}

		// Retrieve and verify
		key := models.Item{
			"pk": models.NewStringAttribute("bool_test"),
			"sk": models.NewStringAttribute("item"),
		}

		retrieved, err := im.GetItem("TestTable", key, true)
		if err != nil {
			t.Fatalf("GetItem failed: %v", err)
		}

		if active, ok := retrieved["active"].GetBool(); !ok || !active {
			t.Errorf("Expected active=true, got %v", active)
		}

		if !retrieved["deleted"].GetNull() {
			t.Error("Expected deleted to be null")
		}
	})
}

func TestItemManager_InvalidKey(t *testing.T) {
	im, tm, cleanup := setupTestItemManager(t)
	defer cleanup()

	// Create test table
	if err := createTestTable(tm, "TestTable", "pk", "sk"); err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	t.Run("PutItem Missing Partition Key", func(t *testing.T) {
		item := models.Item{
			"sk": models.NewStringAttribute("profile"),
			"data": models.NewStringAttribute("some data"),
		}

		_, err := im.PutItem("TestTable", item, false)
		if err == nil {
			t.Error("Expected error for missing partition key")
		}
	})

	t.Run("PutItem Missing Sort Key", func(t *testing.T) {
		item := models.Item{
			"pk": models.NewStringAttribute("user1"),
			"data": models.NewStringAttribute("some data"),
		}

		_, err := im.PutItem("TestTable", item, false)
		if err == nil {
			t.Error("Expected error for missing sort key in composite key table")
		}
	})
}

func TestItemManager_ConcurrentAccess(t *testing.T) {
	im, tm, cleanup := setupTestItemManager(t)
	defer cleanup()

	// Create test table
	if err := createTestTable(tm, "TestTable", "pk", ""); err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Run concurrent PutItem operations
	done := make(chan bool, 10)
	for i := 0; i < 10; i++ {
		go func(index int) {
			item := models.Item{
				"pk":   models.NewStringAttribute(fmt.Sprintf("concurrent_%d", index)),
				"data": models.NewStringAttribute(fmt.Sprintf("data_%d", index)),
			}
			_, err := im.PutItem("TestTable", item, false)
			if err != nil {
				t.Errorf("Concurrent PutItem failed: %v", err)
			}
			done <- true
		}(i)
	}

	// Wait for all goroutines
	for i := 0; i < 10; i++ {
		<-done
	}

	// Verify all items were inserted
	results, _, err := im.Scan("TestTable", "", 0, nil, 0, 0)
	if err != nil {
		t.Fatalf("Scan failed: %v", err)
	}

	if len(results) != 10 {
		t.Errorf("Expected 10 items, got %d", len(results))
	}
}
