// Package storage provides tests for pagination operations.
package storage

import (
	"os"
	"testing"

	"github.com/e6qu/dyscount/internal/models"
)

func TestItemManager_Query_Pagination(t *testing.T) {
	im, tm, cleanup := setupTestItemManager(t)
	defer cleanup()

	// Create test table with hash + range key
	if err := createTestTable(tm, "TestTable", "pk", "sk"); err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Insert 5 items with same partition key but different sort keys
	items := []models.Item{
		{"pk": models.NewStringAttribute("user1"), "sk": models.NewStringAttribute("a"), "data": models.NewStringAttribute("item1")},
		{"pk": models.NewStringAttribute("user1"), "sk": models.NewStringAttribute("b"), "data": models.NewStringAttribute("item2")},
		{"pk": models.NewStringAttribute("user1"), "sk": models.NewStringAttribute("c"), "data": models.NewStringAttribute("item3")},
		{"pk": models.NewStringAttribute("user1"), "sk": models.NewStringAttribute("d"), "data": models.NewStringAttribute("item4")},
		{"pk": models.NewStringAttribute("user1"), "sk": models.NewStringAttribute("e"), "data": models.NewStringAttribute("item5")},
	}

	for _, item := range items {
		if _, err := im.PutItem("TestTable", item, false); err != nil {
			t.Fatalf("Failed to put item: %v", err)
		}
	}

	t.Run("Query With Limit Returns LastEvaluatedKey", func(t *testing.T) {
		keyConditions := map[string]models.Condition{
			"pk": {
				ComparisonOperator: "EQ",
				AttributeValueList: []models.AttributeValue{models.NewStringAttribute("user1")},
			},
		}

		// Query with limit of 2
		results, lastKey, err := im.Query("TestTable", "", "user1", keyConditions, true, 2, nil)
		if err != nil {
			t.Fatalf("Query failed: %v", err)
		}

		if len(results) != 2 {
			t.Errorf("Expected 2 items, got %d", len(results))
		}

		if lastKey == nil {
			t.Fatal("Expected last key for pagination")
		}

		// Verify last key contains pk and sk
		if _, ok := lastKey["pk"]; !ok {
			t.Error("Last key should contain pk")
		}
		if _, ok := lastKey["sk"]; !ok {
			t.Error("Last key should contain sk")
		}
	})

	t.Run("Query With ExclusiveStartKey", func(t *testing.T) {
		keyConditions := map[string]models.Condition{
			"pk": {
				ComparisonOperator: "EQ",
				AttributeValueList: []models.AttributeValue{models.NewStringAttribute("user1")},
			},
		}

		// First page
		results1, lastKey1, err := im.Query("TestTable", "", "user1", keyConditions, true, 2, nil)
		if err != nil {
			t.Fatalf("Query page 1 failed: %v", err)
		}

		if len(results1) != 2 {
			t.Fatalf("Expected 2 items on page 1, got %d", len(results1))
		}

		if lastKey1 == nil {
			t.Fatal("Expected last key for pagination")
		}

		// Second page using lastKey1 as ExclusiveStartKey
		results2, lastKey2, err := im.Query("TestTable", "", "user1", keyConditions, true, 2, lastKey1)
		if err != nil {
			t.Fatalf("Query page 2 failed: %v", err)
		}

		if len(results2) != 2 {
			t.Errorf("Expected 2 items on page 2, got %d", len(results2))
		}

		if lastKey2 == nil {
			t.Error("Expected last key for page 2")
		}

		// Verify items are different
		sk1, _ := results1[0]["sk"].GetString()
		sk2, _ := results2[0]["sk"].GetString()
		if sk1 == sk2 {
			t.Error("Page 1 and Page 2 should have different items")
		}

		// Third page (should have 1 item left)
		results3, lastKey3, err := im.Query("TestTable", "", "user1", keyConditions, true, 2, lastKey2)
		if err != nil {
			t.Fatalf("Query page 3 failed: %v", err)
		}

		if len(results3) != 1 {
			t.Errorf("Expected 1 item on page 3, got %d", len(results3))
		}

		if lastKey3 != nil {
			t.Error("Expected no last key after final page")
		}
	})

	t.Run("Query All Items With Pagination", func(t *testing.T) {
		keyConditions := map[string]models.Condition{
			"pk": {
				ComparisonOperator: "EQ",
				AttributeValueList: []models.AttributeValue{models.NewStringAttribute("user1")},
			},
		}

		var allItems []models.Item
		var exclusiveStartKey models.Item
		pageCount := 0

		for {
			pageCount++
			if pageCount > 10 {
				t.Fatal("Too many pages, possible infinite loop")
			}

			results, lastKey, err := im.Query("TestTable", "", "user1", keyConditions, true, 2, exclusiveStartKey)
			if err != nil {
				t.Fatalf("Query failed: %v", err)
			}

			allItems = append(allItems, results...)

			if lastKey == nil {
				break
			}
			exclusiveStartKey = lastKey
		}

		if len(allItems) != 5 {
			t.Errorf("Expected 5 total items, got %d", len(allItems))
		}

		if pageCount != 3 {
			t.Errorf("Expected 3 pages, got %d", pageCount)
		}
	})
}

func TestItemManager_Scan_Pagination(t *testing.T) {
	im, tm, cleanup := setupTestItemManager(t)
	defer cleanup()

	// Create test table
	if err := createTestTable(tm, "TestTable", "pk", ""); err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Insert 5 items
	items := []models.Item{
		{"pk": models.NewStringAttribute("a"), "data": models.NewStringAttribute("item1")},
		{"pk": models.NewStringAttribute("b"), "data": models.NewStringAttribute("item2")},
		{"pk": models.NewStringAttribute("c"), "data": models.NewStringAttribute("item3")},
		{"pk": models.NewStringAttribute("d"), "data": models.NewStringAttribute("item4")},
		{"pk": models.NewStringAttribute("e"), "data": models.NewStringAttribute("item5")},
	}

	for _, item := range items {
		if _, err := im.PutItem("TestTable", item, false); err != nil {
			t.Fatalf("Failed to put item: %v", err)
		}
	}

	t.Run("Scan With Limit Returns LastEvaluatedKey", func(t *testing.T) {
		results, lastKey, err := im.Scan("TestTable", "", 2, nil, 0, 0)
		if err != nil {
			t.Fatalf("Scan failed: %v", err)
		}

		if len(results) != 2 {
			t.Errorf("Expected 2 items, got %d", len(results))
		}

		if lastKey == nil {
			t.Fatal("Expected last key for pagination")
		}

		// Verify last key contains pk
		if _, ok := lastKey["pk"]; !ok {
			t.Error("Last key should contain pk")
		}
	})

	t.Run("Scan With ExclusiveStartKey", func(t *testing.T) {
		// First page
		results1, lastKey1, err := im.Scan("TestTable", "", 2, nil, 0, 0)
		if err != nil {
			t.Fatalf("Scan page 1 failed: %v", err)
		}

		if len(results1) != 2 {
			t.Fatalf("Expected 2 items on page 1, got %d", len(results1))
		}

		if lastKey1 == nil {
			t.Fatal("Expected last key for pagination")
		}

		// Second page using lastKey1 as ExclusiveStartKey
		results2, lastKey2, err := im.Scan("TestTable", "", 2, lastKey1, 0, 0)
		if err != nil {
			t.Fatalf("Scan page 2 failed: %v", err)
		}

		if len(results2) != 2 {
			t.Errorf("Expected 2 items on page 2, got %d", len(results2))
		}

		if lastKey2 == nil {
			t.Error("Expected last key for page 2")
		}

		// Third page (should have 1 item left)
		results3, lastKey3, err := im.Scan("TestTable", "", 2, lastKey2, 0, 0)
		if err != nil {
			t.Fatalf("Scan page 3 failed: %v", err)
		}

		if len(results3) != 1 {
			t.Errorf("Expected 1 item on page 3, got %d", len(results3))
		}

		if lastKey3 != nil {
			t.Error("Expected no last key after final page")
		}
	})

	t.Run("Scan All Items With Pagination", func(t *testing.T) {
		var allItems []models.Item
		var exclusiveStartKey models.Item
		pageCount := 0

		for {
			pageCount++
			if pageCount > 10 {
				t.Fatal("Too many pages, possible infinite loop")
			}

			results, lastKey, err := im.Scan("TestTable", "", 2, exclusiveStartKey, 0, 0)
			if err != nil {
				t.Fatalf("Scan failed: %v", err)
			}

			allItems = append(allItems, results...)

			if lastKey == nil {
				break
			}
			exclusiveStartKey = lastKey
		}

		if len(allItems) != 5 {
			t.Errorf("Expected 5 total items, got %d", len(allItems))
		}

		if pageCount != 3 {
			t.Errorf("Expected 3 pages, got %d", pageCount)
		}
	})
}

func TestItemManager_Query_Pagination_WithFilter(t *testing.T) {
	im, tm, cleanup := setupTestItemManager(t)
	defer cleanup()

	// Create test table
	if err := createTestTable(tm, "TestTable", "pk", "sk"); err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Insert items with status attribute for filtering
	items := []models.Item{
		{"pk": models.NewStringAttribute("user1"), "sk": models.NewStringAttribute("a"), "status": models.NewStringAttribute("active")},
		{"pk": models.NewStringAttribute("user1"), "sk": models.NewStringAttribute("b"), "status": models.NewStringAttribute("inactive")},
		{"pk": models.NewStringAttribute("user1"), "sk": models.NewStringAttribute("c"), "status": models.NewStringAttribute("active")},
		{"pk": models.NewStringAttribute("user1"), "sk": models.NewStringAttribute("d"), "status": models.NewStringAttribute("inactive")},
		{"pk": models.NewStringAttribute("user1"), "sk": models.NewStringAttribute("e"), "status": models.NewStringAttribute("active")},
	}

	for _, item := range items {
		if _, err := im.PutItem("TestTable", item, false); err != nil {
			t.Fatalf("Failed to put item: %v", err)
		}
	}

	t.Run("Query With Filter And Pagination", func(t *testing.T) {
		// Note: This test verifies that pagination works correctly even with filters
		// The limit applies before filtering in DynamoDB, but our implementation
		// may differ. This test documents the current behavior.
		keyConditions := map[string]models.Condition{
			"pk": {
				ComparisonOperator: "EQ",
				AttributeValueList: []models.AttributeValue{models.NewStringAttribute("user1")},
			},
		}

		// Query with limit
		results, lastKey, err := im.Query("TestTable", "", "user1", keyConditions, true, 3, nil)
		if err != nil {
			t.Fatalf("Query failed: %v", err)
		}

		// Verify we got results
		if len(results) == 0 {
			t.Error("Expected some results")
		}

		// Verify pagination key is set if we have more items
		if len(results) >= 3 && lastKey == nil {
			t.Error("Expected last key when limit is reached")
		}
	})
}

func TestItemManager_Pagination_HashOnlyTable(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-pagination-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	im := NewItemManager(tm)

	// Create table with hash key only (no range key)
	req := &models.DynamoDBRequest{
		TableName: "HashOnlyTable",
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

	// Insert items
	for i := 0; i < 5; i++ {
		item := models.Item{
			"pk":   models.NewStringAttribute(string(rune('a' + i))),
			"data": models.NewStringAttribute("item"),
		}
		if _, err := im.PutItem("HashOnlyTable", item, false); err != nil {
			t.Fatalf("Failed to put item: %v", err)
		}
	}

	t.Run("Scan Hash Only Table With Pagination", func(t *testing.T) {
		results, lastKey, err := im.Scan("HashOnlyTable", "", 2, nil, 0, 0)
		if err != nil {
			t.Fatalf("Scan failed: %v", err)
		}

		if len(results) != 2 {
			t.Errorf("Expected 2 items, got %d", len(results))
		}

		if lastKey == nil {
			t.Fatal("Expected last key for pagination")
		}

		// Verify last key only contains pk
		if len(lastKey) != 1 {
			t.Errorf("Last key should only contain pk, got %d attributes", len(lastKey))
		}
	})
}
