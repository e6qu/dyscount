// Package storage provides tests for tagging operations.
package storage

import (
	"os"
	"testing"

	"github.com/e6qu/dyscount/internal/models"
)

func TestTableManager_TagResource(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-tagging-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

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

	t.Run("Tag Single Tag", func(t *testing.T) {
		tags := []models.Tag{
			{Key: "Environment", Value: "Test"},
		}

		err := tm.TagResource("TestTable", tags)
		if err != nil {
			t.Fatalf("Failed to tag resource: %v", err)
		}

		// Verify tag was added
		listTags, err := tm.ListTagsOfResource("TestTable")
		if err != nil {
			t.Fatalf("Failed to list tags: %v", err)
		}

		if len(listTags) != 1 {
			t.Errorf("Expected 1 tag, got %d", len(listTags))
		}

		if listTags[0].Key != "Environment" || listTags[0].Value != "Test" {
			t.Errorf("Expected tag Environment=Test, got %s=%s", listTags[0].Key, listTags[0].Value)
		}
	})

	t.Run("Tag Multiple Tags", func(t *testing.T) {
		tags := []models.Tag{
			{Key: "Owner", Value: "TeamA"},
			{Key: "Project", Value: "Dyscount"},
		}

		err := tm.TagResource("TestTable", tags)
		if err != nil {
			t.Fatalf("Failed to tag resource: %v", err)
		}

		// Verify tags were added
		listTags, err := tm.ListTagsOfResource("TestTable")
		if err != nil {
			t.Fatalf("Failed to list tags: %v", err)
		}

		// Should have 3 tags now (1 from previous test + 2 new)
		if len(listTags) != 3 {
			t.Errorf("Expected 3 tags, got %d", len(listTags))
		}

		// Check that new tags exist
		tagMap := make(map[string]string)
		for _, tag := range listTags {
			tagMap[tag.Key] = tag.Value
		}

		if tagMap["Owner"] != "TeamA" {
			t.Errorf("Expected Owner=TeamA, got %s", tagMap["Owner"])
		}
		if tagMap["Project"] != "Dyscount" {
			t.Errorf("Expected Project=Dyscount, got %s", tagMap["Project"])
		}
	})

	t.Run("Update Existing Tag", func(t *testing.T) {
		// Update the Environment tag
		tags := []models.Tag{
			{Key: "Environment", Value: "Production"},
		}

		err := tm.TagResource("TestTable", tags)
		if err != nil {
			t.Fatalf("Failed to update tag: %v", err)
		}

		// Verify tag was updated
		listTags, err := tm.ListTagsOfResource("TestTable")
		if err != nil {
			t.Fatalf("Failed to list tags: %v", err)
		}

		// Should still have 3 tags
		if len(listTags) != 3 {
			t.Errorf("Expected 3 tags, got %d", len(listTags))
		}

		// Check that Environment was updated
		tagMap := make(map[string]string)
		for _, tag := range listTags {
			tagMap[tag.Key] = tag.Value
		}

		if tagMap["Environment"] != "Production" {
			t.Errorf("Expected Environment=Production, got %s", tagMap["Environment"])
		}
	})

	t.Run("Tag NonExistent Table", func(t *testing.T) {
		tags := []models.Tag{
			{Key: "Test", Value: "Value"},
		}

		err := tm.TagResource("NonExistentTable", tags)
		if err == nil {
			t.Error("Expected error when tagging non-existent table")
		}
	})
}

func TestTableManager_UntagResource(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-tagging-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

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

	// Add some tags first
	tags := []models.Tag{
		{Key: "Environment", Value: "Test"},
		{Key: "Owner", Value: "TeamA"},
		{Key: "Project", Value: "Dyscount"},
	}
	err = tm.TagResource("TestTable", tags)
	if err != nil {
		t.Fatalf("Failed to add tags: %v", err)
	}

	t.Run("Untag Single Tag", func(t *testing.T) {
		err := tm.UntagResource("TestTable", []string{"Owner"})
		if err != nil {
			t.Fatalf("Failed to untag resource: %v", err)
		}

		// Verify tag was removed
		listTags, err := tm.ListTagsOfResource("TestTable")
		if err != nil {
			t.Fatalf("Failed to list tags: %v", err)
		}

		if len(listTags) != 2 {
			t.Errorf("Expected 2 tags, got %d", len(listTags))
		}

		// Check that Owner was removed
		for _, tag := range listTags {
			if tag.Key == "Owner" {
				t.Error("Owner tag should have been removed")
			}
		}
	})

	t.Run("Untag Multiple Tags", func(t *testing.T) {
		err := tm.UntagResource("TestTable", []string{"Environment", "Project"})
		if err != nil {
			t.Fatalf("Failed to untag resource: %v", err)
		}

		// Verify all tags were removed
		listTags, err := tm.ListTagsOfResource("TestTable")
		if err != nil {
			t.Fatalf("Failed to list tags: %v", err)
		}

		if len(listTags) != 0 {
			t.Errorf("Expected 0 tags, got %d", len(listTags))
		}
	})

	t.Run("Untag NonExistent Tag", func(t *testing.T) {
		// Should not error when removing non-existent tag
		err := tm.UntagResource("TestTable", []string{"NonExistent"})
		if err != nil {
			t.Fatalf("Failed to untag resource: %v", err)
		}
	})

	t.Run("Untag NonExistent Table", func(t *testing.T) {
		err := tm.UntagResource("NonExistentTable", []string{"Test"})
		if err == nil {
			t.Error("Expected error when untagging non-existent table")
		}
	})
}

func TestTableManager_ListTagsOfResource(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-tagging-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

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

	t.Run("List Tags Empty", func(t *testing.T) {
		tags, err := tm.ListTagsOfResource("TestTable")
		if err != nil {
			t.Fatalf("Failed to list tags: %v", err)
		}

		if len(tags) != 0 {
			t.Errorf("Expected 0 tags, got %d", len(tags))
		}
	})

	t.Run("List Tags With Tags", func(t *testing.T) {
		// Add some tags
		tags := []models.Tag{
			{Key: "Environment", Value: "Test"},
			{Key: "Owner", Value: "TeamA"},
		}
		err := tm.TagResource("TestTable", tags)
		if err != nil {
			t.Fatalf("Failed to add tags: %v", err)
		}

		// List tags
		listTags, err := tm.ListTagsOfResource("TestTable")
		if err != nil {
			t.Fatalf("Failed to list tags: %v", err)
		}

		if len(listTags) != 2 {
			t.Errorf("Expected 2 tags, got %d", len(listTags))
		}

		// Check tags
		tagMap := make(map[string]string)
		for _, tag := range listTags {
			tagMap[tag.Key] = tag.Value
		}

		if tagMap["Environment"] != "Test" {
			t.Errorf("Expected Environment=Test, got %s", tagMap["Environment"])
		}
		if tagMap["Owner"] != "TeamA" {
			t.Errorf("Expected Owner=TeamA, got %s", tagMap["Owner"])
		}
	})

	t.Run("List Tags NonExistent Table", func(t *testing.T) {
		_, err := tm.ListTagsOfResource("NonExistentTable")
		if err == nil {
			t.Error("Expected error when listing tags for non-existent table")
		}
	})
}
