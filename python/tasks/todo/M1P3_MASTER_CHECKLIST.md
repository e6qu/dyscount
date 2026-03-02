# M1 Phase 3: Data Plane - Master Checklist

## Phase Overview

Implement core Data Plane operations for DynamoDB API compatibility.

## Definition of Done (Per `DEFINITION_OF_DONE.md`)

This phase is **Done** when ALL of the following are true:

---

### 1. Code Complete

- [ ] All 4 operations implemented:
  - [ ] GetItem (M1P3_T1)
  - [ ] PutItem (M1P3_T2)
  - [ ] DeleteItem (M1P3_T3)
  - [ ] UpdateItem (M1P3_T4)
- [ ] Condition expressions implemented (M1P3_T5)
- [ ] Code follows style guidelines (ruff, ty)
- [ ] No TODO comments left (unless marked as future work)
- [ ] All error cases handled per `specs/ERROR_CODES.md`:
  - [ ] `ResourceNotFoundException`
  - [ ] `ValidationException`
  - [ ] `ConditionalCheckFailedException`

---

### 2. Tests Pass

- [ ] Unit tests written for all operations (>80% coverage)
- [ ] All unit tests passing:
  - [ ] test_get_item.py
  - [ ] test_put_item.py
  - [ ] test_delete_item.py
  - [ ] test_update_item.py
  - [ ] test_condition_expressions.py
- [ ] E2E tests passing (M1P3_T6):
  - [ ] tests/e2e/test_data_operations.py
- [ ] Integration with CI pipeline

**Test Count Target**: +50 new tests (134+ total)

---

### 3. Documentation Updated

- [ ] Inline code documentation (docstrings) complete
- [ ] Expression parser documented
- [ ] API documentation updated (OpenAPI)
- [ ] README updated with new operations
- [ ] Changelog updated

---

### 4. Quality Checks Pass

- [ ] Linter checks pass: `ruff check .`
- [ ] Type checker passes: `ty check`
- [ ] Formatter run: `ruff format .`
- [ ] No security vulnerabilities

---

### 5. State Files Updated

- [ ] `/STATUS.md` updated with phase completion
- [ ] `/WHAT_WE_DID.md` updated with completed work log
- [ ] `/PLAN.md` updated if plans changed
- [ ] `/DO_NEXT.md` updated with next priorities
- [ ] `python/STATUS.md` updated
- [ ] `python/DO_NEXT.md` updated
- [ ] Task files moved to `python/tasks/done/`:
  - [ ] M1P3_T1_GET_ITEM.md
  - [ ] M1P3_T2_PUT_ITEM.md
  - [ ] M1P3_T3_DELETE_ITEM.md
  - [ ] M1P3_T4_UPDATE_ITEM.md
  - [ ] M1P3_T5_CONDITION_EXPRESSIONS.md
  - [ ] M1P3_T6_E2E_DATA_OPS.md

---

## Acceptance Criteria (Per `ACCEPTANCE_CRITERIA.md`)

### M1 Phase 3 Specific
- [ ] GetItem, PutItem, DeleteItem, UpdateItem working
- [ ] MessagePack serialization working (for item storage)
- [ ] Primary key handling correct
- [ ] Tests passing

### API Compatibility
- [ ] Request/response format matches AWS DynamoDB
- [ ] Error codes and messages match AWS DynamoDB
- [ ] Supports all DynamoDB data types in items

---

## Task Tracking

| Task | Status | Assignee | Start | Complete |
|------|--------|----------|-------|----------|
| M1P3_T1: GetItem | Planned | - | - | - |
| M1P3_T2: PutItem | Planned | - | - | - |
| M1P3_T3: DeleteItem | Planned | - | - | - |
| M1P3_T4: UpdateItem | Planned | - | - | - |
| M1P3_T5: Condition Expressions | Planned | - | - | - |
| M1P3_T6: E2E Tests | Planned | - | - | - |

---

## Sign-off

- [ ] Code review completed
- [ ] User review and approval
- [ ] Phase marked complete in documentation

---

**Note**: Update this checklist as tasks progress. Move task files to `tasks/done/` when complete.
