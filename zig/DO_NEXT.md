# Zig Implementation - Next Steps

## Current Status

**Phase 2 Complete**: UpdateItem, BatchGetItem (stub), BatchWriteItem (stub)

## Phase 3 - Batch Operations

### BatchGetItem
- [ ] Parse multi-table request format
- [ ] Handle up to 100 items per request
- [ ] Return UnprocessedKeys for failed items
- [ ] Response format: `{Responses: {table: [{...}]}}`

### BatchWriteItem
- [ ] Parse PutRequest/DeleteRequest operations
- [ ] Handle up to 25 items per request
- [ ] Return UnprocessedItems for failed operations
- [ ] Support mixed put/delete in single request

### UpdateItem Enhancements
- [ ] Parse SET/REMOVE/ADD/DELETE expressions
- [ ] Expression attribute names (#name substitution)
- [ ] Expression attribute values (:value substitution)
- [ ] ReturnValues support (ALL_OLD, ALL_NEW, etc.)

## Phase 4 - Advanced Features

### Transactions
- TransactGetItems
- TransactWriteItems

### Expressions
- ConditionExpression support
- FilterExpression for Query/Scan
- ProjectionExpression

### Pagination
- ExclusiveStartKey handling
- LastEvaluatedKey in responses

## Technical Debt

- [ ] Add proper argument parsing for port/data-dir
- [ ] Implement proper JSON parser (current is string-based)
- [ ] Add more comprehensive error handling
- [ ] Improve test coverage
