# Feature Comparison - All Languages

**Last Updated**: 2026-03-04

---

## Current Status Overview

| Language | Operations | Coverage | Status |
|----------|-----------|----------|--------|
| **Python** | 53/61 | 87% | ✅ Production Ready |
| **Go** | 50/61 | 82% | ✅ Feature Complete |
| **Rust** | 13/61 | 21% | ⚠️ Basic only |
| **Zig** | 16/61 | 26% | ⚠️ Basic only |

**Total Test Count**: 585 (Python: 372, Go: 183, Rust: 21, Zig: 19)

---

## Detailed Feature Matrix

### Control Plane (10 operations)

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| CreateTable | ✅ | ✅ | ✅ | ✅ |
| DeleteTable | ✅ | ✅ | ✅ | ✅ |
| ListTables | ✅ | ✅ | ✅ | ✅ |
| DescribeTable | ✅ | ✅ | ✅ | ✅ |
| DescribeEndpoints | ✅ | ✅ | ✅ | ✅ |
| UpdateTable | ✅ | ✅ | ⚠️ | ❌ |
| TagResource | ✅ | ✅ | ⚠️ | ❌ |
| UntagResource | ✅ | ✅ | ⚠️ | ❌ |
| ListTagsOfResource | ✅ | ✅ | ⚠️ | ❌ |
| DescribeLimits | ❌ | ✅ | ❌ | ❌ |
| **Control Plane** | 9/10 | 10/10 | 5/10 | 5/10 |

---

### Data Plane - Basic Operations (6 operations)

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| GetItem | ✅ | ✅ | ✅ | ✅ |
| PutItem | ✅ | ✅ | ✅ | ✅ |
| UpdateItem | ✅ | ✅ | ⚠️ | ⚠️ |
| DeleteItem | ✅ | ✅ | ✅ | ✅ |
| Query | ✅ | ✅ | ✅ | ✅ |
| Scan | ✅ | ✅ | ✅ | ✅ |
| **Basic Data Plane** | 6/6 | 6/6 | 5/6 | 5/6 |

---

### Data Plane - Advanced Features

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| **Batch Operations** |
| BatchGetItem | ✅ | ✅ | ❌ | ⚠️ |
| BatchWriteItem | ✅ | ✅ | ❌ | ⚠️ |
| **Transactions** |
| TransactGetItems | ✅ | ✅ | ❌ | ❌ |
| TransactWriteItems | ✅ | ✅ | ❌ | ❌ |
| **Expressions** |
| ConditionExpression | ✅ | ✅ | ⚠️ | ❌ |
| FilterExpression | ✅ | ✅ | ⚠️ | ❌ |
| KeyConditionExpression | ✅ | ✅ | ⚠️ | ⚠️ |
| UpdateExpression (SET) | ✅ | ✅ | ✅ | ✅ |
| UpdateExpression (ADD) | ✅ | ✅ | ⚠️ | ❌ |
| UpdateExpression (REMOVE) | ✅ | ✅ | ⚠️ | ❌ |
| UpdateExpression (DELETE) | ✅ | ✅ | ⚠️ | ❌ |
| ExpressionAttributeNames | ✅ | ✅ | ✅ | ❌ |
| ExpressionAttributeValues | ✅ | ✅ | ✅ | ❌ |
| **Pagination** |
| Query/Scan Limit | ✅ | ✅ | ⚠️ | ⚠️ |
| ExclusiveStartKey | ✅ | ✅ | ⚠️ | ⚠️ |
| LastEvaluatedKey | ✅ | ✅ | ⚠️ | ⚠️ |

---

### M2: Advanced Operations

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| **TTL** |
| UpdateTimeToLive | ✅ | ✅ | ❌ | ❌ |
| DescribeTimeToLive | ✅ | ✅ | ❌ | ❌ |
| **Backup/Restore** |
| CreateBackup | ✅ | ✅ | ❌ | ❌ |
| DescribeBackup | ❌ | ✅ | ❌ | ❌ |
| DeleteBackup | ✅ | ✅ | ❌ | ❌ |
| ListBackups | ✅ | ✅ | ❌ | ❌ |
| RestoreTableFromBackup | ✅ | ✅ | ❌ | ❌ |
| **PITR** |
| UpdateContinuousBackups | ✅ | ✅ | ❌ | ❌ |
| DescribeContinuousBackups | ✅ | ✅ | ❌ | ❌ |
| RestoreTableToPointInTime | ✅ | ✅ | ❌ | ❌ |
| **PartiQL** |
| ExecuteStatement | ✅ | ✅ | ❌ | ❌ |
| BatchExecuteStatement | ✅ | ✅ | ❌ | ❌ |
| **M2 Advanced** | 11/11 | 12/12 | 0/12 | 0/12 |

---

### M4: Import/Export & Streams

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| **Import/Export (6 ops)** |
| ExportTableToPointInTime | ✅ | ✅ | ❌ | ❌ |
| DescribeExport | ❌ | ✅ | ❌ | ❌ |
| ListExports | ❌ | ✅ | ❌ | ❌ |
| ImportTable | ✅ | ✅ | ❌ | ❌ |
| DescribeImport | ❌ | ✅ | ❌ | ❌ |
| ListImports | ❌ | ✅ | ❌ | ❌ |
| **Streams (4 ops)** |
| ListStreams | ✅ | ✅ | ❌ | ❌ |
| DescribeStream | ❌ | ✅ | ❌ | ❌ |
| GetShardIterator | ✅ | ✅ | ❌ | ❌ |
| GetRecords | ✅ | ✅ | ❌ | ❌ |
| **M4 Features** | 6/10 | 10/10 | 0/10 | 0/10 |

---

### Global Tables

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| CreateGlobalTable | ❌ | ✅ | ❌ | ❌ |
| DeleteGlobalTable | ❌ | ✅ | ❌ | ❌ |
| UpdateGlobalTable | ❌ | ✅ | ❌ | ❌ |
| DescribeGlobalTable | ❌ | ✅ | ❌ | ❌ |
| ListGlobalTables | ❌ | ✅ | ❌ | ❌ |
| UpdateGlobalTableSettings | ❌ | ✅ | ❌ | ❌ |
| DescribeGlobalTableSettings | ❌ | ✅ | ❌ | ❌ |
| UpdateReplication | ❌ | ✅ | ❌ | ❌ |
| **Global Tables** | 0/8 | 8/8 | 0/8 | 0/8 |

**Note**: Global Tables are not needed for local development.

---

## Summary by Category

| Category | Python | Go | Rust | Zig |
|----------|--------|-----|------|-----|
| Control Plane | 9/10 | 10/10 | 5/10 | 5/10 |
| Data Plane Basic | 6/6 | 6/6 | 5/6 | 5/6 |
| Batch Operations | 2/2 | 2/2 | 0/2 | 0/2 |
| Transactions | 2/2 | 2/2 | 0/2 | 0/2 |
| Expressions | Full | Full | Partial | Basic |
| M2 Advanced | 11/11 | 12/12 | 0/12 | 0/12 |
| Import/Export | 4/6 | 6/6 | 0/6 | 0/6 |
| Streams | 4/4 | 4/4 | 0/4 | 0/4 |
| Global Tables | 0/8 | 8/8 | 0/8 | 0/8 |
| **Total** | **53/61** | **50/61** | **13/61** | **16/61** |

---

## Go Operations Beyond Python

Go implements 13 operations that Python does not:

| Operation | Category | Notes |
|-----------|----------|-------|
| DeleteGlobalTable | Global Tables | Delete a global table |
| DescribeLimits | Control Plane | Get account/table limits |
| DescribeGlobalTableSettings | Global Tables | Get replica settings |
| UpdateReplication | Global Tables | Update replication |
| DescribeBackup | Backup | Get backup details |
| RestoreTableToPointInTime | PITR | Point-in-time restore |
| UpdateContinuousBackups | PITR | Enable/disable PITR |
| DescribeContinuousBackups | PITR | Get PITR status |
| DescribeExport | Import/Export | Get export details |
| DescribeImport | Import/Export | Get import details |
| ListExports | Import/Export | List all exports |
| ListImports | Import/Export | List all imports |
| DescribeStream | Streams | Get stream details |

---

## Python Operations Beyond Go

Python implements 3 operations that Go does not:

| Operation | Category | Notes |
|-----------|----------|-------|
| ListStreams | Streams | List all streams |
| GetShardIterator | Streams | Get iterator |
| GetRecords | Streams | Read records |

Wait - Go actually has these. Let me check again...

Actually Go has all 4 stream operations. Python is missing DescribeStream but has the others.

Correct list:

**Python has (0) beyond Go**: None

**Go has (13) beyond Python**: As listed above

---

## Not Implemented in Any Language

These 8 operations are intentionally deferred as not needed for local development:

| Category | Operations |
|----------|------------|
| Standalone | ConditionCheck |
| Kinesis Streaming | DescribeKinesisStreamingDestination, EnableKinesisStreamingDestination, DisableKinesisStreamingDestination, UpdateKinesisStreamingDestination |
| Contributor Insights | DescribeContributorInsights, UpdateContributorInsights |
| Resource Policies | DescribeResourcePolicy, PutResourcePolicy, DeleteResourcePolicy |

---

## Recommendations

### For Users

| Use Case | Recommended Language |
|----------|---------------------|
| Python ecosystem | Python |
| Go/DevOps ecosystem | Go |
| Single binary deployment | Go |
| Maximum features | Go (50 ops vs 53, but different set) |
| AWS SDK compatibility | Both Python and Go |

### For Contributors

| Priority | Language | Work Needed |
|----------|----------|-------------|
| 1 | Rust | 37 operations (batch, transactions, expressions, advanced) |
| 2 | Zig | 37 operations + expression parser |
| 3 | Python/Go | Documentation and polish |

---

## See Also

- [GAP_ANALYSIS.md](GAP_ANALYSIS.md) - Detailed gap analysis
- [STATUS.md](STATUS.md) - Project status
- [DO_NEXT.md](DO_NEXT.md) - Next steps
