// Package storage provides tests for DynamoDB Streams.
package storage

import (
	"testing"

	"github.com/e6qu/dyscount/internal/models"
)

func TestStreamManager_EnableStream(t *testing.T) {
	sm := NewStreamManager("/tmp/test", "default")

	t.Run("Enable Stream", func(t *testing.T) {
		stream, err := sm.EnableStream("TestTable", models.StreamViewTypeNewAndOldImages)
		if err != nil {
			t.Fatalf("EnableStream failed: %v", err)
		}

		if stream.StreamArn == "" {
			t.Error("StreamArn should not be empty")
		}

		if stream.StreamStatus != models.StreamStatusEnabled {
			t.Errorf("Expected status ENABLED, got %s", stream.StreamStatus)
		}

		if stream.StreamViewType != models.StreamViewTypeNewAndOldImages {
			t.Errorf("Expected view type NEW_AND_OLD_IMAGES, got %s", stream.StreamViewType)
		}

		if stream.TableName != "TestTable" {
			t.Errorf("Expected TableName=TestTable, got %s", stream.TableName)
		}
	})
}

func TestStreamManager_DescribeStream(t *testing.T) {
	sm := NewStreamManager("/tmp/test", "default")

	t.Run("Describe Existing Stream", func(t *testing.T) {
		stream, err := sm.EnableStream("TestTable", models.StreamViewTypeNewImage)
		if err != nil {
			t.Fatalf("EnableStream failed: %v", err)
		}

		described, err := sm.DescribeStream(stream.StreamArn)
		if err != nil {
			t.Fatalf("DescribeStream failed: %v", err)
		}

		if described.StreamArn != stream.StreamArn {
			t.Errorf("StreamArn mismatch")
		}
	})

	t.Run("Describe NonExistent Stream", func(t *testing.T) {
		_, err := sm.DescribeStream("arn:aws:dynamodb:local:default:table/NonExistent/stream/2024-01-01T00:00:00.000")
		if err == nil {
			t.Error("Expected error for non-existent stream")
		}
	})
}

func TestStreamManager_ListStreams(t *testing.T) {
	sm := NewStreamManager("/tmp/test", "default")

	// Enable streams on multiple tables
	tables := []string{"Table1", "Table2", "Table3"}
	for _, table := range tables {
		_, err := sm.EnableStream(table, models.StreamViewTypeNewImage)
		if err != nil {
			t.Fatalf("EnableStream failed: %v", err)
		}
	}

	t.Run("List All Streams", func(t *testing.T) {
		streams, _, err := sm.ListStreams("")
		if err != nil {
			t.Fatalf("ListStreams failed: %v", err)
		}

		if len(streams) != 3 {
			t.Errorf("Expected 3 streams, got %d", len(streams))
		}
	})

	t.Run("List Streams For Table", func(t *testing.T) {
		streams, _, err := sm.ListStreams("Table1")
		if err != nil {
			t.Fatalf("ListStreams failed: %v", err)
		}

		if len(streams) != 1 {
			t.Errorf("Expected 1 stream, got %d", len(streams))
		}

		if streams[0].TableName != "Table1" {
			t.Errorf("Expected TableName=Table1, got %s", streams[0].TableName)
		}
	})
}

func TestStreamManager_DisableStream(t *testing.T) {
	sm := NewStreamManager("/tmp/test", "default")

	t.Run("Disable Stream", func(t *testing.T) {
		stream, err := sm.EnableStream("TestTable", models.StreamViewTypeNewImage)
		if err != nil {
			t.Fatalf("EnableStream failed: %v", err)
		}

		err = sm.DisableStream("TestTable")
		if err != nil {
			t.Fatalf("DisableStream failed: %v", err)
		}

		described, err := sm.DescribeStream(stream.StreamArn)
		if err != nil {
			t.Fatalf("DescribeStream failed: %v", err)
		}

		if described.StreamStatus != models.StreamStatusDisabled {
			t.Errorf("Expected status DISABLED, got %s", described.StreamStatus)
		}
	})
}

func TestStreamManager_GetShardIterator(t *testing.T) {
	sm := NewStreamManager("/tmp/test", "default")

	t.Run("Get Shard Iterator", func(t *testing.T) {
		stream, err := sm.EnableStream("TestTable", models.StreamViewTypeNewImage)
		if err != nil {
			t.Fatalf("EnableStream failed: %v", err)
		}

		iterator, err := sm.GetShardIterator(stream.StreamArn, "shardId-00000000000000000000-0000000000", "TRIM_HORIZON")
		if err != nil {
			t.Fatalf("GetShardIterator failed: %v", err)
		}

		if iterator == "" {
			t.Error("ShardIterator should not be empty")
		}
	})

	t.Run("Get Shard Iterator NonExistent Stream", func(t *testing.T) {
		_, err := sm.GetShardIterator("arn:aws:dynamodb:local:default:table/NonExistent/stream/2024-01-01T00:00:00.000", "shardId-00000000000000000000-0000000000", "TRIM_HORIZON")
		if err == nil {
			t.Error("Expected error for non-existent stream")
		}
	})
}

func TestStreamManager_WriteAndGetRecords(t *testing.T) {
	sm := NewStreamManager("/tmp/test", "default")

	t.Run("Write and Get Records", func(t *testing.T) {
		stream, err := sm.EnableStream("TestTable", models.StreamViewTypeNewAndOldImages)
		if err != nil {
			t.Fatalf("EnableStream failed: %v", err)
		}

		// Write some records
		oldImage := models.Item{"pk": models.NewStringAttribute("user1"), "name": models.NewStringAttribute("OldName")}
		newImage := models.Item{"pk": models.NewStringAttribute("user1"), "name": models.NewStringAttribute("NewName")}

		err = sm.WriteStreamRecord("TestTable", "MODIFY", oldImage, newImage, models.StreamViewTypeNewAndOldImages)
		if err != nil {
			t.Fatalf("WriteStreamRecord failed: %v", err)
		}

		// Get shard iterator
		iterator, err := sm.GetShardIterator(stream.StreamArn, "shardId-00000000000000000000-0000000000", "TRIM_HORIZON")
		if err != nil {
			t.Fatalf("GetShardIterator failed: %v", err)
		}

		// Get records
		records, _, err := sm.GetRecords(iterator, 10)
		if err != nil {
			t.Fatalf("GetRecords failed: %v", err)
		}

		if len(records) != 1 {
			t.Errorf("Expected 1 record, got %d", len(records))
		} else if records[0].EventName != "MODIFY" {
			t.Errorf("Expected EventName=MODIFY, got %s", records[0].EventName)
		}
	})
}
