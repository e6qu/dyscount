// Package storage provides tests for TTL operations.
package storage

import (
	"os"
	"testing"

	"github.com/e6qu/dyscount/internal/models"
)

func TestTableManager_UpdateTimeToLive_Enable(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-ttl-test-*")
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

	// Enable TTL
	updateReq := &models.UpdateTimeToLiveRequest{
		TableName: "TestTable",
		TimeToLiveSpecification: models.TimeToLiveSpecification{
			AttributeName: "ttl",
			Enabled:       true,
		},
	}

	ttlDesc, err := tm.UpdateTimeToLive(updateReq)
	if err != nil {
		t.Fatalf("Failed to update TTL: %v", err)
	}

	// Verify TTL was enabled
	if ttlDesc.AttributeName != "ttl" {
		t.Errorf("Expected AttributeName=ttl, got %s", ttlDesc.AttributeName)
	}
	if ttlDesc.TimeToLiveStatus != "ENABLED" {
		t.Errorf("Expected TimeToLiveStatus=ENABLED, got %s", ttlDesc.TimeToLiveStatus)
	}
}

func TestTableManager_UpdateTimeToLive_Disable(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-ttl-test-*")
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

	// First enable TTL
	enableReq := &models.UpdateTimeToLiveRequest{
		TableName: "TestTable",
		TimeToLiveSpecification: models.TimeToLiveSpecification{
			AttributeName: "ttl",
			Enabled:       true,
		},
	}
	_, err = tm.UpdateTimeToLive(enableReq)
	if err != nil {
		t.Fatalf("Failed to enable TTL: %v", err)
	}

	// Then disable TTL
	disableReq := &models.UpdateTimeToLiveRequest{
		TableName: "TestTable",
		TimeToLiveSpecification: models.TimeToLiveSpecification{
			AttributeName: "ttl",
			Enabled:       false,
		},
	}

	ttlDesc, err := tm.UpdateTimeToLive(disableReq)
	if err != nil {
		t.Fatalf("Failed to disable TTL: %v", err)
	}

	// Verify TTL was disabled
	if ttlDesc.TimeToLiveStatus != "DISABLED" {
		t.Errorf("Expected TimeToLiveStatus=DISABLED, got %s", ttlDesc.TimeToLiveStatus)
	}
}

func TestTableManager_DescribeTimeToLive_NotConfigured(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-ttl-test-*")
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

	// Describe TTL (not configured)
	ttlDesc, err := tm.DescribeTimeToLive("TestTable")
	if err != nil {
		t.Fatalf("Failed to describe TTL: %v", err)
	}

	// Verify TTL is disabled by default
	if ttlDesc.TimeToLiveStatus != "DISABLED" {
		t.Errorf("Expected TimeToLiveStatus=DISABLED, got %s", ttlDesc.TimeToLiveStatus)
	}
}

func TestTableManager_DescribeTimeToLive_Enabled(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-ttl-test-*")
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

	// Enable TTL
	updateReq := &models.UpdateTimeToLiveRequest{
		TableName: "TestTable",
		TimeToLiveSpecification: models.TimeToLiveSpecification{
			AttributeName: "expiration",
			Enabled:       true,
		},
	}
	_, err = tm.UpdateTimeToLive(updateReq)
	if err != nil {
		t.Fatalf("Failed to enable TTL: %v", err)
	}

	// Describe TTL
	ttlDesc, err := tm.DescribeTimeToLive("TestTable")
	if err != nil {
		t.Fatalf("Failed to describe TTL: %v", err)
	}

	// Verify TTL is enabled
	if ttlDesc.AttributeName != "expiration" {
		t.Errorf("Expected AttributeName=expiration, got %s", ttlDesc.AttributeName)
	}
	if ttlDesc.TimeToLiveStatus != "ENABLED" {
		t.Errorf("Expected TimeToLiveStatus=ENABLED, got %s", ttlDesc.TimeToLiveStatus)
	}
}

func TestTableManager_UpdateTimeToLive_NonExistentTable(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-ttl-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	// Try to update TTL on non-existent table
	updateReq := &models.UpdateTimeToLiveRequest{
		TableName: "NonExistentTable",
		TimeToLiveSpecification: models.TimeToLiveSpecification{
			AttributeName: "ttl",
			Enabled:       true,
		},
	}

	_, err = tm.UpdateTimeToLive(updateReq)
	if err == nil {
		t.Error("Expected error when updating TTL on non-existent table")
	}
}

func TestTableManager_DescribeTimeToLive_NonExistentTable(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-ttl-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	// Try to describe TTL on non-existent table
	_, err = tm.DescribeTimeToLive("NonExistentTable")
	if err == nil {
		t.Error("Expected error when describing TTL on non-existent table")
	}
}
