# Task: Go & Rust Feature Parity (M1+M2)

## Task ID
GAP-CLOSURE-1

## Description
Bring Go and Rust implementations to feature parity with Python's M1 (Foundation) and M2 (Advanced Operations) phases. This adds 20 operations to each language.

## Current State

| Metric | Go | Rust | Python (Target) |
|--------|-----|------|-----------------|
| Operations | 16 | 13 | 47 |
| Test Coverage | 50 | 21 | 427 |
| Missing | 31 | 34 | 0 |

## Target State

| Metric | Go | Rust |
|--------|-----|------|
| Operations | 36 | 36 |
| Test Coverage | 150+ | 100+ |

## Operations to Add (20 per language)

### Phase 1: Critical Data Plane (8 ops)
**Priority**: Critical | **Effort**: 1 week

| Operation | Go | Rust | Notes |
|-----------|-----|------|-------|
| BatchGetItem | ❌ | ❌ | Up to 100 items |
| BatchWriteItem | ❌ | ❌ | Up to 25 items |
| TransactGetItems | ❌ | ❌ | Atomic read |
| TransactWriteItems | ❌ | ❌ | Atomic write |
| ConditionExpression | ❌ | ❌ | For Put/Update/Delete |
| FilterExpression | ❌ | ❌ | For Query/Scan |
| UpdateTable | ❌ | ❌ | GSI support |
| UpdateExpression | ⚠️ | ⚠️ | Full SET/REMOVE/ADD/DELETE |

### Phase 2: TTL Operations (2 ops)
**Priority**: High | **Effort**: 3 days

| Operation | Go | Rust |
|-----------|-----|------|
| UpdateTimeToLive | ❌ | ❌ |
| DescribeTimeToLive | ❌ | ❌ |

### Phase 3: Backup/Restore (4 ops)
**Priority**: Medium | **Effort**: 4 days

| Operation | Go | Rust |
|-----------|-----|------|
| CreateBackup | ❌ | ❌ |
| RestoreTableFromBackup | ❌ | ❌ |
| ListBackups | ❌ | ❌ |
| DeleteBackup | ❌ | ❌ |

### Phase 4: PITR (3 ops)
**Priority**: Medium | **Effort**: 3 days

| Operation | Go | Rust |
|-----------|-----|------|
| UpdateContinuousBackups | ❌ | ❌ |
| DescribeContinuousBackups | ❌ | ❌ |
| RestoreTableToPointInTime | ❌ | ❌ |

### Phase 5: PartiQL (2 ops)
**Priority**: Low | **Effort**: 1 week

| Operation | Go | Rust |
|-----------|-----|------|
| ExecuteStatement | ❌ | ❌ |
| BatchExecuteStatement | ❌ | ❌ |

### Phase 6: Tagging (3 ops) - Complete Implementation
**Priority**: Low | **Effort**: 2 days

| Operation | Go | Rust | Current |
|-----------|-----|------|---------|
| TagResource | ⚠️ | ⚠️ | Stubs only |
| UntagResource | ⚠️ | ⚠️ | Stubs only |
| ListTagsOfResource | ⚠️ | ⚠️ | Stubs only |

## Implementation Details

### Expression Parser

Both Go and Rust need expression parsers for:
- ConditionExpression
- FilterExpression  
- KeyConditionExpression
- UpdateExpression

**Approach**:
1. Port Python's expression parser
2. Or implement using existing libraries:
   - Go: Use `github.com/alecthomas/participle` or custom parser
   - Rust: Use `nom` or `pest` parser combinator

### Storage Layer Updates

**Go** (`internal/storage/`):
- Add batch operation methods to `item_manager.go`
- Add transaction support
- Add TTL tracking
- Add backup/restore methods

**Rust** (`src/`):
- Extend `items.rs` with batch operations
- Add transaction support
- Add TTL tracking
- Add backup/restore methods

## Test Plan

### Go Tests Needed

| Test File | Tests | Focus |
|-----------|-------|-------|
| batch_operations_test.go | 15 | BatchGetItem, BatchWriteItem |
| transaction_test.go | 15 | TransactGetItems, TransactWriteItems |
| expression_test.go | 20 | Condition, Filter, Update expressions |
| ttl_test.go | 10 | TTL operations |
| backup_test.go | 15 | Backup/Restore/PITR |

### Rust Tests Needed

| Test Module | Tests | Focus |
|-------------|-------|-------|
| batch_tests | 15 | Batch operations |
| transaction_tests | 15 | Transactions |
| expression_tests | 20 | Expressions |
| ttl_tests | 10 | TTL |
| backup_tests | 15 | Backup/Restore |

## Acceptance Criteria

- [ ] All 20 operations implemented in Go
- [ ] All 20 operations implemented in Rust
- [ ] 150+ tests passing in Go
- [ ] 100+ tests passing in Rust
- [ ] Expression parser working in both
- [ ] Batch operations handle up to 100/25 items
- [ ] Transactions are atomic
- [ ] TTL background cleanup works
- [ ] Backup/restore round-trip verified
- [ ] All existing tests still pass

## Definition of Done

- [ ] Go implementation matches Python M1+M2
- [ ] Rust implementation matches Python M1+M2
- [ ] CI passes for both languages
- [ ] Documentation updated
- [ ] Task file moved to done/

## Estimated Effort

| Phase | Go | Rust | Parallel |
|-------|-----|------|----------|
| Phase 1: Critical Data Plane | 1 week | 1 week | Yes |
| Phase 2: TTL | 3 days | 3 days | Yes |
| Phase 3: Backup/Restore | 4 days | 4 days | Yes |
| Phase 4: PITR | 3 days | 3 days | Yes |
| Phase 5: PartiQL | 1 week | 1 week | Yes |
| Phase 6: Tagging | 2 days | 2 days | Yes |
| **Total** | **~5 weeks** | **~5 weeks** | **~5 weeks total** |

## Notes

- Go and Rust can be developed in parallel
- Python implementation is reference
- Expression parser is the hardest part - consider using existing libraries
- Focus on correctness over performance initially
