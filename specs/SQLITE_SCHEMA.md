# DynamoDB to SQLite Schema Mapping Design

This document outlines the design for mapping DynamoDB concepts to SQLite storage for the Dyscount project.

## Overview

DynamoDB Local uses SQLite internally, storing all tables in a single database file (`shared-local-instance.db`). However, for Dyscount, we use **one SQLite file per DynamoDB table** as per project requirements. This provides better isolation, easier backup/restore per table, and cleaner resource management.

## 1. Core Table Schema

### 1.1 Items Table (`items`)

Stores the actual DynamoDB items with a key-value approach:

```sql
CREATE TABLE items (
    -- Primary key components (DynamoDB partition key + optional sort key)
    pk BLOB NOT NULL,              -- Partition key value (binary for flexibility)
    sk BLOB,                       -- Sort key value (NULL for simple primary key tables)
    
    -- Metadata
    version INTEGER DEFAULT 1,     -- For optimistic locking
    created_at INTEGER NOT NULL,   -- Unix timestamp (milliseconds)
    updated_at INTEGER NOT NULL,   -- Unix timestamp (milliseconds)
    
    -- Serialized item data
    item_data BLOB NOT NULL,       -- Full item as serialized blob (JSON/MessagePack)
    
    -- Primary key type information for reconstruction
    pk_type TEXT NOT NULL CHECK(pk_type IN ('S', 'N', 'B')),  -- String, Number, Binary
    sk_type TEXT CHECK(sk_type IN ('S', 'N', 'B', NULL)),
    
    PRIMARY KEY (pk, sk)
);

-- Index for efficient sorting on sort key
CREATE INDEX idx_items_sk ON items(sk);

-- Index for time-based queries (TTL, recent items)
CREATE INDEX idx_items_updated ON items(updated_at);
```

**Key Design Decisions:**

- **pk/sk as BLOB**: DynamoDB keys can be String (S), Number (N), or Binary (B). Storing as BLOB allows uniform handling:
  - Strings: UTF-8 encoded bytes
  - Numbers: IEEE 754 binary64 double-precision (8 bytes) or string representation for precision
  - Binary: Stored as-is

- **Composite PK**: SQLite's composite primary key `(pk, sk)` provides:
  - Unique constraint for the full DynamoDB primary key
  - Efficient range queries on sort key within a partition
  - Clustered index storage for locality

- **item_data as BLOB**: Stores the complete item including all attributes. This enables:
  - Fast retrieval without joins
  - Preservation of attribute ordering (DynamoDB maintains order)
  - Easy atomic updates

### 1.2 Alternative: Separate Key Storage (for large items)

For tables with very large items or frequent partial updates:

```sql
CREATE TABLE items (
    pk BLOB NOT NULL,
    sk BLOB,
    
    -- Top-level scalar attributes extracted for indexing/filtering
    -- (Optional optimization, populated based on projection needs)
    
    -- Metadata
    version INTEGER DEFAULT 1,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    
    PRIMARY KEY (pk, sk)
);

CREATE TABLE item_attributes (
    pk BLOB NOT NULL,
    sk BLOB,
    attr_path TEXT NOT NULL,       -- JSON path: "name", "address.city", "tags[0]"
    attr_type TEXT NOT NULL CHECK(attr_type IN ('S', 'N', 'B', 'BOOL', 'NULL', 'L', 'M', 'SS', 'NS', 'BS')),
    attr_value BLOB,               -- Serialized value
    
    PRIMARY KEY (pk, sk, attr_path),
    FOREIGN KEY (pk, sk) REFERENCES items(pk, sk) ON DELETE CASCADE
);
```

**Note**: The attribute-decomposed approach is more complex. For MVP, the single BLOB approach is recommended.

## 2. Index Schema Design

### 2.1 Global Secondary Indexes (GSI)

Each GSI gets its own table in the same SQLite database file:

```sql
-- GSI table naming: gsi_<index_name>
CREATE TABLE gsi_<index_name> (
    -- GSI key attributes
    gsi_pk BLOB NOT NULL,          -- GSI partition key
    gsi_sk BLOB,                   -- GSI sort key (optional)
    
    -- Reference to base table item
    pk BLOB NOT NULL,              -- Base table partition key
    sk BLOB,                       -- Base table sort key
    
    -- Projected attributes (if projection is KEYS_ONLY, this can be omitted)
    projected_data BLOB,           -- Serialized projected attributes
    
    PRIMARY KEY (gsi_pk, gsi_sk, pk, sk)
);

-- Index for range queries on GSI sort key
CREATE INDEX idx_gsi_<index_name>_sk ON gsi_<index_name>(gsi_pk, gsi_sk);

-- Index for reverse lookups (when deleting/updating base table items)
CREATE INDEX idx_gsi_<index_name>_base ON gsi_<index_name>(pk, sk);
```

**GSI Characteristics:**
- **Eventually Consistent**: Updates to GSI are asynchronous (or transaction-bound)
- **Sparse Index**: Only items with the GSI key attributes are indexed
- **Non-unique keys**: Multiple items can have the same GSI key (hence full primary key in PK)

### 2.2 Local Secondary Indexes (LSI)

LSI shares the partition key with the base table but has a different sort key:

```sql
-- LSI table naming: lsi_<index_name>
CREATE TABLE lsi_<index_name> (
    -- Same partition key as base table
    pk BLOB NOT NULL,              -- Same as items.pk
    
    -- LSI sort key
    lsi_sk BLOB NOT NULL,          -- LSI sort key value
    
    -- Reference for full item retrieval
    sk BLOB,                       -- Base table sort key
    
    -- Projected attributes
    projected_data BLOB,
    
    PRIMARY KEY (pk, lsi_sk, sk)
);

-- Index for reverse lookups
CREATE INDEX idx_lsi_<index_name>_base ON lsi_<index_name>(pk, sk);
```

**LSI Characteristics:**
- **Strongly Consistent**: Updated in the same transaction as base table
- **Same Partition**: All LSI entries for a partition are stored together
- **Item Collection Size Limit**: Must track total size per partition (10GB limit in DynamoDB)

### 2.3 Index Maintenance Strategy

**For Updates:**

```sql
-- Transaction-based index maintenance
BEGIN TRANSACTION;

-- 1. Fetch old item to determine index key changes
SELECT item_data FROM items WHERE pk = ? AND sk = ?;

-- 2. Calculate old and new index keys
-- (Parse item_data, extract GSI/LSI key attributes)

-- 3. Update base table
UPDATE items SET item_data = ?, updated_at = ? WHERE pk = ? AND sk = ?;

-- 4. Update/remove GSI entries as needed
DELETE FROM gsi_<name> WHERE pk = ? AND sk = ? AND gsi_pk = ? AND gsi_sk = ?;  -- Old entry
INSERT INTO gsi_<name> (gsi_pk, gsi_sk, pk, sk, projected_data) VALUES (...); -- New entry

COMMIT;
```

**Write Modes:**

1. **Synchronous (default for LSI, optional for GSI)**:
   - Index updated in same transaction
   - Higher latency, guaranteed consistency

2. **Asynchronous (GSI)**:
   - Changes queued and applied in background
   - Better write throughput
   - Eventual consistency

## 3. Data Type Storage

### 3.1 Serialization Format Comparison

| Format | Size | Speed | Queryable | Notes |
|--------|------|-------|-----------|-------|
| **JSON** | Medium | Medium | Via JSON1 ext | Human-readable, widely supported |
| **MessagePack** | Small | Fast | Requires parsing | Binary, efficient, no schema |
| **BSON** | Large | Medium | Partial | MongoDB format, overkill |
| **SQLite JSONB** | Small | Fast | Native JSONB funcs | SQLite 3.45+, optimal |

**Recommendation: MessagePack** for storage, with optional JSON for debugging.

### 3.2 DynamoDB Type Mapping

DynamoDB uses typed attributes in a JSON-like structure:

```json
{
    "UserId": {"S": "user123"},
    "Age": {"N": "25"},
    "Scores": {"NS": ["100", "95", "87"]},
    "Address": {"M": {
        "Street": {"S": "123 Main St"},
        "Zip": {"N": "12345"}
    }},
    "Tags": {"L": [{"S": "premium"}, {"BOOL": true}]},
    "Data": {"B": "base64encoded..."},
    "Flags": {"SS": ["a", "b", "c"]}
}
```

**Storage in SQLite:**

```sql
-- Full item stored as MessagePack in item_data column
-- Structure preserves DynamoDB type annotations:
-- {
--     "UserId": ("S", "user123"),
--     "Age": ("N", "25"),
--     "Scores": ("NS", ["100", "95", "87"]),
--     ...
-- }
```

### 3.3 Key Serialization

For consistent ordering and storage:

```python
# Key serialization strategy
def serialize_key(value, dtype):
    """
    Returns bytes for storage as BLOB.
    Ensures proper lexicographical ordering for range queries.
    """
    if dtype == 'S':
        return value.encode('utf-8')
    elif dtype == 'N':
        # DynamoDB numbers are decimal with 38-digit precision
        # Normalize: remove leading zeros, handle negatives
        # Pad for proper ordering: sign + exponent + mantissa
        return encode_dynamodb_number(value)
    elif dtype == 'B':
        return base64.b64decode(value)
    else:
        raise ValueError(f"Invalid key type: {dtype}")
```

**Number Encoding for Ordering:**

DynamoDB numbers must sort correctly (e.g., -10 < -1 < 0 < 1 < 10). Use:
- Sign-magnitude with exponent normalization, OR
- Store as string with fixed-width formatting for comparison

## 4. Table Metadata Storage

### 4.1 Table Catalog (per SQLite file)

```sql
CREATE TABLE __table_metadata (
    key TEXT PRIMARY KEY,
    value BLOB
);

-- Table definition
INSERT INTO __table_metadata VALUES ('table_name', 'MyTable');
INSERT INTO __table_metadata VALUES ('creation_time', '1699999999999');
INSERT INTO __table_metadata VALUES ('table_status', 'ACTIVE');
INSERT INTO __table_metadata VALUES ('item_count', '0');
INSERT INTO __table_metadata VALUES ('table_size_bytes', '0');

-- Key schema (stored as MessagePack/JSON)
INSERT INTO __table_metadata VALUES ('key_schema', 
    '{"hash_key": {"name": "UserId", "type": "S"}, "range_key": {"name": "Timestamp", "type": "N"}}');

-- Attribute definitions
INSERT INTO __table_metadata VALUES ('attribute_definitions',
    '[{"name": "UserId", "type": "S"}, {"name": "Timestamp", "type": "N"}]');

-- Provisioned throughput (for compatibility)
INSERT INTO __table_metadata VALUES ('provisioned_throughput',
    '{"read": 5, "write": 5}');

-- TTL configuration
INSERT INTO __table_metadata VALUES ('ttl_specification',
    '{"attribute_name": "expires_at", "enabled": true}');
```

### 4.2 Index Metadata

```sql
CREATE TABLE __index_metadata (
    index_name TEXT PRIMARY KEY,
    index_type TEXT NOT NULL CHECK(index_type IN ('GSI', 'LSI')),
    key_schema BLOB NOT NULL,           -- Serialized key schema
    projection_type TEXT NOT NULL CHECK(projection_type IN ('KEYS_ONLY', 'INCLUDE', 'ALL')),
    projected_attributes BLOB,          -- Array of attribute names (for INCLUDE)
    index_status TEXT,                  -- For GSI: CREATING, ACTIVE, etc.
    backfilling INTEGER,                -- 0 or 1 (GSI creation)
    provisioned_throughput BLOB         -- For GSI
);

-- Example GSI entry
INSERT INTO __index_metadata VALUES (
    'GameTitleIndex',
    'GSI',
    '{"hash_key": {"name": "GameTitle", "type": "S"}, "range_key": {"name": "TopScore", "type": "N"}}',
    'INCLUDE',
    '["UserId", "Wins", "Losses"]',
    'ACTIVE',
    0,
    '{"read": 5, "write": 5}'
);

-- Example LSI entry
INSERT INTO __index_metadata VALUES (
    'TimestampIndex',
    'LSI',
    '{"hash_key": {"name": "UserId", "type": "S"}, "range_key": {"name": "Timestamp", "type": "N"}}',
    'ALL',
    NULL,
    NULL,
    NULL,
    NULL
);
```

### 4.3 Statistics and Bookkeeping

```sql
CREATE TABLE __table_stats (
    stat_name TEXT PRIMARY KEY,
    stat_value INTEGER,
    last_updated INTEGER
);

INSERT INTO __table_stats VALUES ('item_count', 0, 1699999999999);
INSERT INTO __table_stats VALUES ('total_size_bytes', 0, 1699999999999);
INSERT INTO __table_stats VALUES ('gsi_<name>_item_count', 0, 1699999999999);
```

## 5. Query Patterns

### 5.1 GetItem (Point Query)

```sql
SELECT item_data FROM items 
WHERE pk = ? AND sk = ?;
```

### 5.2 Query (Partition + Range)

```sql
-- Exact partition key, range on sort key
SELECT item_data FROM items 
WHERE pk = ? 
  AND sk BETWEEN ? AND ?
ORDER BY sk ASC  -- or DESC
LIMIT ?;

-- With filter expression (post-processing in code or using JSON functions)
SELECT item_data FROM items 
WHERE pk = ? 
  AND sk > ?
  AND json_extract(item_data, '$.Status.S') = 'ACTIVE'
ORDER BY sk ASC
LIMIT ?;
```

### 5.3 Query on GSI

```sql
-- Query GSI table, then fetch full items if needed
SELECT gsi.pk, gsi.sk, gsi.projected_data 
FROM gsi_<name> AS gsi
WHERE gsi.gsi_pk = ?
  AND gsi.gsi_sk BETWEEN ? AND ?
ORDER BY gsi.gsi_sk ASC
LIMIT ?;

-- If projection = ALL or need non-projected attributes:
SELECT i.item_data 
FROM items AS i
INNER JOIN (
    SELECT pk, sk FROM gsi_<name>
    WHERE gsi_pk = ? AND gsi_sk > ?
    ORDER BY gsi_sk ASC
    LIMIT ?
) AS gsi ON i.pk = gsi.pk AND i.sk = gsi.sk;
```

### 5.4 Scan

```sql
-- Full table scan with pagination (offset-based, less efficient)
SELECT item_data FROM items 
WHERE rowid > ?  -- Cursor-based pagination
ORDER BY rowid
LIMIT ?;

-- Parallel scan simulation (segment-based)
-- Use hash(pk) % total_segments = segment_number
SELECT item_data FROM items 
WHERE abs(cast(pk AS INTEGER)) % ? = ?
LIMIT ?;
```

## 6. Update Strategies

### 6.1 Immutable Rows (Versioning)

For audit trails or time-travel queries:

```sql
-- Items table with versioned entries
CREATE TABLE items (
    pk BLOB NOT NULL,
    sk BLOB,
    version INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    item_data BLOB NOT NULL,
    is_current INTEGER DEFAULT 1,  -- 1 = current, 0 = historical
    
    PRIMARY KEY (pk, sk, version)
);

CREATE INDEX idx_items_current ON items(pk, sk, is_current) WHERE is_current = 1;
```

**Trade-offs:**
- Pros: Full history, point-in-time recovery
- Cons: Storage overhead, complex cleanup

### 6.2 Update In-Place (Recommended)

```sql
-- Standard UPDATE for item modification
UPDATE items 
SET item_data = ?, updated_at = ?, version = version + 1
WHERE pk = ? AND sk = ? AND version = ?;  -- Optimistic locking

-- Conditional update using CASE
UPDATE items 
SET item_data = CASE 
    WHEN json_extract(item_data, '$.Version.N') > ? THEN ?
    ELSE item_data 
END
WHERE pk = ? AND sk = ?;
```

## 7. SQLite Best Practices for This Use Case

### 7.1 Performance Optimizations

```sql
-- WAL mode for better concurrent reads/writes
PRAGMA journal_mode = WAL;

-- Normal synchronous mode (balance safety/performance)
PRAGMA synchronous = NORMAL;

-- Memory-mapped I/O for faster access (optional)
PRAGMA mmap_size = 268435456;  -- 256MB

-- Foreign keys for referential integrity (index tables)
PRAGMA foreign_keys = ON;

-- Temporary storage in memory
PRAGMA temp_store = MEMORY;
```

### 7.2 Page Size and Cache

```sql
-- Larger page size for blob-heavy workloads
PRAGMA page_size = 4096;  -- or 8192 for larger items

-- Increase cache size for better performance
PRAGMA cache_size = -32768;  -- 32MB (negative = kilobytes)
```

### 7.3 Index Maintenance

```sql
-- Run periodically to optimize query performance
ANALYZE;

-- Reclaim space after deletions (run during low traffic)
VACUUM;
```

## 8. DynamoDB Local Reference

DynamoDB Local (AWS's official local emulator) stores data in SQLite with the following characteristics:

- **Storage**: Single SQLite file (`shared-local-instance.db` or per-table files)
- **Schema**: Uses generic tables with EAV-like structure
- **Blobs**: Stores serialized item data similar to our approach
- **Indexes**: Creates separate tables for GSI/LSI with denormalized data

Key differences from Dyscount approach:
1. DynamoDB Local uses Java with SQLite JDBC
2. Shared DB mode stores all tables in one file
3. Optimized for API compatibility, not performance

## 9. Implementation Recommendations

### 9.1 File Structure

```
/data
  /<table_name>.db          -- Main table SQLite file
    - items table
    - gsi_* tables
    - lsi_* tables
    - __table_metadata
    - __index_metadata
    - __table_stats
```

### 9.2 Connection Pooling

- Use connection pooling per SQLite file
- Maximum 1 writer at a time (SQLite limitation)
- Multiple readers allowed with WAL mode

### 9.3 Migration Strategy

```sql
-- Schema versioning in each SQLite file
CREATE TABLE __schema_version (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER NOT NULL,
    description TEXT
);
```

## 10. Summary

| DynamoDB Concept | SQLite Implementation |
|------------------|----------------------|
| Table | Single SQLite file |
| Item | Row in `items` table with serialized BLOB |
| Partition Key | `pk` column (BLOB) |
| Sort Key | `sk` column (BLOB, nullable) |
| GSI | Separate table `gsi_<name>` with denormalized keys |
| LSI | Separate table `lsi_<name>` sharing partition key |
| Data Types | Preserved in MessagePack/JSON serialization |
| Attributes | Stored in `item_data` BLOB (single-table design) |
| Metadata | `__table_metadata`, `__index_metadata` tables |
| Query | SQL with BLOB key lookups and optional JSON filtering |
| Scan | Cursor-based iteration with segment support |

This design provides:
- ✅ Efficient point lookups by primary key
- ✅ Efficient range queries on sort keys
- ✅ Support for GSI/LSI query patterns
- ✅ Preservation of DynamoDB data types
- ✅ Per-table isolation via separate files
- ✅ Extensibility for TTL, streams, transactions
