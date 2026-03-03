# Task: Zig Data Plane Implementation

## Task ID
ZIG-DP-1

## Description
Implement the data plane operations for the Zig implementation to bring it to M1 completion (Foundation). Currently Zig only has control plane (5 ops), needs 11 more for basic CRUD functionality.

## Current State

| Metric | Value |
|--------|-------|
| Operations | 5/61 (8%) |
| Control Plane | 5 ops ✅ |
| Data Plane | 0 ops ❌ |
| Tests | 9 |

## Target State

| Metric | Value |
|--------|-------|
| Operations | 16/61 (26%) |
| Control Plane | 5 ops ✅ |
| Data Plane | 11 ops ✅ |
| Tests | 50+ |

## Operations to Add (11 ops)

### Phase 1: Core Item Operations (4 ops)
**Priority**: Critical | **Effort**: 1 week

| Operation | Status | Notes |
|-----------|--------|-------|
| GetItem | ❌ | Primary key retrieval |
| PutItem | ❌ | Create/replace items |
| UpdateItem | ❌ | Partial updates |
| DeleteItem | ❌ | Delete by key |

### Phase 2: Query Operations (2 ops)
**Priority**: High | **Effort**: 1 week

| Operation | Status | Notes |
|-----------|--------|-------|
| Query | ❌ | Partition key queries |
| Scan | ❌ | Full table scan |

### Phase 3: Batch Operations (2 ops)
**Priority**: Medium | **Effort**: 1 week

| Operation | Status | Notes |
|-----------|--------|-------|
| BatchGetItem | ❌ | Multi-item read |
| BatchWriteItem | ❌ | Multi-item write |

### Phase 4: Transactions (2 ops)
**Priority**: Medium | **Effort**: 1 week

| Operation | Status | Notes |
|-----------|--------|-------|
| TransactGetItems | ❌ | Atomic reads |
| TransactWriteItems | ❌ | Atomic writes |

### Phase 5: Expressions (1 capability)
**Priority**: High | **Effort**: 2 weeks

| Feature | Status | Notes |
|---------|--------|-------|
| ConditionExpression | ❌ | Conditional operations |
| FilterExpression | ❌ | Query/Scan filtering |
| KeyConditionExpression | ❌ | Query key conditions |
| UpdateExpression | ❌ | Update operations |

## Implementation Details

### SQLite Schema

Current Zig storage only tracks table metadata. Need to add:

```zig
// Item table schema
const ITEMS_SCHEMA = 
    CREATE TABLE IF NOT EXISTS items (
        pk BLOB NOT NULL,        // Partition key
        sk BLOB,                 // Sort key (optional)
        item_data BLOB NOT NULL, // MessagePack encoded item
        created_at INTEGER,      // Unix timestamp
        updated_at INTEGER,      // Unix timestamp
        PRIMARY KEY (pk, sk)
    );
    CREATE INDEX IF NOT EXISTS idx_sk ON items(sk) WHERE sk IS NOT NULL;
```

### Key Components

#### 1. Item Manager (`src/items.zig`)
New file to handle item operations:

```zig
pub const ItemManager = struct {
    allocator: std.mem.Allocator,
    db: sqlite3.db,
    
    pub fn getItem(...) !?Item {...}
    pub fn putItem(...) !void {...}
    pub fn updateItem(...) !Item {...}
    pub fn deleteItem(...) !?Item {...}
    pub fn query(...) ![]Item {...}
    pub fn scan(...) ![]Item {...}
};
```

#### 2. Expression Parser
Simplified expression parser for Zig:

```zig
pub const ExpressionParser = struct {
    pub fn parseConditionExpression(expr: []const u8) !Condition {...}
    pub fn parseUpdateExpression(expr: []const u8) !UpdateOps {...}
    pub fn parseKeyConditionExpression(expr: []const u8) !KeyCondition {...}
};
```

#### 3. Update Handlers (`src/main.zig`)
Add to HTTP router:

```zig
if (std.mem.eql(u8, operation, "GetItem")) {
    try self.handleGetItem(request, writer);
} else if (std.mem.eql(u8, operation, "PutItem")) {
    try self.handlePutItem(request, writer);
}
// ... etc
```

### MessagePack Support

Zig needs MessagePack serialization for item storage:
- Library: `zig-msgpack` or implement simple encoder/decoder
- Store items as MessagePack blobs in SQLite

## Test Plan

### New Test File: `src/items_test.zig`

| Test | Description |
|------|-------------|
| test_get_item | Retrieve item by key |
| test_get_item_not_found | Handle missing item |
| test_put_item | Create new item |
| test_put_item_replace | Replace existing |
| test_update_item | Partial update |
| test_delete_item | Delete by key |
| test_query | Query by partition key |
| test_scan | Scan all items |
| test_batch_get | Multiple items |
| test_batch_write | Put/Delete batch |

## Acceptance Criteria

- [ ] GetItem implemented and tested
- [ ] PutItem implemented and tested
- [ ] UpdateItem implemented and tested
- [ ] DeleteItem implemented and tested
- [ ] Query implemented and tested
- [ ] Scan implemented and tested
- [ ] BatchGetItem implemented and tested
- [ ] BatchWriteItem implemented and tested
- [ ] TransactGetItems implemented and tested
- [ ] TransactWriteItems implemented and tested
- [ ] Basic expression parsing working
- [ ] 40+ tests passing
- [ ] All existing tests still pass

## Definition of Done

- [ ] 11 data plane operations implemented
- [ ] 40+ tests passing
- [ ] Items stored as MessagePack in SQLite
- [ ] Basic expressions working
- [ ] CI passes
- [ ] Documentation updated
- [ ] Task file moved to done/

## Estimated Effort

| Phase | Effort |
|-------|--------|
| Phase 1: Core Item Operations | 1 week |
| Phase 2: Query Operations | 1 week |
| Phase 3: Batch Operations | 1 week |
| Phase 4: Transactions | 1 week |
| Phase 5: Expressions | 2 weeks |
| **Total** | **~6 weeks** |

## Notes

- Keep it simple - Zig is meant to be minimal
- MessagePack library choice is critical
- Expression parser can be simplified vs Python
- SQLite is the reference storage implementation
- Test against Python's behavior for consistency
