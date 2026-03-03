# Zig Data Plane Implementation (DP1)

## Task ID
ZIG-DP1

## Description
Implement data plane operations for the Zig implementation to bring it to M1 (Foundation) completion. Currently Zig only has control plane (5 ops), needs 11 more for basic CRUD functionality.

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
| Tests | 40+ |

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

### Files to Modify

1. **src/storage.zig** - Add ItemManager
2. **src/main.zig** - Add HTTP handlers
3. **src/models.zig** - Add request/response types (if needed)

### ItemManager Structure

```zig
pub const ItemManager = struct {
    table_manager: *TableManager,
    
    pub fn getItem(...) !?Item {...}
    pub fn putItem(...) !void {...}
    pub fn updateItem(...) !Item {...}
    pub fn deleteItem(...) !?Item {...}
    pub fn query(...) ![]Item {...}
    pub fn scan(...) ![]Item {...}
};
```

### HTTP Handlers to Add

```zig
// In main.zig handleRequest
if (std.mem.eql(u8, operation, "GetItem")) {
    try self.handleGetItem(request, writer);
} else if (std.mem.eql(u8, operation, "PutItem")) {
    try self.handlePutItem(request, writer);
}
// ... etc
```

## Test Plan

### New Tests

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
- [ ] Items stored as JSON in SQLite
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

## Status
🟡 **IN PROGRESS**
