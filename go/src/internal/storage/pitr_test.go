// Package storage provides tests for Point-in-Time Recovery (PITR).
package storage

import (
	"os"
	"testing"

	"github.com/e6qu/dyscount/internal/models"
)

func TestPITRManager_UpdateContinuousBackups(t *testing.T) {
	pm := NewPITRManager("/tmp/test", "default")

	t.Run("Enable PITR", func(t *testing.T) {
		desc, err := pm.UpdateContinuousBackups("TestTable", true)
		if err != nil {
			t.Fatalf("UpdateContinuousBackups failed: %v", err)
		}

		if desc.ContinuousBackupsStatus != models.PointInTimeRecoveryStatusEnabled {
			t.Errorf("Expected status ENABLED, got %s", desc.ContinuousBackupsStatus)
		}

		if desc.PointInTimeRecoveryDescription == nil {
			t.Fatal("PointInTimeRecoveryDescription should not be nil")
		}

		if desc.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus != models.PointInTimeRecoveryStatusEnabled {
			t.Errorf("Expected PITR status ENABLED, got %s", desc.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus)
		}
	})

	t.Run("Disable PITR", func(t *testing.T) {
		desc, err := pm.UpdateContinuousBackups("TestTable", false)
		if err != nil {
			t.Fatalf("UpdateContinuousBackups failed: %v", err)
		}

		if desc.ContinuousBackupsStatus != models.PointInTimeRecoveryStatusDisabled {
			t.Errorf("Expected status DISABLED, got %s", desc.ContinuousBackupsStatus)
		}
	})
}

func TestPITRManager_DescribeContinuousBackups(t *testing.T) {
	pm := NewPITRManager("/tmp/test", "default")

	t.Run("Describe Enabled PITR", func(t *testing.T) {
		// Enable first
		_, err := pm.UpdateContinuousBackups("TestTable", true)
		if err != nil {
			t.Fatalf("UpdateContinuousBackups failed: %v", err)
		}

		desc, err := pm.DescribeContinuousBackups("TestTable")
		if err != nil {
			t.Fatalf("DescribeContinuousBackups failed: %v", err)
		}

		if desc.ContinuousBackupsStatus != models.PointInTimeRecoveryStatusEnabled {
			t.Errorf("Expected status ENABLED, got %s", desc.ContinuousBackupsStatus)
		}
	})

	t.Run("Describe Disabled PITR", func(t *testing.T) {
		desc, err := pm.DescribeContinuousBackups("NonExistentTable")
		if err != nil {
			t.Fatalf("DescribeContinuousBackups failed: %v", err)
		}

		if desc.ContinuousBackupsStatus != models.PointInTimeRecoveryStatusDisabled {
			t.Errorf("Expected status DISABLED for new table, got %s", desc.ContinuousBackupsStatus)
		}
	})
}

func TestTableManager_RestoreTableToPointInTime(t *testing.T) {
	// Create temporary directory for test databases
	tempDir, err := os.MkdirTemp("", "dyscount-pitr-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tm, err := NewTableManager(tempDir, "default")
	if err != nil {
		t.Fatalf("Failed to create table manager: %v", err)
	}

	// Create source table
	req := &models.DynamoDBRequest{
		TableName: "SourceTable",
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

	t.Run("Restore Table to Point in Time", func(t *testing.T) {
		restoreReq := &models.RestoreTableToPointInTimeRequest{
			SourceTableName:         "SourceTable",
			TargetTableName:         "RestoredTable",
			UseLatestRestorableTime: true,
		}

		metadata, err := tm.RestoreTableToPointInTime(restoreReq)
		if err != nil {
			t.Fatalf("RestoreTableToPointInTime failed: %v", err)
		}

		if metadata.TableName != "RestoredTable" {
			t.Errorf("Expected TableName=RestoredTable, got %s", metadata.TableName)
		}

		// Verify table exists
		tables, _ := tm.ListTables()
		found := false
		for _, name := range tables {
			if name == "RestoredTable" {
				found = true
				break
			}
		}
		if !found {
			t.Error("Restored table not found in table list")
		}
	})

	t.Run("Restore NonExistent Source Table", func(t *testing.T) {
		restoreReq := &models.RestoreTableToPointInTimeRequest{
			SourceTableName:         "NonExistentTable",
			TargetTableName:         "TargetTable",
			UseLatestRestorableTime: true,
		}

		_, err := tm.RestoreTableToPointInTime(restoreReq)
		if err == nil {
			t.Error("Expected error for non-existent source table")
		}
	})

	t.Run("Restore to Existing Target Table", func(t *testing.T) {
		restoreReq := &models.RestoreTableToPointInTimeRequest{
			SourceTableName:         "SourceTable",
			TargetTableName:         "SourceTable", // Same as source
			UseLatestRestorableTime: true,
		}

		_, err := tm.RestoreTableToPointInTime(restoreReq)
		if err == nil {
			t.Error("Expected error for existing target table")
		}
	})
}
