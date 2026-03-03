// Package storage provides DynamoDB Streams support.
package storage

import (
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/e6qu/dyscount/internal/models"
	"github.com/google/uuid"
)

// StreamManager manages DynamoDB Streams.
type StreamManager struct {
	dataDirectory string
	namespace     string
	mu            sync.RWMutex
	streams       map[string]*models.StreamDescription
	records       map[string][]models.Record
}

// NewStreamManager creates a new StreamManager.
func NewStreamManager(dataDirectory, namespace string) *StreamManager {
	return &StreamManager{
		dataDirectory: dataDirectory,
		namespace:     namespace,
		streams:       make(map[string]*models.StreamDescription),
		records:       make(map[string][]models.Record),
	}
}

// EnableStream enables a stream on a table.
func (sm *StreamManager) EnableStream(tableName string, streamViewType models.StreamViewType) (*models.StreamDescription, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	streamArn := sm.generateStreamArn(tableName)
	
	stream := &models.StreamDescription{
		StreamArn:      streamArn,
		StreamLabel:    time.Now().Format("2006-01-02T15:04:05.000"),
		StreamStatus:   models.StreamStatusEnabled,
		StreamViewType: streamViewType,
		TableName:      tableName,
		KeySchema: []models.KeySchemaElement{
			{AttributeName: "pk", KeyType: "HASH"},
		},
		Shards: []models.Shard{
			{
				ShardId: "shardId-00000000000000000000-0000000000",
				SequenceNumberRange: models.SequenceNumberRange{
					StartingSequenceNumber: "100000000000000000000",
				},
			},
		},
	}

	sm.streams[streamArn] = stream
	sm.records[streamArn] = []models.Record{}

	return stream, nil
}

// DisableStream disables a stream on a table.
func (sm *StreamManager) DisableStream(tableName string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	streamArn := sm.generateStreamArn(tableName)
	if stream, ok := sm.streams[streamArn]; ok {
		stream.StreamStatus = models.StreamStatusDisabled
	}

	return nil
}

// DescribeStream returns stream details.
func (sm *StreamManager) DescribeStream(streamArn string) (*models.StreamDescription, error) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	if stream, ok := sm.streams[streamArn]; ok {
		return stream, nil
	}

	return nil, fmt.Errorf("stream not found: %s", streamArn)
}

// ListStreams lists all streams.
func (sm *StreamManager) ListStreams(tableName string) ([]models.Stream, string, error) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	var streams []models.Stream
	for _, desc := range sm.streams {
		if tableName != "" && desc.TableName != tableName {
			continue
		}
		streams = append(streams, models.Stream{
			StreamArn:    desc.StreamArn,
			StreamLabel:  desc.StreamLabel,
			StreamStatus: desc.StreamStatus,
			TableName:    desc.TableName,
		})
	}

	return streams, "", nil
}

// GetShardIterator returns a shard iterator.
func (sm *StreamManager) GetShardIterator(streamArn, shardId, shardIteratorType string) (string, error) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	if _, ok := sm.streams[streamArn]; !ok {
		return "", fmt.Errorf("stream not found: %s", streamArn)
	}

	// Generate iterator token
	iteratorToken := fmt.Sprintf("%s|%s|%s|%d", streamArn, shardId, shardIteratorType, time.Now().Unix())
	return iteratorToken, nil
}

// GetRecords returns records from a stream.
func (sm *StreamManager) GetRecords(shardIterator string, limit int) ([]models.Record, string, error) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	// Parse iterator to get stream ARN
	// Format: streamArn|shardId|shardIteratorType|timestamp
	parts := strings.Split(shardIterator, "|")
	if len(parts) < 1 {
		return []models.Record{}, "", fmt.Errorf("invalid shard iterator")
	}
	streamArn := parts[0]
	
	// Find stream
	records, ok := sm.records[streamArn]
	if !ok {
		return []models.Record{}, "", nil
	}

	// Apply limit
	if limit > 0 && len(records) > limit {
		records = records[:limit]
	}

	// Generate next iterator
	nextIterator := ""
	if len(records) > 0 {
		nextIterator = fmt.Sprintf("%s|shardId-00000000000000000000-0000000000|LATEST|%d", streamArn, time.Now().Unix())
	}

	return records, nextIterator, nil
}

// WriteStreamRecord writes a record to a stream.
func (sm *StreamManager) WriteStreamRecord(tableName, eventName string, oldImage, newImage models.Item, streamViewType models.StreamViewType) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	streamArn := sm.generateStreamArn(tableName)
	stream, ok := sm.streams[streamArn]
	if !ok || stream.StreamStatus != models.StreamStatusEnabled {
		return nil // Stream not enabled
	}

	record := models.Record{
		AwsRegion:      "local",
		EventID:        uuid.New().String(),
		EventName:      eventName,
		EventSource:    "aws:dynamodb",
		EventVersion:   "1.1",
		EventSourceARN: streamArn,
		Dynamodb: models.StreamRecord{
			ApproximateCreationDateTime: time.Now().Unix(),
			SequenceNumber:              fmt.Sprintf("%d", time.Now().UnixNano()),
			StreamViewType:              streamViewType,
		},
	}

	// Apply stream view type
	switch streamViewType {
	case models.StreamViewTypeNewImage:
		record.Dynamodb.NewImage = newImage
	case models.StreamViewTypeOldImage:
		record.Dynamodb.OldImage = oldImage
	case models.StreamViewTypeNewAndOldImages:
		record.Dynamodb.NewImage = newImage
		record.Dynamodb.OldImage = oldImage
	case models.StreamViewTypeKeysOnly:
		// Only keys
	}

	// Extract keys
	if newImage != nil {
		record.Dynamodb.Keys = extractKeys(newImage, stream.KeySchema)
	} else if oldImage != nil {
		record.Dynamodb.Keys = extractKeys(oldImage, stream.KeySchema)
	}

	sm.records[streamArn] = append(sm.records[streamArn], record)
	return nil
}

// generateStreamArn generates a stream ARN.
func (sm *StreamManager) generateStreamArn(tableName string) string {
	return fmt.Sprintf("arn:aws:dynamodb:local:%s:table/%s/stream/%s", 
		sm.namespace, tableName, time.Now().Format("2006-01-02T15:04:05.000"))
}

// extractKeys extracts key attributes from an item.
func extractKeys(item models.Item, keySchema []models.KeySchemaElement) models.Item {
	keys := make(models.Item)
	for _, ks := range keySchema {
		if val, ok := item[ks.AttributeName]; ok {
			keys[ks.AttributeName] = val
		}
	}
	return keys
}
