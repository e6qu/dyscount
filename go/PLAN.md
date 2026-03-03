# Go Implementation Plan

## Overview

Go implementation of Dyscount using:
- **HTTP Framework**: Gin
- **Storage**: SQLite with mattn/go-sqlite3
- **Architecture**: Clean architecture with handlers, services, storage layers

## Milestones

### M1: Foundation ✅ COMPLETE
- [x] Project setup
- [x] Control plane operations (CreateTable, DeleteTable, ListTables, DescribeTable)
- [x] Basic data plane (GetItem, PutItem, UpdateItem, DeleteItem, Query, Scan)
- [x] SQLite storage backend
- [x] Basic expression parser

### M2: Advanced Data Plane 🚧 IN PROGRESS

#### Phase 1: Condition Expressions (Current)
**Goal**: Full condition expression support

Operations:
- [ ] Comparison operators (=, <>, <, <=, >, >=)
- [ ] BETWEEN, IN operators
- [ ] attribute_exists, begins_with functions
- [ ] AND, OR, NOT logical operators
- [ ] Expression attribute names/values

**Deliverables**:
- ConditionExpression for PutItem/UpdateItem/DeleteItem
- FilterExpression for Query/Scan
- KeyConditionExpression improvements

#### Phase 2: Batch Operations
**Goal**: Efficient bulk operations

Operations:
- [ ] BatchGetItem (up to 100 items)
- [ ] BatchWriteItem (up to 25 items)

**Deliverables**:
- Batch request/response handling
- Unprocessed items support
- Partial failure handling

#### Phase 3: Transactions
**Goal**: ACID transactions

Operations:
- [ ] TransactGetItems (up to 100 items)
- [ ] TransactWriteItems (up to 100 items)

**Deliverables**:
- Atomic multi-item operations
- Transaction conflict detection
- All-or-nothing semantics

#### Phase 4: UpdateExpression
**Goal**: Full UpdateExpression support

Operations:
- [ ] SET with arithmetic
- [ ] SET with list_append
- [ ] SET with if_not_exists
- [ ] REMOVE clause
- [ ] ADD clause
- [ ] DELETE clause

**Deliverables**:
- Complete UpdateExpression parser
- All UpdateItem functionality

#### Phase 5: UpdateTable GSI
**Goal**: Dynamic GSI management

Operations:
- [ ] Create GSI via UpdateTable
- [ ] Delete GSI via UpdateTable
- [ ] Update GSI throughput

**Deliverables**:
- GSI update operations
- Backfilling support

### M3: Advanced Features (Future)
- TTL support
- Backup/Restore
- PITR (Point-in-Time Recovery)
- PartiQL support
- Import/Export

### M4: Polish (Future)
- Performance optimization
- Security audit
- Complete documentation
- Docker distribution

## Implementation Notes

### Code Organization
```
go/src/
├── main.go                 # Entry point
├── internal/
│   ├── config/            # Configuration
│   ├── handlers/          # HTTP handlers
│   ├── models/            # Data models
│   ├── storage/           # SQLite storage
│   └── expression/        # Expression parser
```

### Testing Strategy
- Unit tests for each layer
- Handler integration tests
- End-to-end tests with real requests

### Dependencies
- github.com/gin-gonic/gin
- github.com/mattn/go-sqlite3
- Standard library for JSON, testing, etc.

## Success Criteria

Each phase must:
1. Pass all new unit tests (>80% coverage)
2. Pass existing tests (no regressions)
3. Match Python implementation behavior
4. Have proper error handling

## See Also

- [STATUS.md](STATUS.md) - Current status
- [DO_NEXT.md](DO_NEXT.md) - Immediate next steps
- [tasks/GO_M2_PARITY.md](../tasks/GO_M2_PARITY.md) - Detailed task breakdown
