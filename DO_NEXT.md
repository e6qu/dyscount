# Do Next - M1 COMPLETE, Starting M2

## ✅ Previous Milestones Complete

### M1 Phase 1: Foundation ✅
- Repository structure
- Documentation
- 9 specifications created (~249KB)

### M1 Phase 2: Python Control Plane ✅ 
- Python monorepo with uv workspace
- 5 DynamoDB operations implemented
- 84 tests passing

### M1 Phase 3: Python Data Plane ✅
- GetItem, PutItem, DeleteItem, UpdateItem
- Condition Expressions
- E2E Tests
- 208 tests passing

### M1 Phase 4: Query & Scan ✅
- Query with KeyConditionExpression
- Scan with FilterExpression
- Pagination support
- 233 tests passing

### M1 Phase 5: Batch, Transactions & Indexes ✅
- BatchGetItem, BatchWriteItem
- TransactGetItems, TransactWriteItems
- GSI/LSI support
- 294 tests passing

### M1 Phase 6: Metrics & Tagging ✅
- Prometheus metrics endpoint
- TagResource, UntagResource, ListTagsOfResource
- AWS SigV4 deferred to later phase
- 309 tests passing

### M1 Phase 7: Go Implementation ✅
- Full Go implementation (control + data plane)
- 50 tests passing

### M1 Phase 8: Rust Implementation ✅
- Full Rust implementation (control + data plane)
- 21 tests passing

### M1 Phase 9: Zig Implementation ✅
- Zig control plane implementation
- 9 tests passing

---

## 🚀 Current Phase: M2 - Advanced Operations

**Status**: ⚪ **STARTING**

### M2 Phase 1: Time-to-Live (TTL)

| Task | Operation | Status | Est. Effort |
|------|-----------|--------|-------------|
| M2P1-T1 | TTL Implementation | Planned | 2 days |
| M2P1-T2 | Expiration Management | Planned | 1.5 days |

**Total Effort**: ~3.5 days

### M2 Phase 2: Backup & Restore

| Task | Operation | Status | Est. Effort |
|------|-----------|--------|-------------|
| M2P2-T1 | CreateBackup | Planned | 2 days |
| M2P2-T2 | RestoreTableFromBackup | Planned | 2 days |
| M2P2-T3 | ListBackups | Planned | 1 day |

**Total Effort**: ~5 days

### M2 Phase 3: Point-in-Time Recovery

| Task | Operation | Status | Est. Effort |
|------|-----------|--------|-------------|
| M2P3-T1 | Enable/Disable PITR | Planned | 2 days |
| M2P3-T2 | RestoreTableToPointInTime | Planned | 2 days |

**Total Effort**: ~4 days

### M2 Phase 4: Advanced Query Features

| Task | Operation | Status | Est. Effort |
|------|-----------|--------|-------------|
| M2P4-T1 | PartiQL Support | Planned | 3 days |
| M2P4-T2 | Parallel Scan Improvements | Planned | 1.5 days |

**Total Effort**: ~4.5 days

---

## 📋 Immediate Next Steps

### 1. Create feature branch for M2 Phase 1
```bash
git checkout main
git pull origin main
git checkout -b feature/M2P1-ttl
```

### 2. Implement TTL (M2P1-T1)

**Goals**:
- Enable TTL on tables
- Store expiration timestamps
- Background cleanup process
- UpdateItem with TTL attribute

### 3. M1 Phase 10: Cross-Language E2E Testing

Before moving fully to M2, complete E2E validation:

**Goals**:
- boto3 tests against Go implementation
- boto3 tests against Rust implementation
- boto3 tests against Zig implementation
- Performance benchmarks across languages
- Compatibility matrix validation

---

## 📊 Project Progress

| Milestone | Phases | Progress |
|-----------|--------|----------|
| M1: Foundation | 9 | ✅ 100% |
| M2: Advanced | 4 | ⚪ 0% |
| M3: Global/Streams | 3 | ⚪ 0% |
| M4: Import/Export | 3 | ⚪ 0% |
| **Total** | **19** | **53%** |

---

## 🔜 M2 Phase 1 Scope

**TTL Operations**:
- UpdateTimeToLive - Enable/disable TTL on a table
- DescribeTimeToLive - Get TTL configuration
- Automatic item expiration
- Background cleanup process

---

## 📝 Notes

- M1 is 100% complete (all 9 phases)
- 389 total tests passing across 4 languages
- 36 DynamoDB operations implemented
- Ready for advanced features (TTL, backups, PITR)
- AWS SigV4 auth deferred to production phase
