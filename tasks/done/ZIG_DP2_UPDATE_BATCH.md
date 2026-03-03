# Zig Data Plane Phase 2: UpdateItem & Batch Operations

## Task ID
ZIG-DP2

## Description
Continue implementing data plane operations for Zig. Add UpdateItem, BatchGetItem, and BatchWriteItem to bring Zig to 13/61 operations (21% coverage).

## Current State

| Metric | Value |
|--------|-------|
| Operations | 10/61 (16%) |
| Control Plane | 5 ops ✅ |
| Data Plane | 5 ops ✅ |
| Tests | 15 |

## Target State

| Metric | Value |
|--------|-------|
| Operations | 13/61 (21%) |
| Control Plane | 5 ops ✅ |
| Data Plane | 8 ops ✅ |
| Tests | 25+ |

## Operations to Add (3 ops)

### Phase 2: Update & Batch (3 ops)
**Priority**: High | **Effort**: 1 week

| Operation | Status | Notes |
|-----------|--------|-------|
| UpdateItem | ❌ | Partial updates with expressions |
| BatchGetItem | ❌ | Multi-item read (up to 100) |
| BatchWriteItem | ❌ | Multi-item write (up to 25) |

## Implementation Details

### UpdateItem

UpdateItem with SET/REMOVE/ADD/DELETE operations:

```zig
pub fn updateItem(
    self: ItemManager,
    table_name: []const u8,
    pk: []const u8,
    sk: ?[]const u8,
    update_expression: []const u8,
    expression_values: ?std.StringHashMap(AttributeValue),
) !Item {
    // Parse update expression
    // Apply updates to item
    // Store back to database
}
```

### BatchGetItem

Read multiple items from one or more tables:

```zig
pub fn batchGetItem(
    self: ItemManager,
    requests: []const BatchGetRequest,
) ![]BatchGetResult {
    // Process each request
    // Return items and unprocessed keys
}
```

### BatchWriteItem

Write multiple items (Put/Delete) to one or more tables:

```zig
pub fn batchWriteItem(
    self: ItemManager,
    requests: []const BatchWriteRequest,
) ![]BatchWriteResult {
    // Process each request (up to 25)
    // Return unprocessed items
}
```

## Test Plan

### New Tests

| Test | Description |
|------|-------------|
| test_update_item_set | SET attribute |
| test_update_item_remove | REMOVE attribute |
| test_update_item_add | ADD to number |
| test_batch_get_item | Multiple items |
| test_batch_get_item_multi_table | Cross-table |
| test_batch_write_item_put | Batch put |
| test_batch_write_item_delete | Batch delete |
| test_batch_write_item_mixed | Put + Delete |

## Acceptance Criteria

- [ ] UpdateItem implemented and tested
- [ ] BatchGetItem implemented and tested
- [ ] BatchWriteItem implemented and tested
- [ ] 10+ new tests passing
- [ ] All existing tests still pass
- [ ] Build succeeds

## Definition of Done

- [ ] 3 operations implemented
- [ ] HTTP handlers working
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Task file moved to done/

## Estimated Effort

| Operation | Effort |
|-----------|--------|
| UpdateItem | 3 days |
| BatchGetItem | 2 days |
| BatchWriteItem | 2 days |
| **Total** | **~1 week** |

## Status
🟡 **IN PROGRESS**
