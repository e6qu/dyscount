# Go Implementation - Next Steps

## Current Status

Go implementation has M1 (Foundation) complete with 16/61 operations.

**Missing Critical Features:**
- Condition expressions (ConditionExpression, FilterExpression)
- Batch operations (BatchGetItem, BatchWriteItem)
- Transactions (TransactGetItems, TransactWriteItems)
- UpdateExpression parser

## Next Phase: M2 Feature Parity

### Goal
Implement critical missing features to reach feature parity with Python's core data plane functionality.

### Tasks

#### Phase 1: Condition Expressions (Week 1)
**Priority: Critical**

Implement expression parser and evaluator for:
- Comparison operators (=, <>, <, <=, >, >=)
- BETWEEN, IN operators
- attribute_exists, begins_with functions
- AND, OR, NOT logical operators

**Files to modify:**
- `go/src/internal/expression/expression.go` - extend existing

**Tests:**
- Unit tests for all operators
- Integration tests with PutItem/UpdateItem/DeleteItem

#### Phase 2: Batch Operations (Week 1-2)
**Priority: High**

Implement:
1. **BatchGetItem** - Retrieve up to 100 items
2. **BatchWriteItem** - Put/Delete up to 25 items

**Files to modify:**
- `go/src/internal/storage/item_manager.go`
- `go/src/internal/handlers/dynamodb.go`

**Tests:**
- Test batch limits
- Test partial failures
- Test unprocessed items handling

#### Phase 3: Transactions (Week 2)
**Priority: High**

Implement:
1. **TransactGetItems** - Atomic multi-item read
2. **TransactWriteItems** - Atomic multi-item write

**Files to modify:**
- `go/src/internal/storage/item_manager.go`
- `go/src/internal/handlers/dynamodb.go`

**Tests:**
- Test transaction limits (100 items)
- Test all-or-nothing semantics
- Test conflict detection

#### Phase 4: UpdateExpression Parser (Week 3)
**Priority: Medium**

Extend UpdateItem with full UpdateExpression support:
- SET clause (including arithmetic, list_append, if_not_exists)
- REMOVE clause
- ADD clause
- DELETE clause (for sets)

**Files to modify:**
- `go/src/internal/expression/expression.go`

**Tests:**
- Test all UpdateExpression clauses
- Test complex expressions with multiple clauses

#### Phase 5: UpdateTable GSI (Week 3-4)
**Priority: Medium**

Implement:
- Create GSI via UpdateTable
- Delete GSI via UpdateTable
- Update GSI provisioned throughput

**Files to modify:**
- `go/src/internal/storage/table_manager.go`
- `go/src/internal/handlers/dynamodb.go`

**Tests:**
- Test GSI creation
- Test GSI deletion
- Test backfilling (if applicable)

## Testing Strategy

Each phase should include:
1. Unit tests for new functions
2. Handler integration tests
3. End-to-end tests with real requests

## Success Criteria

- All new operations have >80% test coverage
- Existing tests continue to pass
- Implementation matches Python behavior
- Performance within 20% of Python implementation

## Notes

- Follow existing Go code patterns
- Use existing SQLite storage layer
- Reference Python implementation for logic
- Update this file as work progresses
