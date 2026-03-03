# Go Implementation - Next Steps

## Current Status

Go implementation:
- **M1 (Foundation)**: ✅ Complete - 16 operations
- **M2 (Feature Parity)**: ✅ Complete - All phases finished
- **M3 (Advanced Features)**: 🚧 In Progress - TTL ✅, Backup/Restore ✅, Pagination ✅, Tagging ✅, PartiQL ✅, Import/Export ✅, Streams ✅

**Current Operations**: 43/61 (70%)
**Tests**: 172 passing

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
- **Phase 2**: Backup/Restore (CreateBackup, DescribeBackup, ListBackups, DeleteBackup, RestoreTableFromBackup) - 11 tests ✅
- **Phase 2.5**: Pagination (Query/Scan with LastEvaluatedKey) - 9 tests ✅
- **Phase 2.6**: Tagging (TagResource, UntagResource, ListTagsOfResource) - 8 tests ✅
- **Phase 2.7**: ListTables Pagination (Limit, ExclusiveStartTableName) - 5 tests ✅
- **Phase 2.8**: DescribeBackup - 2 tests ✅
- **Phase 3**: PartiQL (ExecuteStatement, BatchExecuteStatement) - 6 tests ✅
- **Phase 4**: Import/Export (ExportTableToPointInTime, DescribeExport, ListExports, ImportTable, DescribeImport, ListImports) - 6 tests ✅
- **Phase 5**: Streams (ListStreams, DescribeStream, GetShardIterator, GetRecords) - 10 tests ✅

## Next Phase: M3 Phase 5 - Point-in-Time Recovery (PITR) and Streams

### Goal
Implement PITR and DynamoDB Streams operations.

### Tasks

#### Phase 5: Point-in-Time Recovery
**Priority: High**

Implement:
1. **UpdateContinuousBackups** - Enable/disable PITR on a table
2. **DescribeContinuousBackups** - Get PITR configuration
3. **RestoreTableToPointInTime** - Restore table to specific timestamp

#### Phase 6: DynamoDB Streams
**Priority: Medium**

Implement:
1. **ListStreams** - List all streams
2. **DescribeStream** - Get stream details
3. **GetShardIterator** - Get iterator for reading records
4. **GetRecords** - Read records from stream

**Files to modify:**
- `go/src/internal/storage/table_manager.go` - add PITR and stream methods
- `go/src/internal/handlers/dynamodb.go` - add handlers
- `go/src/internal/models/operations.go` - add models

**Tests:**
- Test PITR enable/disable
- Test stream creation and reading

## Future Phases

### Global Tables
**Priority: Low**

- CreateGlobalTable, UpdateGlobalTable, DescribeGlobalTable, ListGlobalTables
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
