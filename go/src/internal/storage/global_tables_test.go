// Package storage provides tests for Global Tables.
package storage

import (
	"fmt"
	"testing"
	"time"

	"github.com/e6qu/dyscount/internal/models"
)

func TestGlobalTableManager_CreateGlobalTable(t *testing.T) {
	gtm := NewGlobalTableManager("/tmp/test", "default")

	t.Run("Create Global Table", func(t *testing.T) {
		req := &models.CreateGlobalTableRequest{
			GlobalTableName: "TestGlobalTable",
			ReplicationGroup: []models.Replica{
				{RegionName: "us-east-1"},
				{RegionName: "us-west-2"},
			},
		}

		desc, err := gtm.CreateGlobalTable(req)
		if err != nil {
			t.Fatalf("CreateGlobalTable failed: %v", err)
		}

		if desc.GlobalTableName != "TestGlobalTable" {
			t.Errorf("Expected GlobalTableName=TestGlobalTable, got %s", desc.GlobalTableName)
		}

		if desc.GlobalTableStatus != models.GlobalTableStatusCreating {
			t.Errorf("Expected status CREATING, got %s", desc.GlobalTableStatus)
		}

		if len(desc.ReplicationGroup) != 2 {
			t.Errorf("Expected 2 replicas, got %d", len(desc.ReplicationGroup))
		}
	})

	t.Run("Create Duplicate Global Table", func(t *testing.T) {
		req := &models.CreateGlobalTableRequest{
			GlobalTableName: "TestGlobalTable",
			ReplicationGroup: []models.Replica{
				{RegionName: "us-east-1"},
			},
		}

		_, err := gtm.CreateGlobalTable(req)
		if err == nil {
			t.Error("Expected error for duplicate global table")
		}
	})
}

func TestGlobalTableManager_DescribeGlobalTable(t *testing.T) {
	gtm := NewGlobalTableManager("/tmp/test", "default")

	// Create a global table first
	createReq := &models.CreateGlobalTableRequest{
		GlobalTableName: "TestGlobalTable",
		ReplicationGroup: []models.Replica{
			{RegionName: "us-east-1"},
		},
	}
	_, err := gtm.CreateGlobalTable(createReq)
	if err != nil {
		t.Fatalf("CreateGlobalTable failed: %v", err)
	}

	t.Run("Describe Existing Global Table", func(t *testing.T) {
		desc, err := gtm.DescribeGlobalTable("TestGlobalTable")
		if err != nil {
			t.Fatalf("DescribeGlobalTable failed: %v", err)
		}

		if desc.GlobalTableName != "TestGlobalTable" {
			t.Errorf("Expected GlobalTableName=TestGlobalTable, got %s", desc.GlobalTableName)
		}
	})

	t.Run("Describe NonExistent Global Table", func(t *testing.T) {
		_, err := gtm.DescribeGlobalTable("NonExistentTable")
		if err == nil {
			t.Error("Expected error for non-existent global table")
		}
	})
}

func TestGlobalTableManager_ListGlobalTables(t *testing.T) {
	gtm := NewGlobalTableManager("/tmp/test", "default")

	// Create multiple global tables
	for i := 0; i < 3; i++ {
		req := &models.CreateGlobalTableRequest{
			GlobalTableName: fmt.Sprintf("GlobalTable%d", i),
			ReplicationGroup: []models.Replica{
				{RegionName: "us-east-1"},
			},
		}
		_, err := gtm.CreateGlobalTable(req)
		if err != nil {
			t.Fatalf("CreateGlobalTable failed: %v", err)
		}
	}

	t.Run("List All Global Tables", func(t *testing.T) {
		tables, _, err := gtm.ListGlobalTables(0, "")
		if err != nil {
			t.Fatalf("ListGlobalTables failed: %v", err)
		}

		if len(tables) != 3 {
			t.Errorf("Expected 3 global tables, got %d", len(tables))
		}
	})

	t.Run("List Global Tables With Limit", func(t *testing.T) {
		tables, _, err := gtm.ListGlobalTables(2, "")
		if err != nil {
			t.Fatalf("ListGlobalTables failed: %v", err)
		}

		if len(tables) != 2 {
			t.Errorf("Expected 2 global tables, got %d", len(tables))
		}
	})
}

func TestGlobalTableManager_UpdateGlobalTable(t *testing.T) {
	gtm := NewGlobalTableManager("/tmp/test", "default")

	// Create a global table first
	createReq := &models.CreateGlobalTableRequest{
		GlobalTableName: "TestGlobalTable",
		ReplicationGroup: []models.Replica{
			{RegionName: "us-east-1"},
		},
	}
	_, err := gtm.CreateGlobalTable(createReq)
	if err != nil {
		t.Fatalf("CreateGlobalTable failed: %v", err)
	}

	// Wait for activation
	time.Sleep(3 * time.Second)

	t.Run("Add Replica", func(t *testing.T) {
		req := &models.UpdateGlobalTableRequest{
			GlobalTableName: "TestGlobalTable",
			ReplicaUpdates: []models.ReplicaUpdate{
				{
					Create: &models.CreateReplicaAction{
						RegionName: "eu-west-1",
					},
				},
			},
		}

		desc, err := gtm.UpdateGlobalTable(req)
		if err != nil {
			t.Fatalf("UpdateGlobalTable failed: %v", err)
		}

		// Should have 2 replicas now
		if len(desc.ReplicationGroup) != 2 {
			t.Errorf("Expected 2 replicas, got %d", len(desc.ReplicationGroup))
		}
	})

	t.Run("Remove Replica", func(t *testing.T) {
		req := &models.UpdateGlobalTableRequest{
			GlobalTableName: "TestGlobalTable",
			ReplicaUpdates: []models.ReplicaUpdate{
				{
					Delete: &models.DeleteReplicaAction{
						RegionName: "eu-west-1",
					},
				},
			},
		}

		desc, err := gtm.UpdateGlobalTable(req)
		if err != nil {
			t.Fatalf("UpdateGlobalTable failed: %v", err)
		}

		// Should have 1 replica now
		if len(desc.ReplicationGroup) != 1 {
			t.Errorf("Expected 1 replica, got %d", len(desc.ReplicationGroup))
		}
	})

	t.Run("Update NonExistent Global Table", func(t *testing.T) {
		req := &models.UpdateGlobalTableRequest{
			GlobalTableName: "NonExistentTable",
			ReplicaUpdates: []models.ReplicaUpdate{
				{
					Create: &models.CreateReplicaAction{
						RegionName: "us-west-2",
					},
				},
			},
		}

		_, err := gtm.UpdateGlobalTable(req)
		if err == nil {
			t.Error("Expected error for non-existent global table")
		}
	})
}

func TestGlobalTableManager_UpdateGlobalTableSettings(t *testing.T) {
	gtm := NewGlobalTableManager("/tmp/test", "default")

	// Create a global table first
	createReq := &models.CreateGlobalTableRequest{
		GlobalTableName: "TestGlobalTable",
		ReplicationGroup: []models.Replica{
			{RegionName: "us-east-1"},
		},
	}
	_, err := gtm.CreateGlobalTable(createReq)
	if err != nil {
		t.Fatalf("CreateGlobalTable failed: %v", err)
	}

	t.Run("Update Global Table Settings", func(t *testing.T) {
		req := &models.UpdateGlobalTableSettingsRequest{
			GlobalTableName: "TestGlobalTable",
			ReplicaSettingsUpdate: []models.ReplicaSettingsUpdate{
				{
					RegionName: "us-east-1",
				},
			},
		}

		desc, err := gtm.UpdateGlobalTableSettings(req)
		if err != nil {
			t.Fatalf("UpdateGlobalTableSettings failed: %v", err)
		}

		if desc.GlobalTableName != "TestGlobalTable" {
			t.Errorf("Expected GlobalTableName=TestGlobalTable, got %s", desc.GlobalTableName)
		}
	})
}
