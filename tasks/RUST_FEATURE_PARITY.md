# Task: Rust Feature Parity with Go M2 Phase 1

## Task ID
RUST-PARITY-1

## Description
Bring Rust implementation to feature parity with Go's M2 Phase 1 (22 operations).
Currently Rust has 13 operations, need to add 9 more.

## Current State

**Rust Implementation**: 13/61 operations (21%)
- Control Plane: 6 ops (CreateTable, DeleteTable, ListTables, DescribeTable, Tag/Untag/List)
- Data Plane: 7 ops (GetItem, PutItem, UpdateItem, DeleteItem, Query, Scan, DescribeEndpoints)

**Go Target**: 22/61 operations (36%)

## Target State

**Rust Implementation**: 22/61 operations (36%)
- Add 9 operations to match Go

## Operations to Add (9)

### Priority 1: Batch Operations (2 ops) | 2-3 days
| Operation | Rust | Notes |
|-----------|------|-------|
| BatchGetItem | ❌ | Multi-table read, up to 100 items |
| BatchWriteItem | ❌ | Put/Delete, up to 25 items |

### Priority 2: Transactions (2 ops) | 2-3 days
| Operation | Rust | Notes |
|-----------|------|-------|
| TransactGetItems | ❌ | Atomic multi-item read |
| TransactWriteItems | ❌ | Atomic multi-item write |

### Priority 3: Expressions (2 ops) | 3-4 days
| Operation | Rust | Notes |
|-----------|------|-------|
| ConditionExpression | ❌ | For Put/Update/Delete |
| FilterExpression | ❌ | For Query/Scan |

### Priority 4: Schema Evolution (1 op) | 2 days
| Operation | Rust | Notes |
|-----------|------|-------|
| UpdateTable | ❌ | GSI support |

### Priority 5: UpdateExpression Completion | 1-2 days
| Operation | Rust | Notes |
|-----------|------|-------|
| UpdateExpression | ⚠️ | ADD/DELETE/REMOVE (currently only SET) |

## Implementation Plan

### Week 1: Batch + Transactions

#### Batch Operations (src/items.rs)
```rust
pub async fn batch_get_item(
    &self,
    requests: HashMap<String, KeysAndAttributes>,
) -> Result<BatchGetItemResponse, StorageError>

pub async fn batch_write_item(
    &self,
    requests: HashMap<String, Vec<WriteRequest>>,
) -> Result<BatchWriteItemResponse, StorageError>
```

#### Transaction Operations (src/items.rs)
```rust
pub async fn transact_get_items(
    &self,
    items: Vec<TransactGetItem>,
) -> Result<Vec<ItemResponse>, StorageError>

pub async fn transact_write_items(
    &self,
    items: Vec<TransactWriteItem>,
) -> Result<(), StorageError>
```

### Week 2: Expressions + UpdateTable

#### Expression Parser (new: src/expression.rs)
- Port Go's expression parser to Rust
- Use nom or custom parser
- Support: =, <>, <, <=, >, >=, BETWEEN, IN, attribute_exists

#### UpdateTable with GSI (src/storage.rs)
```rust
pub async fn update_table(
    &self,
    request: UpdateTableRequest,
) -> Result<TableMetadata, StorageError>
```

## Files to Modify

### Models (src/models.rs)
- Add batch request/response types
- Add transaction types
- Add UpdateTable request/response types
- Add expression-related types

### Storage (src/storage.rs)
- Add UpdateTable method
- Add GSI management

### Items (src/items.rs)
- Add batch operation methods
- Add transaction methods
- Extend UpdateExpression parser

### Handlers (src/handlers.rs)
- Add 9 new handlers
- Add routes for new operations

### Expression Parser (new: src/expression.rs)
- ConditionExpression evaluator
- FilterExpression evaluator

## Test Plan

| Test File | Tests | Coverage |
|-----------|-------|----------|
| batch_tests.rs | 10 | BatchGetItem, BatchWriteItem |
| transaction_tests.rs | 10 | TransactGetItems, TransactWriteItems |
| expression_tests.rs | 15 | Condition, Filter expressions |
| update_table_tests.rs | 5 | UpdateTable, GSI |
| update_expression_tests.rs | 10 | ADD, DELETE, REMOVE |

## Acceptance Criteria

- [ ] All 9 operations implemented
- [ ] 50+ new tests passing
- [ ] Expression parser supports common cases
- [ ] Batch operations handle limits (100 read, 25 write)
- [ ] Transactions are atomic
- [ ] UpdateTable can add GSI
- [ ] UpdateExpression supports all actions
- [ ] CI passes

## Definition of Done

- [ ] Rust matches Go's 22 operations
- [ ] All tests passing
- [ ] Documentation updated
- [ ] PR merged to main

## Estimated Effort

**2-3 weeks**

## Dependencies

- Rust 1.70+
- tokio (already in use)
- axum (already in use)
- sqlite (already in use)
- nom or custom parser for expressions
