# Task: Go M2 Feature Parity

## Goal

Implement critical missing features in Go to reach feature parity with Python's core data plane functionality.

## Background

Go implementation currently has 16/61 operations (26%). The most critical gaps are:
1. **No condition expressions** - Cannot do conditional updates
2. **No batch operations** - Cannot efficiently read/write multiple items
3. **No transactions** - No ACID support
4. **Limited UpdateExpression** - Basic SET support only

## Scope

### In Scope
- ConditionExpression parser/evaluator
- BatchGetItem and BatchWriteItem
- TransactGetItems and TransactWriteItems
- UpdateExpression improvements (SET, REMOVE, ADD, DELETE)
- UpdateTable GSI operations

### Out of Scope
- Advanced features (TTL, Backup, PITR, PartiQL, Import/Export)
- Streams
- Global Tables

## Implementation Plan

### Phase 1: Condition Expressions (Priority: Critical)

**Estimated Effort**: 3-4 days

Implement expression parser supporting:

```go
// Supported operators
=, <>, <, <=, >, >=           // Comparison
BETWEEN                        // Range check
IN                             // Set membership
attribute_exists(path)         // Check attribute exists
attribute_not_exists(path)     // Check attribute doesn't exist
begins_with(path, substr)      // String prefix check
contains(path, operand)        // String/set contains
size(path)                     // Get size of attribute

// Logical operators
AND, OR, NOT
```

**Files**:
- `go/src/internal/expression/expression.go` - Extend existing parser
- `go/src/internal/expression/expression_test.go` - Add tests

**Acceptance Criteria**:
- [ ] All comparison operators work
- [ ] BETWEEN and IN operators work
- [ ] attribute_exists, begins_with functions work
- [ ] AND, OR, NOT logical operators work
- [ ] Expression attribute names (#name) supported
- [ ] Expression attribute values (:value) supported
- [ ] Unit tests for all operators (>90% coverage)

### Phase 2: Batch Operations (Priority: High)

**Estimated Effort**: 2-3 days

#### BatchGetItem

```go
// Request
type BatchGetItemRequest struct {
    RequestItems map[string]KeysAndAttributes
}

type KeysAndAttributes struct {
    Keys           []map[string]AttributeValue
    ConsistentRead bool
}

// Response
type BatchGetItemResponse struct {
    Responses       map[string][]map[string]AttributeValue
    UnprocessedKeys map[string]KeysAndAttributes
}
```

#### BatchWriteItem

```go
// Request
type BatchWriteItemRequest struct {
    RequestItems map[string][]WriteRequest
}

type WriteRequest struct {
    PutRequest    *PutRequest
    DeleteRequest *DeleteRequest
}

// Response
type BatchWriteItemResponse struct {
    UnprocessedItems map[string][]WriteRequest
}
```

**Files**:
- `go/src/internal/storage/item_manager.go` - Add batch methods
- `go/src/internal/handlers/dynamodb.go` - Add handlers

**Acceptance Criteria**:
- [ ] BatchGetItem retrieves up to 100 items
- [ ] BatchWriteItem handles up to 25 items
- [ ] Unprocessed items returned correctly
- [ ] Partial failures handled
- [ ] Integration tests pass

### Phase 3: Transactions (Priority: High)

**Estimated Effort**: 2-3 days

#### TransactGetItems

```go
type TransactGetItemsRequest struct {
    TransactItems []TransactGetItem
}

type TransactGetItem struct {
    Get GetItemRequest
}
```

#### TransactWriteItems

```go
type TransactWriteItemsRequest struct {
    TransactItems []TransactWriteItem
}

type TransactWriteItem struct {
    ConditionCheck *ConditionCheck
    Put            *PutItemRequest
    Delete         *DeleteItemRequest
    Update         *UpdateItemRequest
}
```

**Files**:
- `go/src/internal/storage/item_manager.go` - Add transaction support
- `go/src/internal/handlers/dynamodb.go` - Add handlers

**Acceptance Criteria**:
- [ ] Up to 100 items per transaction
- [ ] All-or-nothing semantics
- [ ] Transaction conflicts detected
- [ ] Proper error responses

### Phase 4: UpdateExpression (Priority: Medium)

**Estimated Effort**: 3-4 days

Extend UpdateItem to support:

```go
// SET clause
SET attr = value
SET attr = attr + value           // Arithmetic ADD
SET attr = attr - value           // Arithmetic SUB
SET attr = list_append(list, value)  // Append to list
SET attr = if_not_exists(attr, value) // Set if not exists

// REMOVE clause
REMOVE attr

// ADD clause (for numbers and sets)
ADD attr value

// DELETE clause (for sets)
DELETE attr value
```

**Files**:
- `go/src/internal/expression/expression.go` - Add UpdateExpression parser

**Acceptance Criteria**:
- [ ] SET with arithmetic works
- [ ] SET with list_append works
- [ ] SET with if_not_exists works
- [ ] REMOVE works
- [ ] ADD works for numbers and sets
- [ ] DELETE works for sets

### Phase 5: UpdateTable GSI (Priority: Medium)

**Estimated Effort**: 2-3 days

Implement GSI updates:

```go
type UpdateTableRequest struct {
    TableName                  string
    GlobalSecondaryIndexUpdates []GlobalSecondaryIndexUpdate
}

type GlobalSecondaryIndexUpdate struct {
    Create *CreateGlobalSecondaryIndexAction
    Delete *DeleteGlobalSecondaryIndexAction
    Update *UpdateGlobalSecondaryIndexAction
}
```

**Files**:
- `go/src/internal/storage/table_manager.go` - Add GSI update methods
- `go/src/internal/handlers/dynamodb.go` - Add handler

**Acceptance Criteria**:
- [ ] Create GSI via UpdateTable
- [ ] Delete GSI via UpdateTable
- [ ] Update GSI throughput
- [ ] Backfilling handled

## Testing Strategy

### Unit Tests
Each new function should have unit tests with >80% coverage.

### Integration Tests
Test the full flow: handler → storage → SQLite → response.

### E2E Tests
Test with real HTTP requests to ensure API compatibility.

## Dependencies

- Phase 1 must be complete before Phases 2-5 (condition expressions needed)
- Phases 2 and 3 can be done in parallel
- Phase 4 can be done in parallel with Phases 2-3
- Phase 5 should be done last

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| Operations | 16/61 (26%) | 26/61 (43%) |
| Tests | 50 | 100+ |
| Test Coverage | ~60% | >75% |

## References

- Python implementation: `python/packages/dyscount-core/`
- Go implementation: `go/src/internal/`
- DynamoDB API docs: `specs/API_OPERATIONS.md`
