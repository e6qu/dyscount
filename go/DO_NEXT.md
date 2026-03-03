# Go Implementation - Next Steps

## Current Status

Go implementation:
- **M1 (Foundation)**: ✅ Complete - 16 operations
- **M2 (Feature Parity)**: ✅ Complete - All phases finished
- **M3 (Advanced Features)**: 🚧 In Progress - TTL ✅, Backup/Restore ✅, Pagination ✅, Tagging ✅

**Current Operations**: 29/61 (48%)
**Tests**: 143 passing

## Completed Work

### M1 Foundation ✅
- Control Plane: CreateTable, DeleteTable, ListTables, DescribeTable, DescribeEndpoints
- Data Plane: GetItem, PutItem, UpdateItem, DeleteItem, Query, Scan
- GSI/LSI support

### M2 Feature Parity ✅
- **Phase 1**: Condition Expressions (AND, OR, NOT, begins_with, contains) - 28 tests
- **Phase 2**: Batch Operations (BatchGetItem, BatchWriteItem) - 10 tests
- **Phase 3**: Transactions (TransactGetItems, TransactWriteItems) - 10 tests
- **Phase 4**: UpdateExpression (SET, ADD, REMOVE, DELETE) - 8 tests
- **Phase 5**: UpdateTable GSI (Create/Update/Delete GSI) - 8 tests

### M3 Advanced Features 🚧
- **Phase 1**: TTL (UpdateTimeToLive, DescribeTimeToLive) - 6 tests ✅
- **Phase 2**: Backup/Restore (CreateBackup, DescribeBackup, ListBackups, DeleteBackup, RestoreTableFromBackup) - 9 tests ✅
- **Phase 2.5**: Pagination (Query/Scan with LastEvaluatedKey) - 9 tests ✅
- **Phase 2.6**: Tagging (TagResource, UntagResource, ListTagsOfResource) - 8 tests ✅

## Next Phase: M3 Phase 3 - Point-in-Time Recovery (PITR)

### Goal
Implement continuous backups and point-in-time recovery operations.

### Tasks

#### Phase 3: Point-in-Time Recovery
**Priority: High**

Implement:
1. **UpdateContinuousBackups** - Enable/disable PITR on a table
2. **DescribeContinuousBackups** - Get PITR configuration
3. **RestoreTableToPointInTime** - Restore table to specific timestamp

**Files to modify:**
- `go/src/internal/storage/table_manager.go` - add PITR methods
- `go/src/internal/handlers/dynamodb.go` - add PITR handlers

**Tests:**
- Test enabling PITR
- Test disabling PITR
- Test restoring to specific timestamp
- Test error cases

## Future M3 Phases

### M3 Phase 4: PartiQL Support
**Priority: Medium**

Implement:
- ExecuteStatement
- BatchExecuteStatement

### M3 Phase 5: Import/Export
**Priority: Low**

Implement:
- ExportTableToPointInTime
- ImportTable
- ListImports
- DescribeImport
- etc.

### M3 Phase 6: DynamoDB Streams
**Priority: Low**

Implement:
- ListStreams
- DescribeStream
- GetShardIterator
- GetRecords

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
