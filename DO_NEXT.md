# Do Next - M1 Phase 3 COMPLETE, Starting Phase 4

## ✅ Previous Milestones Complete

### M1 Phase 1: Foundation ✅
- Repository structure
- Documentation
- 9 specifications created (~249KB)

### M1 Phase 2: Control Plane ✅ 
- Python monorepo with uv workspace
- 5 DynamoDB operations implemented
- 84 tests passing
- CI/CD workflows added

### M1 Phase 3: Data Plane ✅
- **T1: GetItem** - Complete (10 tests, PR #3 merged)
- **T2: PutItem** - Complete (14 tests, PR #5 merged)
- **T3: DeleteItem** - Complete (13 tests, PR #6 merged)
- **T4: UpdateItem** - Complete (17 tests, PR #7 merged)
- **T5: Condition Expressions** - Complete (70 tests, PR #8 merged)
- **T6: E2E Tests** - Complete (25 tests)
- 208 unit tests + 25 E2E tests

---

## 🚀 Current Phase: M1 Phase 4 - Query & Scan

**Status**: 🟡 **STARTING**

### Phase 4 Tasks

| Task | Operation | Status | Est. Effort |
|------|-----------|--------|-------------|
| M1P4-T1 | Query | 🟡 Next | 2 days |
| M1P4-T2 | Scan | Planned | 1.5 days |
| M1P4-T3 | KeyConditionExpression | Planned | 1 day |
| M1P4-T4 | FilterExpression | Planned | 1 day |
| M1P4-T5 | ProjectionExpression | Planned | 0.5 days |
| M1P4-T6 | Pagination | Planned | 0.5 days |

**Total Effort**: ~6.5 days

---

## 📋 Immediate Next Steps

### 1. Create feature branch for M1 Phase 4
```bash
git checkout main
git pull origin main
git checkout -b feature/M1P4-query-scan
```

### 2. Implement Query Operation (M1P4-T1)

**Goals**:
- Query items by partition key
- Support sort key conditions (begins_with, =, <, <=, >, >=, BETWEEN)
- Support KeyConditionExpression
- Return paginated results with LastEvaluatedKey

**Key Files to Create/Modify**:
- `dyscount_core/expressions/key_condition_parser.py` - Parse KeyConditionExpression
- `dyscount_core/storage/table_manager.py` - Add query() method
- `dyscount_core/services/item_service.py` - Add query() service method
- `dyscount_api/routes/tables.py` - Add Query route handler
- `tests/test_query.py` - Comprehensive tests

**Implementation Notes**:
- Use SQLite index on pk column for efficient queries
- For sort key conditions, filter in SQL WHERE clause
- Support ascending/descending order (ScanIndexForward)
- Handle pagination with Limit and ExclusiveStartKey

### 3. Implement Scan Operation (M1P4-T2)

**Goals**:
- Full table scan with optional filters
- Support FilterExpression
- Pagination support

**Key Files**:
- Similar structure to Query
- `tests/test_scan.py` - Tests

---

## 📊 Project Progress

| Milestone | Phases | Progress |
|-----------|--------|----------|
| M1: Foundation | 10 | 🟡 80% (3 complete, 1 starting) |
| M2: Advanced | 4 | ⚪ 0% |
| M3: Global/Streams | 3 | ⚪ 0% |
| M4: Import/Export | 3 | ⚪ 0% |
| **Total** | **20** | **40%** |

---

## 🔜 M1 Phase 4 Scope

**Query Operation Features**:
- Query by partition key (required)
- Sort key conditions (optional)
  - `=`, `<`, `<=`, `>`, `>=`, `BETWEEN`, `begins_with`
- KeyConditionExpression parser
- FilterExpression for post-filtering
- ProjectionExpression for attribute selection
- ScanIndexForward (ascending/descending)
- Limit and pagination (ExclusiveStartKey, LastEvaluatedKey)
- ReturnConsumedCapacity

**Scan Operation Features**:
- Full table scan
- FilterExpression support
- ProjectionExpression
- Limit and pagination
- Segment/TotalSegments for parallel scans
- ReturnConsumedCapacity

---

## 📝 Notes

- M1 Phase 3 is 100% complete
- All 6 tasks merged to main
- 208 unit tests passing
- 25 E2E tests ready (require running server)
- Expression parser infrastructure ready from T5
- SQLite storage layer ready for Query/Scan
