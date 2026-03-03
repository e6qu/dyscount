# Feature Comparison - Remaining Work by Language

## Current Status Overview

| Language | Operations | Coverage | Status |
|----------|-----------|----------|--------|
| **Python** | 53/61 | 87% | Production Ready ✅ |
| **Go** | 22/61 | 36% | M2 Phase 1 Complete |
| **Rust** | 21/61 | 34% | Feature Parity Phase 1 |
| **Zig** | 13/61 | 21% | DP Phase 2 Complete |

---

## Detailed Feature Matrix

### Control Plane (5 operations)

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| CreateTable | ✅ | ✅ | ✅ | ✅ |
| DeleteTable | ✅ | ✅ | ✅ | ✅ |
| ListTables | ✅ | ✅ | ✅ | ✅ |
| DescribeTable | ✅ | ✅ | ✅ | ✅ |
| DescribeEndpoints | ✅ | ✅ | ✅ | ✅ |
| **Control Plane Complete** | ✅ | ✅ | ✅ | ✅ |

---

### Data Plane - Basic Operations (5 operations)

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| GetItem | ✅ | ✅ | ✅ | ✅ |
| PutItem | ✅ | ✅ | ✅ | ✅ |
| UpdateItem | ✅ | ✅ | ✅ | ✅ (stub) |
| DeleteItem | ✅ | ✅ | ✅ | ✅ |
| **Basic Data Plane** | ✅ | ✅ | ✅ | 🚧 |

---

### Data Plane - Query & Scan (2 operations)

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| Query | ✅ | ✅ | ✅ | ✅ |
| Scan | ✅ | ✅ | ✅ | ✅ |
| FilterExpression | ✅ | ✅ | ✅ | ❌ |
| ProjectionExpression | ✅ | ✅ | ❌ | ❌ |
| **Query/Scan Complete** | ✅ | ✅ | 🚧 | 🚧 |

---

### Data Plane - Batch Operations (2 operations)

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| BatchGetItem | ✅ | ✅ | 🚧 (stub) | 🚧 (stub) |
| BatchWriteItem | ✅ | ✅ | 🚧 (stub) | 🚧 (stub) |
| **Batch Operations** | ✅ | ✅ | 🚧 | 🚧 |

**Notes:**
- Go: Full implementation with projection support
- Rust: Types + storage layer implemented, handlers stubbed
- Zig: Returns 501 Not Implemented

---

### Data Plane - Transactions (2 operations)

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| TransactGetItems | ✅ | ✅ | 🚧 (stub) | ❌ |
| TransactWriteItems | ✅ | ✅ | 🚧 (stub) | ❌ |
| **Transactions** | ✅ | ✅ | 🚧 | ❌ |

**Notes:**
- Go: Full implementation with atomicity per table
- Rust: Types + storage layer implemented, handlers stubbed
- Zig: Not implemented

---

### Data Plane - Expressions (4 capabilities)

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| ConditionExpression | ✅ | ✅ | ✅ | ❌ |
| FilterExpression | ✅ | ✅ | ✅ | ❌ |
| UpdateExpression (SET) | ✅ | ✅ | ✅ | ✅ |
| UpdateExpression (ADD/DELETE/REMOVE) | ✅ | ✅ | ✅ | ❌ |
| Expression Attribute Names | ✅ | ✅ | ✅ | ❌ |
| Expression Attribute Values | ✅ | ✅ | ✅ | ❌ |
| **Expressions Complete** | ✅ | ✅ | ✅ | 🚧 |

**Notes:**
- Python: Full Tree-sitter based parser
- Go: Custom parser with all operators
- Rust: New expression module with parser + evaluator
- Zig: Basic SET support only

---

### Schema Operations (1 operation)

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| UpdateTable | ✅ | ✅ | ✅ (types) | ❌ |
| UpdateTable (GSI Create) | ✅ | ✅ | 🚧 (types) | ❌ |
| UpdateTable (GSI Update) | ✅ | ✅ | 🚧 (types) | ❌ |
| UpdateTable (GSI Delete) | ✅ | ✅ | 🚧 (types) | ❌ |
| **Schema Operations** | ✅ | ✅ | 🚧 | ❌ |

---

### M2: Advanced Operations (11 operations)

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| TTL (UpdateTimeToLive) | ✅ | ❌ | ❌ | ❌ |
| TTL (DescribeTimeToLive) | ✅ | ❌ | ❌ | ❌ |
| CreateBackup | ✅ | ❌ | ❌ | ❌ |
| RestoreTableFromBackup | ✅ | ❌ | ❌ | ❌ |
| ListBackups | ✅ | ❌ | ❌ | ❌ |
| DeleteBackup | ✅ | ❌ | ❌ | ❌ |
| UpdateContinuousBackups | ✅ | ❌ | ❌ | ❌ |
| DescribeContinuousBackups | ✅ | ❌ | ❌ | ❌ |
| RestoreTableToPointInTime | ✅ | ❌ | ❌ | ❌ |
| ExecuteStatement (PartiQL) | ✅ | ❌ | ❌ | ❌ |
| BatchExecuteStatement | ✅ | ❌ | ❌ | ❌ |
| **M2 Advanced** | ✅ | ❌ | ❌ | ❌ |

---

### M4 Phase 1: Import/Export (6 operations)

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| ExportTableToPointInTime | ✅ | ❌ | ❌ | ❌ |
| DescribeExport | ✅ | ❌ | ❌ | ❌ |
| ListExports | ✅ | ❌ | ❌ | ❌ |
| ImportTable | ✅ | ❌ | ❌ | ❌ |
| DescribeImport | ✅ | ❌ | ❌ | ❌ |
| ListImports | ✅ | ❌ | ❌ | ❌ |
| **Import/Export** | ✅ | ❌ | ❌ | ❌ |

---

### M3: Streams (4 operations)

| Feature | Python | Go | Rust | Zig |
|---------|--------|-----|------|-----|
| Enable/Disable Streams | ❌ | ❌ | ❌ | ❌ |
| GetRecords | ❌ | ❌ | ❌ | ❌ |
| GetShardIterator | ❌ | ❌ | ❌ | ❌ |
| DescribeStream | ❌ | ❌ | ❌ | ❌ |
| **Streams** | ❌ | ❌ | ❌ | ❌ |

---

## Remaining Work Summary

### Python (8 operations to 100%)
1. Streams (4 operations)
2. Other advanced features

### Go (39 operations to catch up to Python)
**Priority 1 - M2 Phase 2 (9 ops, ~2 weeks):**
| Operation | Effort |
|-----------|--------|
| TTL Operations | 3 days |
| Backup/Restore | 4 days |
| PITR | 3 days |

**Priority 2 - M4 Phase 1 (6 ops, ~1 week):**
| Operation | Effort |
|-----------|--------|
| Import/Export | 1 week |

**Priority 3 - M2 Phase 4 (2 ops, ~1 week):**
| Operation | Effort |
|-----------|--------|
| PartiQL | 1 week |

### Rust (40 operations to catch up to Python)
**Priority 1 - Complete Current Work (1 op, ~2 days):**
| Operation | Effort |
|-----------|--------|
| UpdateTable GSI (full storage impl) | 2 days |

**Priority 2 - M2 Phase 2+ (17 ops, ~4 weeks):**
Same as Go's remaining work

### Zig (48 operations to catch up to Python)
**Priority 1 - Data Plane Phase 3 (3 ops, ~1 week):**
| Operation | Effort |
|-----------|--------|
| Full BatchGetItem | 2 days |
| Full BatchWriteItem | 2 days |
| Expression Parser | 3 days |

**Priority 2 - Transactions (2 ops, ~1 week):**
| Operation | Effort |
|-----------|--------|
| TransactGetItems | 3 days |
| TransactWriteItems | 4 days |

**Priority 3 - M2+ (remaining):**
Same structure as Go/Rust

---

## Recommended Next Steps

### Option A: Python-First (Recommended for v1.0)
- Focus: Complete Python implementation
- Work: Streams + Polish + Production Readiness
- Timeline: 2-3 weeks
- Outcome: Production-ready single implementation

### Option B: Multi-Language Parity
- Focus: Bring Go/Rust/Zig to M2 completion
- Work: 16 weeks parallel effort
- Outcome: 4 complete implementations

### Option C: Hybrid Approach
- Focus: Python as primary, others as reference
- Work: Document Go/Rust/Zig as "basic implementations"
- Outcome: One production-ready + 3 reference impls
