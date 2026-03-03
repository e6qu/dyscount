# Task: Go M2 Phase 1 - Critical Data Plane Operations

## Task ID
GO-M2-P1

## Description
Implement 8 critical data plane operations in Go to bring it closer to Python parity. These are the most commonly used operations for real-world DynamoDB applications.

## Current State

**Go Implementation**: 16/61 operations (26%)
- Control Plane: 5 ops (CreateTable, DeleteTable, ListTables, DescribeTable, Tag/Untag/List tags - stubs)
- Data Plane: 11 ops (GetItem, PutItem, UpdateItem, DeleteItem, Query, Scan, DescribeEndpoints)

## Target State

**Go Implementation**: 24/61 operations (39%)
- Add 8 critical data plane operations

## Operations to Implement (8)

### Priority 1: Batch Operations (2 ops) | 3 days
| Operation | Status | Description |
|-----------|--------|-------------|
| BatchGetItem | ❌ | Multi-table read, up to 100 items |
| BatchWriteItem | ❌ | Put/Delete operations, up to 25 items |

### Priority 2: Transactions (2 ops) | 3 days
| Operation | Status | Description |
|-----------|--------|-------------|
| TransactGetItems | ❌ | Atomic multi-item read |
| TransactWriteItems | ❌ | Atomic multi-item write (Put, Update, Delete, ConditionCheck) |

### Priority 3: Expressions (3 ops) | 4 days
| Operation | Status | Description |
|-----------|--------|-------------|
| ConditionExpression | ❌ | For PutItem, UpdateItem, DeleteItem |
| FilterExpression | ❌ | For Query, Scan |
| UpdateExpression | ⚠️ | Complete SET/REMOVE/ADD/DELETE support |

### Priority 4: Schema Evolution (1 op) | 2 days
| Operation | Status | Description |
|-----------|--------|-------------|
| UpdateTable | ❌ | Add GSI/LSI support |

## Implementation Plan

### Week 1: Batch Operations + Transactions

#### Day 1-2: BatchGetItem
**Files to modify:**
- `go/src/internal/models/item.go` - Add batch request/response types
- `go/src/internal/storage/item_manager.go` - Add BatchGetItem method
- `go/src/internal/handlers/dynamodb.go` - Add handler

**Request format:**
```json
{
  "RequestItems": {
    "TableName": {
      "Keys": [{"pk": {"S": "..."}}],
      "ProjectionExpression": "..."
    }
  }
}
```

**Response format:**
```json
{
  "Responses": {
    "TableName": [{"pk": {"S": "..."}, ...}]
  },
  "UnprocessedKeys": {...}
}
```

#### Day 3-4: BatchWriteItem
**Request format:**
```json
{
  "RequestItems": {
    "TableName": [
      {"PutRequest": {"Item": {...}}},
      {"DeleteRequest": {"Key": {...}}}
    ]
  }
}
```

**Handle:**
- Up to 25 items per request
- Partial failures (UnprocessedItems)
- Put and Delete in same batch

#### Day 5-6: TransactGetItems
**Request format:**
```json
{
  "TransactItems": [
    {"Get": {"TableName": "...", "Key": {...}}}
  ]
}
```

**Atomicity:** All-or-nothing read

#### Day 7: TransactWriteItems
**Request format:**
```json
{
  "TransactItems": [
    {"Put": {"TableName": "...", "Item": {...}}},
    {"Update": {"TableName": "...", "Key": {...}}},
    {"Delete": {"TableName": "...", "Key": {...}}},
    {"ConditionCheck": {"TableName": "...", "Key": {...}}}
  ]
}
```

### Week 2: Expressions + UpdateTable

#### Day 8-10: Expression Parser
**Options:**
1. Port Python's parser (recursive descent)
2. Use `github.com/alecthomas/participle`
3. Custom parser with shunting yard algorithm

**Grammar:**
```
expression := or_expression
or_expression := and_expression ("OR" and_expression)*
and_expression := condition ("AND" condition)*
condition := operand comparator operand
           | operand "BETWEEN" operand "AND" operand
           | operand "IN" "(" operand_list ")"
           | "(" expression ")"
           | "NOT" condition
           | function_call
operand := path | value
path := identifier ("." identifier | "[" number "]")*
```

#### Day 11-12: ConditionExpression
- Integrate with PutItem, UpdateItem, DeleteItem
- Return ConditionalCheckFailedException on failure

#### Day 13: FilterExpression
- Post-filtering for Query/Scan results
- Doesn't affect consumed capacity

#### Day 14: UpdateTable with GSI
- Add Global Secondary Index support
- Add Local Secondary Index support

## Files to Modify

### Models
- `go/src/internal/models/item.go` - Add batch/transaction types
- `go/src/internal/models/table.go` - Add GSI/LSI types
- `go/src/internal/models/expression.go` - New file for expression AST

### Storage
- `go/src/internal/storage/item_manager.go` - Add batch/transaction methods
- `go/src/internal/storage/table_manager.go` - Add UpdateTable, GSI support

### Handlers
- `go/src/internal/handlers/dynamodb.go` - Add 8 new handlers

### Parser (New)
- `go/src/internal/expression/parser.go` - Expression parser
- `go/src/internal/expression/evaluator.go` - Expression evaluator

## Test Plan

| Test File | Tests | Coverage |
|-----------|-------|----------|
| batch_operations_test.go | 10 | BatchGetItem, BatchWriteItem |
| transaction_test.go | 10 | TransactGetItems, TransactWriteItems |
| expression_test.go | 15 | Condition, Filter, Update expressions |
| update_table_test.go | 5 | UpdateTable, GSI |

## Acceptance Criteria

- [ ] All 8 operations implemented
- [ ] 40+ new tests passing
- [ ] Batch operations handle limits (100 read, 25 write)
- [ ] Transactions are atomic (all-or-nothing)
- [ ] Expression parser handles common cases
- [ ] UpdateTable can add GSI
- [ ] CI passes

## Definition of Done

- [ ] Code complete with tests
- [ ] All tests passing
- [ ] Documentation updated
- [ ] PR merged to main

## Estimated Effort

**2 weeks** (~10 days)

## Dependencies

- Go 1.21+
- SQLite3
- Gin framework (already in use)
- Expression parser library (TBD)

## Notes

- Use Python implementation as reference
- Focus on correctness over performance initially
- Consider using `participle` for expression parsing
- Test with real AWS SDK (boto3) for compatibility
