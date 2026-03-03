// Package storage provides tests for UpdateTable GSI operations.
package storage

import (
	"os"
	"testing"

	"github.com/e6qu/dyscount/internal/models"
)

func TestTableManager_UpdateTable_CreateGSI(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-gsi-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	// Create test table with GSI
	req := &models.DynamoDBRequest{
		TableName: "TestTable",
		KeySchema: []models.KeySchemaElement{
			{AttributeName: "pk", KeyType: "HASH"},
			{AttributeName: "sk", KeyType: "RANGE"},
		},
		AttributeDefinitions: []models.AttributeDefinition{
			{AttributeName: "pk", AttributeType: "S"},
			{AttributeName: "sk", AttributeType: "S"},
			{AttributeName: "gsi_pk", AttributeType: "S"},
			{AttributeName: "gsi_sk", AttributeType: "S"},
		},
		GlobalSecondaryIndexes: []models.GlobalSecondaryIndex{
			{
				IndexName: "InitialGSI",
				KeySchema: []models.KeySchemaElement{
					{AttributeName: "gsi_pk", KeyType: "HASH"},
				},
				Projection: models.Projection{
					ProjectionType: "ALL",
				},
			},
		},
	}

	_, err = tm.CreateTable(req)
	if err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Test creating a new GSI via UpdateTable
	updateReq := &models.UpdateTableRequest{
		TableName: "TestTable",
		AttributeDefinitions: []models.AttributeDefinition{
			{AttributeName: "email", AttributeType: "S"},
			{AttributeName: "timestamp", AttributeType: "S"},
		},
		GlobalSecondaryIndexUpdates: []models.GlobalSecondaryIndexUpdate{
			{
				Create: &models.CreateGlobalSecondaryIndexAction{
					IndexName: "EmailIndex",
					KeySchema: []models.KeySchemaElement{
						{AttributeName: "email", KeyType: "HASH"},
						{AttributeName: "timestamp", KeyType: "RANGE"},
					},
					Projection: models.Projection{
						ProjectionType: "ALL",
					},
				},
			},
		},
	}

	metadata, err := tm.UpdateTable(updateReq)
	if err != nil {
		t.Fatalf("Failed to update table: %v", err)
	}

	// Verify GSI was created
	if len(metadata.GlobalSecondaryIndexes) != 2 {
		t.Errorf("Expected 2 GSIs, got %d", len(metadata.GlobalSecondaryIndexes))
	}

	// Find the new GSI
	found := false
	for _, gsi := range metadata.GlobalSecondaryIndexes {
		if gsi.IndexName == "EmailIndex" {
			found = true
			if len(gsi.KeySchema) != 2 {
				t.Errorf("Expected 2 key elements in EmailIndex, got %d", len(gsi.KeySchema))
			}
		}
	}
	if !found {
		t.Error("EmailIndex GSI not found after creation")
	}
}

func TestTableManager_UpdateTable_DeleteGSI(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-gsi-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	// Create test table with GSI
	req := &models.DynamoDBRequest{
		TableName: "TestTable",
		KeySchema: []models.KeySchemaElement{
			{AttributeName: "pk", KeyType: "HASH"},
		},
		AttributeDefinitions: []models.AttributeDefinition{
			{AttributeName: "pk", AttributeType: "S"},
			{AttributeName: "gsi_pk", AttributeType: "S"},
		},
		GlobalSecondaryIndexes: []models.GlobalSecondaryIndex{
			{
				IndexName: "ToDeleteGSI",
				KeySchema: []models.KeySchemaElement{
					{AttributeName: "gsi_pk", KeyType: "HASH"},
				},
				Projection: models.Projection{
					ProjectionType: "ALL",
				},
			},
		},
	}

	_, err = tm.CreateTable(req)
	if err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Verify GSI exists initially
	metadata, _ := tm.DescribeTable("TestTable")
	if len(metadata.GlobalSecondaryIndexes) != 1 {
		t.Fatalf("Expected 1 GSI initially, got %d", len(metadata.GlobalSecondaryIndexes))
	}

	// Delete the GSI
	updateReq := &models.UpdateTableRequest{
		TableName: "TestTable",
		GlobalSecondaryIndexUpdates: []models.GlobalSecondaryIndexUpdate{
			{
				Delete: &models.DeleteGlobalSecondaryIndexAction{
					IndexName: "ToDeleteGSI",
				},
			},
		},
	}

	metadata, err = tm.UpdateTable(updateReq)
	if err != nil {
		t.Fatalf("Failed to update table: %v", err)
	}

	// Verify GSI was deleted
	if len(metadata.GlobalSecondaryIndexes) != 0 {
		t.Errorf("Expected 0 GSIs after deletion, got %d", len(metadata.GlobalSecondaryIndexes))
	}
}

func TestTableManager_UpdateTable_UpdateGSIThroughput(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-gsi-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	// Create test table with GSI
	req := &models.DynamoDBRequest{
		TableName: "TestTable",
		KeySchema: []models.KeySchemaElement{
			{AttributeName: "pk", KeyType: "HASH"},
		},
		AttributeDefinitions: []models.AttributeDefinition{
			{AttributeName: "pk", AttributeType: "S"},
			{AttributeName: "gsi_pk", AttributeType: "S"},
		},
		GlobalSecondaryIndexes: []models.GlobalSecondaryIndex{
			{
				IndexName: "GSI1",
				KeySchema: []models.KeySchemaElement{
					{AttributeName: "gsi_pk", KeyType: "HASH"},
				},
				Projection: models.Projection{
					ProjectionType: "ALL",
				},
				ProvisionedThroughput: &models.ProvisionedThroughput{
					ReadCapacityUnits:  5,
					WriteCapacityUnits: 5,
				},
			},
		},
	}

	_, err = tm.CreateTable(req)
	if err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Update GSI throughput
	updateReq := &models.UpdateTableRequest{
		TableName: "TestTable",
		GlobalSecondaryIndexUpdates: []models.GlobalSecondaryIndexUpdate{
			{
				Update: &models.UpdateGlobalSecondaryIndexAction{
					IndexName: "GSI1",
					ProvisionedThroughput: &models.ProvisionedThroughput{
						ReadCapacityUnits:  10,
						WriteCapacityUnits: 10,
					},
				},
			},
		},
	}

	metadata, err := tm.UpdateTable(updateReq)
	if err != nil {
		t.Fatalf("Failed to update table: %v", err)
	}

	// Verify GSI throughput was updated
	if len(metadata.GlobalSecondaryIndexes) != 1 {
		t.Fatalf("Expected 1 GSI, got %d", len(metadata.GlobalSecondaryIndexes))
	}

	gsi := metadata.GlobalSecondaryIndexes[0]
	if gsi.ProvisionedThroughput == nil {
		t.Fatal("GSI ProvisionedThroughput is nil")
	}

	if gsi.ProvisionedThroughput.ReadCapacityUnits != 10 {
		t.Errorf("Expected ReadCapacityUnits=10, got %d", gsi.ProvisionedThroughput.ReadCapacityUnits)
	}

	if gsi.ProvisionedThroughput.WriteCapacityUnits != 10 {
		t.Errorf("Expected WriteCapacityUnits=10, got %d", gsi.ProvisionedThroughput.WriteCapacityUnits)
	}
}

func TestTableManager_UpdateTable_MixedGSIOperations(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-gsi-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	// Create test table with GSIs
	req := &models.DynamoDBRequest{
		TableName: "TestTable",
		KeySchema: []models.KeySchemaElement{
			{AttributeName: "pk", KeyType: "HASH"},
		},
		AttributeDefinitions: []models.AttributeDefinition{
			{AttributeName: "pk", AttributeType: "S"},
			{AttributeName: "gsi1_pk", AttributeType: "S"},
			{AttributeName: "gsi2_pk", AttributeType: "S"},
			{AttributeName: "new_gsi_pk", AttributeType: "S"},
		},
		GlobalSecondaryIndexes: []models.GlobalSecondaryIndex{
			{
				IndexName: "GSI1",
				KeySchema: []models.KeySchemaElement{
					{AttributeName: "gsi1_pk", KeyType: "HASH"},
				},
				Projection: models.Projection{
					ProjectionType: "ALL",
				},
			},
			{
				IndexName: "GSI2",
				KeySchema: []models.KeySchemaElement{
					{AttributeName: "gsi2_pk", KeyType: "HASH"},
				},
				Projection: models.Projection{
					ProjectionType: "ALL",
				},
			},
		},
	}

	_, err = tm.CreateTable(req)
	if err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Perform mixed operations: delete GSI2, create new GSI, update GSI1
	updateReq := &models.UpdateTableRequest{
		TableName: "TestTable",
		GlobalSecondaryIndexUpdates: []models.GlobalSecondaryIndexUpdate{
			{
				Delete: &models.DeleteGlobalSecondaryIndexAction{
					IndexName: "GSI2",
				},
			},
			{
				Create: &models.CreateGlobalSecondaryIndexAction{
					IndexName: "NewGSI",
					KeySchema: []models.KeySchemaElement{
						{AttributeName: "new_gsi_pk", KeyType: "HASH"},
					},
					Projection: models.Projection{
						ProjectionType: "ALL",
					},
				},
			},
			{
				Update: &models.UpdateGlobalSecondaryIndexAction{
					IndexName: "GSI1",
					ProvisionedThroughput: &models.ProvisionedThroughput{
						ReadCapacityUnits:  20,
						WriteCapacityUnits: 20,
					},
				},
			},
		},
	}

	metadata, err := tm.UpdateTable(updateReq)
	if err != nil {
		t.Fatalf("Failed to update table: %v", err)
	}

	// Verify final state
	if len(metadata.GlobalSecondaryIndexes) != 2 {
		t.Errorf("Expected 2 GSIs, got %d", len(metadata.GlobalSecondaryIndexes))
	}

	// Verify GSI1 was updated
	gsi1Found := false
	for _, gsi := range metadata.GlobalSecondaryIndexes {
		if gsi.IndexName == "GSI1" {
			gsi1Found = true
			if gsi.ProvisionedThroughput == nil || gsi.ProvisionedThroughput.ReadCapacityUnits != 20 {
				t.Error("GSI1 throughput was not updated")
			}
		}
		if gsi.IndexName == "GSI2" {
			t.Error("GSI2 should have been deleted")
		}
		if gsi.IndexName == "NewGSI" {
			// New GSI exists
		}
	}
	if !gsi1Found {
		t.Error("GSI1 not found")
	}
}

func TestTableManager_UpdateTable_CreateDuplicateGSI(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-gsi-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	// Create test table with GSI
	req := &models.DynamoDBRequest{
		TableName: "TestTable",
		KeySchema: []models.KeySchemaElement{
			{AttributeName: "pk", KeyType: "HASH"},
		},
		AttributeDefinitions: []models.AttributeDefinition{
			{AttributeName: "pk", AttributeType: "S"},
			{AttributeName: "gsi_pk", AttributeType: "S"},
		},
		GlobalSecondaryIndexes: []models.GlobalSecondaryIndex{
			{
				IndexName: "ExistingGSI",
				KeySchema: []models.KeySchemaElement{
					{AttributeName: "gsi_pk", KeyType: "HASH"},
				},
				Projection: models.Projection{
					ProjectionType: "ALL",
				},
			},
		},
	}

	_, err = tm.CreateTable(req)
	if err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Try to create duplicate GSI
	updateReq := &models.UpdateTableRequest{
		TableName: "TestTable",
		GlobalSecondaryIndexUpdates: []models.GlobalSecondaryIndexUpdate{
			{
				Create: &models.CreateGlobalSecondaryIndexAction{
					IndexName: "ExistingGSI",
					KeySchema: []models.KeySchemaElement{
						{AttributeName: "gsi_pk", KeyType: "HASH"},
					},
					Projection: models.Projection{
						ProjectionType: "ALL",
					},
				},
			},
		},
	}

	_, err = tm.UpdateTable(updateReq)
	if err == nil {
		t.Error("Expected error when creating duplicate GSI")
	}
}

func TestTableManager_UpdateTable_UpdateTableThroughput(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-gsi-test-*")
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
		ProvisionedThroughput: &models.ProvisionedThroughput{
			ReadCapacityUnits:  5,
			WriteCapacityUnits: 5,
		},
	}

	_, err = tm.CreateTable(req)
	if err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Update table throughput
	updateReq := &models.UpdateTableRequest{
		TableName: "TestTable",
		ProvisionedThroughput: &models.ProvisionedThroughput{
			ReadCapacityUnits:  25,
			WriteCapacityUnits: 25,
		},
	}

	metadata, err := tm.UpdateTable(updateReq)
	if err != nil {
		t.Fatalf("Failed to update table: %v", err)
	}

	// Verify throughput was updated
	if metadata.ProvisionedThroughput == nil {
		t.Fatal("ProvisionedThroughput is nil")
	}

	if metadata.ProvisionedThroughput.ReadCapacityUnits != 25 {
		t.Errorf("Expected ReadCapacityUnits=25, got %d", metadata.ProvisionedThroughput.ReadCapacityUnits)
	}

	if metadata.ProvisionedThroughput.WriteCapacityUnits != 25 {
		t.Errorf("Expected WriteCapacityUnits=25, got %d", metadata.ProvisionedThroughput.WriteCapacityUnits)
	}
}

func TestTableManager_UpdateTable_UpdateBillingMode(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-gsi-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	// Create test table with PROVISIONED billing mode
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

	// Update billing mode to PAY_PER_REQUEST
	updateReq := &models.UpdateTableRequest{
		TableName:   "TestTable",
		BillingMode: "PAY_PER_REQUEST",
	}

	metadata, err := tm.UpdateTable(updateReq)
	if err != nil {
		t.Fatalf("Failed to update table: %v", err)
	}

	// Verify billing mode was updated
	if metadata.BillingModeSummary == nil {
		t.Fatal("BillingModeSummary is nil")
	}

	if metadata.BillingModeSummary.BillingMode != "PAY_PER_REQUEST" {
		t.Errorf("Expected BillingMode=PAY_PER_REQUEST, got %s", metadata.BillingModeSummary.BillingMode)
	}
}

func TestTableManager_UpdateTable_NonExistentTable(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-gsi-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	// Try to update non-existent table
	updateReq := &models.UpdateTableRequest{
		TableName: "NonExistentTable",
		ProvisionedThroughput: &models.ProvisionedThroughput{
			ReadCapacityUnits:  10,
			WriteCapacityUnits: 10,
		},
	}

	_, err = tm.UpdateTable(updateReq)
	if err == nil {
		t.Error("Expected error when updating non-existent table")
	}
}
