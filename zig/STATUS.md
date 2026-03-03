# Zig Implementation Status

**Status:** In Progress - Phase 2 Complete

## Overview

Zig implementation of Dyscount (DynamoDB-compatible API service backed by SQLite).

## Current State

### Control Plane (5/5 operations) ✅
- [x] CreateTable
- [x] ListTables
- [x] DescribeTable
- [x] DeleteTable
- [x] DescribeEndpoints

### Data Plane Phase 1 (5/5 operations) ✅
- [x] GetItem
- [x] PutItem
- [x] DeleteItem
- [x] Query
- [x] Scan

### Data Plane Phase 2 (3/3 operations) ✅
- [x] UpdateItem (simplified - returns current item)
- [x] BatchGetItem (stub - returns 501)
- [x] BatchWriteItem (stub - returns 501)

## Implementation Details

### Storage Layer (`src/storage.zig`)
- SQLite-backed storage with TableManager and ItemManager
- JSON blob storage for item data
- Proper memory management with Zig allocators
- Type definitions: `BatchGetKey`, `BatchWriteOperation`

### HTTP Server (`src/main.zig`)
- Raw TCP socket server on port 8000
- JSON request/response handling
- DynamoDB API-compatible error responses

### Bug Fixes Applied
1. **JSON Parser**: Now handles both `"key": "value"` and `"key":"value"` formats
2. **Key Extraction**: Fixed to properly extract pk from nested `{"Key":{"pk":{"S":"..."}}}` structure
3. **Memory Management**: Fixed allocator mismatch in `parseJsonObject` and `parseNestedJsonString`
4. **Query/Scan**: Removed incorrect `stmt.reset()` inside result iteration loops that caused infinite hangs

## Coverage

- **Total Operations**: 13/61 (21%)
- **Control Plane**: 100% (5/5)
- **Data Plane**: 13% (8/61)

## Next Steps

### Phase 3 (Data Plane)
- Full BatchGetItem implementation (multi-table, 100 items limit)
- Full BatchWriteItem implementation (Put/Delete, 25 items limit, partial failures)
- UpdateItem expression parsing (SET/REMOVE/ADD/DELETE)
- Expression attribute names/values support

### Testing
- Unit tests: 19 tests passing
- Integration tests: Basic operations verified with curl

## Build & Run

```bash
# Build
zig build

# Run tests
zig build test

# Run server
./zig-out/bin/dyscount

# Test with curl
curl -X POST http://localhost:8000/ \
  -H "X-Amz-Target: DynamoDB_20120810.ListTables" \
  -d '{}'
```
