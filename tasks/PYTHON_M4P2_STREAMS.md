# Task: Python M4 Phase 2 - DynamoDB Streams

## Task ID
PYTHON-M4P2-STREAMS

## Description
Implement DynamoDB Streams for the Python implementation. Streams provide a time-ordered sequence of item-level changes in a table, enabling real-time change data capture (CDC) use cases.

## Background

DynamoDB Streams captures a time-ordered sequence of item-level modifications in any DynamoDB table and stores this information in a log for up to 24 hours. Applications can access this log and view the data items as they appeared before and after they were modified, in near real time.

## Current State

**Python Implementation**: 53/61 operations (87%)
- Missing: Streams (4 operations)
- Goal: 57/61 operations (93%)

## Target State

**Python Implementation**: 57/61 operations (93%)
- Add 4 stream operations
- Enable real-time change data capture

## Operations to Implement (4)

### 1. Enable/Disable Streams on Table
**Operation**: UpdateTable with StreamSpecification
**API**: `DynamoDB_20120810.UpdateTable`

**Request:**
```json
{
  "TableName": "MyTable",
  "StreamSpecification": {
    "StreamEnabled": true,
    "StreamViewType": "NEW_AND_OLD_IMAGES"
  }
}
```

**StreamViewType options:**
- `KEYS_ONLY` - Only key attributes
- `NEW_IMAGE` - Entire item after modification
- `OLD_IMAGE` - Entire item before modification
- `NEW_AND_OLD_IMAGES` - Both before and after

### 2. DescribeStream
**API**: `DynamoDBStreams_20120810.DescribeStream`

**Response:**
```json
{
  "StreamDescription": {
    "StreamArn": "arn:aws:dynamodb:...",
    "StreamStatus": "ENABLED",
    "StreamViewType": "NEW_AND_OLD_IMAGES",
    "Shards": [...]
  }
}
```

### 3. GetShardIterator
**API**: `DynamoDBStreams_20120810.GetShardIterator`

**Request:**
```json
{
  "StreamArn": "arn:aws:dynamodb:...",
  "ShardId": "shardId-...",
  "ShardIteratorType": "TRIM_HORIZON"
}
```

**ShardIteratorType:**
- `TRIM_HORIZON` - Oldest records
- `LATEST` - Newest records
- `AT_SEQUENCE_NUMBER` - At specific sequence
- `AFTER_SEQUENCE_NUMBER` - After specific sequence

### 4. GetRecords
**API**: `DynamoDBStreams_20120810.GetRecords`

**Response:**
```json
{
  "Records": [
    {
      "eventID": "...",
      "eventName": "INSERT|MODIFY|REMOVE",
      "eventVersion": "1.1",
      "eventSource": "aws:dynamodb",
      "awsRegion": "us-east-1",
      "dynamodb": {
        "ApproximateCreationDateTime": 1234567890,
        "Keys": { "pk": {"S": "..."} },
        "NewImage": { ... },
        "OldImage": { ... },
        "SequenceNumber": "...",
        "SizeBytes": 123,
        "StreamViewType": "NEW_AND_OLD_IMAGES"
      }
    }
  ],
  "NextShardIterator": "..."
}
```

## Implementation Plan

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DynamoDB Table                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │ PutItem │  │UpdateItem│  │DeleteItem│                    │
│  └────┬────┘  └────┬────┘  └────┬────┘                     │
│       │            │            │                           │
│       └────────────┼────────────┘                           │
│                    ▼                                        │
│           ┌─────────────────┐                               │
│           │  Stream Writer  │                               │
│           │  (SQLite/WAL)   │                               │
│           └────────┬────────┘                               │
│                    ▼                                        │
│           ┌─────────────────┐                               │
│           │   Stream Log    │                               │
│           │  (per table)    │                               │
│           └─────────────────┘                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  GetRecords API │
                    │  (consumers)    │
                    └─────────────────┘
```

### Week 1: Core Infrastructure

#### Day 1-2: Database Schema
```sql
-- Stream metadata table
CREATE TABLE IF NOT EXISTS __stream_metadata (
    stream_arn TEXT PRIMARY KEY,
    table_name TEXT NOT NULL,
    stream_view_type TEXT NOT NULL,
    stream_status TEXT NOT NULL, -- ENABLED, ENABLING, DISABLED, DISABLING
    creation_time INTEGER NOT NULL,
    latest_stream_label TEXT
);

-- Stream records (WAL-like log)
CREATE TABLE IF NOT EXISTS __stream_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream_arn TEXT NOT NULL,
    shard_id TEXT NOT NULL,
    sequence_number TEXT NOT NULL UNIQUE,
    event_name TEXT NOT NULL, -- INSERT, MODIFY, REMOVE
    event_timestamp INTEGER NOT NULL,
    keys_json TEXT NOT NULL,
    old_image_json TEXT,
    new_image_json TEXT,
    size_bytes INTEGER NOT NULL,
    expires_at INTEGER NOT NULL -- TTL: 24 hours
);

CREATE INDEX idx_stream_shard ON __stream_records(stream_arn, shard_id);
CREATE INDEX idx_stream_sequence ON __stream_records(sequence_number);
CREATE INDEX idx_stream_expires ON __stream_records(expires_at);

-- Shards table
CREATE TABLE IF NOT EXISTS __stream_shards (
    shard_id TEXT PRIMARY KEY,
    stream_arn TEXT NOT NULL,
    parent_shard_id TEXT,
    sequence_number_range_start TEXT NOT NULL,
    sequence_number_range_end TEXT,
    created_at INTEGER NOT NULL
);
```

#### Day 3-4: Stream Manager
**File**: `python/dyscount-core/dyscount/storage/stream_manager.py`

```python
class StreamManager:
    """Manages DynamoDB Streams for tables."""
    
    def enable_stream(
        self, 
        table_name: str, 
        stream_view_type: str
    ) -> str:
        """Enable stream on a table."""
        pass
    
    def disable_stream(self, table_name: str) -> None:
        """Disable stream on a table."""
        pass
    
    def write_stream_record(
        self,
        table_name: str,
        event_name: str,  # INSERT, MODIFY, REMOVE
        keys: dict,
        old_image: Optional[dict] = None,
        new_image: Optional[dict] = None,
    ) -> None:
        """Write a change record to the stream."""
        pass
    
    def get_records(
        self,
        shard_iterator: str,
        limit: int = 100
    ) -> List[StreamRecord]:
        """Get records from a shard."""
        pass
    
    def get_shard_iterator(
        self,
        stream_arn: str,
        shard_id: str,
        iterator_type: str,
        sequence_number: Optional[str] = None
    ) -> str:
        """Get a shard iterator."""
        pass
    
    def describe_stream(
        self,
        stream_arn: str
    ) -> StreamDescription:
        """Describe a stream."""
        pass
```

#### Day 5: Integration with Write Operations
Modify `ItemManager` to write to streams:

```python
# In put_item, update_item, delete_item
if stream_enabled:
    stream_manager.write_stream_record(
        table_name=table_name,
        event_name="INSERT",  # or "MODIFY", "REMOVE"
        keys=extract_keys(item),
        old_image=old_item if stream_view_type in ["OLD_IMAGE", "NEW_AND_OLD_IMAGES"] else None,
        new_image=new_item if stream_view_type in ["NEW_IMAGE", "NEW_AND_OLD_IMAGES"] else None,
    )
```

### Week 2: API Implementation

#### Day 6-7: Stream Handlers
**File**: `python/dyscount-api/dyscount/handlers/streams.py`

Implement 4 API operations:
- `update_table` - Enable/disable streams
- `describe_stream` - Get stream info
- `get_shard_iterator` - Get iterator
- `get_records` - Get change records

#### Day 8-9: Testing
- Unit tests for StreamManager
- Integration tests for stream operations
- End-to-end tests with real consumers

#### Day 10: Documentation
- API documentation
- Usage examples
- Architecture docs

## Data Models

### StreamRecord
```python
class StreamRecord:
    event_id: str
    event_name: str  # INSERT, MODIFY, REMOVE
    event_version: str = "1.1"
    event_source: str = "aws:dynamodb"
    aws_region: str
    dynamodb: DynamoDBStreamRecord

class DynamoDBStreamRecord:
    approximate_creation_date_time: int
    keys: Dict[str, AttributeValue]
    new_image: Optional[Dict[str, AttributeValue]]
    old_image: Optional[Dict[str, AttributeValue]]
    sequence_number: str
    size_bytes: int
    stream_view_type: str
```

### StreamDescription
```python
class StreamDescription:
    stream_arn: str
    stream_label: str
    stream_status: str  # ENABLED, ENABLING, DISABLED, DISABLING
    stream_view_type: str
    creation_date_time: int
    table_name: str
    key_schema: List[KeySchemaElement]
    shards: List[Shard]
```

### Shard
```python
class Shard:
    shard_id: str
    sequence_number_range: SequenceNumberRange
    parent_shard_id: Optional[str]

class SequenceNumberRange:
    starting_sequence_number: str
    ending_sequence_number: Optional[str]
```

## Acceptance Criteria

- [ ] Enable stream on table with StreamSpecification
- [ ] Disable stream on table
- [ ] DescribeStream returns correct stream metadata
- [ ] GetShardIterator returns valid iterator
- [ ] GetRecords returns change records in order
- [ ] Stream records include correct view type (KEYS_ONLY, NEW_IMAGE, etc.)
- [ ] Stream records expire after 24 hours (TTL)
- [ ] Records include both old and new images when configured
- [ ] Sequence numbers are monotonically increasing
- [ ] Shards are properly managed
- [ ] Integration with write operations (PutItem, UpdateItem, DeleteItem)

## Testing Strategy

### Unit Tests
```python
def test_enable_stream():
    """Test enabling stream on table."""
    pass

def test_disable_stream():
    """Test disabling stream on table."""
    pass

def test_stream_record_creation():
    """Test creating stream records."""
    pass

def test_get_records():
    """Test getting records from stream."""
    pass
```

### Integration Tests
```python
def test_stream_with_put_item():
    """Test stream captures put_item operations."""
    pass

def test_stream_with_update_item():
    """Test stream captures update_item operations."""
    pass

def test_stream_with_delete_item():
    """Test stream captures delete_item operations."""
    pass

def test_stream_view_types():
    """Test different stream view types."""
    pass
```

## Definition of Done

- [ ] All 4 stream operations implemented
- [ ] Stream records written on all write operations
- [ ] 15+ new tests passing
- [ ] Integration tests with real consumers
- [ ] Documentation complete
- [ ] PR merged to main
- [ ] Task file moved to done/

## Estimated Effort

**2 weeks** (10 days)

## Dependencies

- SQLite (already in use)
- Existing Python implementation (control plane, data plane)
- FastAPI (already in use)
