# M4 Phase 1: Import/Export Operations

## Task ID
M4P1

## Description
Implement DynamoDB Import/Export operations to enable data migration capabilities. This includes exporting table data to S3-compatible storage and importing data from S3-compatible sources.

## Acceptance Criteria
- [ ] ExportTableToPointInTime operation
- [ ] DescribeExport operation
- [ ] ListExports operation
- [ ] ImportTable operation
- [ ] DescribeImport operation
- [ ] ListImports operation
- [ ] Local filesystem as S3-compatible storage (`data/exports/`)
- [ ] DynamoDB JSON export format support
- [ ] Background async processing for import/export tasks
- [ ] Task status tracking and persistence
- [ ] Comprehensive test coverage

## Definition of Done
- [ ] All 6 operations implemented and tested
- [ ] Import/Export tasks can be created, monitored, and completed
- [ ] Data can be exported and re-imported correctly
- [ ] State files updated
- [ ] Task file moved to done/

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Import/Export System                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Export    │    │   Import    │    │  Task Store │     │
│  │  Service    │    │  Service    │    │  (SQLite)   │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                   │            │
│         ▼                  ▼                   ▼            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Local Storage (data/exports/)           │   │
│  │  - Export files: {export_id}/data.json               │   │
│  │  - Import files: {import_id}/manifest.json           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Background Tasks: asyncio.create_task() for processing   │
└─────────────────────────────────────────────────────────────┘
```

## Tasks

### M4P1-T1: Export Operations
**Estimated Effort**: 2 days

**Deliverables**:
- ExportTableToPointInTime API endpoint
- DescribeExport API endpoint
- ListExports API endpoint
- Export task status tracking
- DynamoDB JSON format export

**Storage Layout**:
```
data/exports/
  ├── {export_id}/
  │   ├── data.json          # Exported items in DynamoDB JSON format
  │   ├── manifest.json      # Export metadata
  │   └── metadata.db        # Export task status
```

### M4P1-T2: Import Operations
**Estimated Effort**: 2 days

**Deliverables**:
- ImportTable API endpoint
- DescribeImport API endpoint
- ListImports API endpoint
- Import task status tracking
- Table creation from import

**Storage Layout**:
```
data/imports/
  ├── {import_id}/
  │   ├── manifest.json      # Import metadata
  │   └── status.db          # Import task status
```

### M4P1-T3: Background Processing & Tests
**Estimated Effort**: 1.5 days

**Deliverables**:
- Async export processing
- Async import processing
- Task state machine (IN_PROGRESS → COMPLETED/FAILED)
- 15+ comprehensive tests

## Implementation Notes

### Export Format (DynamoDB JSON)
```json
{
  "Items": [
    {
      "pk": {"S": "user#123"},
      "sk": {"S": "profile"},
      "name": {"S": "John Doe"},
      "age": {"N": "30"}
    }
  ],
  "ExportMetadata": {
    "ExportArn": "arn:aws:dynamodb:::table/MyTable/export/1234567890",
    "TableArn": "arn:aws:dynamodb:::table/MyTable",
    "ExportTime": 1234567890,
    "ItemCount": 1000,
    "Format": "DYNAMODB_JSON"
  }
}
```

### Task State Machine

**Export Status**:
- `IN_PROGRESS` → `COMPLETED` | `FAILED` | `CANCELLED`

**Import Status**:
- `IN_PROGRESS` → `COMPLETED` | `FAILED` | `CANCELLED`

### API Operations Summary

| Operation | Method | X-Amz-Target |
|-----------|--------|--------------|
| ExportTableToPointInTime | POST | DynamoDB_20120810.ExportTableToPointInTime |
| DescribeExport | POST | DynamoDB_20120810.DescribeExport |
| ListExports | POST | DynamoDB_20120810.ListExports |
| ImportTable | POST | DynamoDB_20120810.ImportTable |
| DescribeImport | POST | DynamoDB_20120810.DescribeImport |
| ListImports | POST | DynamoDB_20120810.ListImports |

## Test Plan
- Test export creation and completion
- Test import from exported data
- Test list operations with pagination
- Test describe operations
- Test error handling (non-existent tasks, invalid formats)
- Test round-trip: export → import → verify data

## Status
🟡 **IN PROGRESS**

## Dependencies
- M1 Complete (all control and data plane operations)
- M2P3 PITR (for point-in-time export)

## Notes
- S3 is simulated using local filesystem
- Export/Import tasks run asynchronously in background
- Task state is persisted for recovery
- Export format is compatible with AWS DynamoDB export format
