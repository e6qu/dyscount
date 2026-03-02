# Task: M1P3_T6 - E2E Tests for Data Operations

## Status

- [ ] Planned
- [ ] In Progress
- [ ] Code Review
- [ ] Done

## Description

Create comprehensive end-to-end tests using boto3 to verify all data plane operations work correctly against the running server.

## Requirements

### Test Coverage

1. **GetItem E2E**
   - Get existing item
   - Get non-existent item
   - With projection expression
   - With consistent read

2. **PutItem E2E**
   - Put new item with all attribute types
   - Replace existing item
   - Conditional put
   - ReturnValues options

3. **DeleteItem E2E**
   - Delete existing item
   - Delete non-existent item
   - Conditional delete
   - ReturnValues=ALL_OLD

4. **UpdateItem E2E**
   - SET operations
   - REMOVE operations
   - ADD operations
   - DELETE operations (sets)
   - Conditional updates
   - All ReturnValues options

5. **Integration Scenarios**
   - Put → Get → Update → Get → Delete → Get (full lifecycle)
   - Multiple items in same table
   - Concurrent modifications (error handling)

### Test Structure

```python
# tests/e2e/test_data_operations.py

class TestDataOperations:
    def test_put_and_get_item(self, client, table_name):
        # Put item
        client.put_item(...)
        # Get item
        response = client.get_item(...)
        # Verify
        assert response['Item'] == ...
```

## Implementation Steps

1. **Create E2E test file** `tests/e2e/test_data_operations.py`

2. **Add fixtures** for:
   - boto3 client
   - Test table creation
   - Test item data

3. **Implement test cases** for each operation

4. **Add integration scenarios**

5. **Verify against real DynamoDB** (optional comparison)

## Acceptance Criteria

Per `DEFINITION_OF_DONE.md` and `ACCEPTANCE_CRITERIA.md`:

### Code Complete
- [ ] E2E tests created for all data operations
- [ ] Tests use boto3 (AWS SDK for Python)
- [ ] Tests run against running server
- [ ] Proper test isolation (clean state between tests)
- [ ] Code follows style guidelines (ruff, ty)
- [ ] No TODO comments

### Testing
- [ ] E2E tests written for:
  - GetItem (existing, non-existent, projection, consistent read)
  - PutItem (new, replace, all attribute types, ReturnValues)
  - DeleteItem (existing, non-existent, ReturnValues=ALL_OLD)
  - UpdateItem (SET, REMOVE, ADD, DELETE, all ReturnValues)
  - Full item lifecycle (Put → Get → Update → Get → Delete)
- [ ] All E2E tests passing
- [ ] Tests run in CI pipeline

### Documentation
- [ ] Docstrings for test classes and methods
- [ ] README for running E2E tests locally

### Quality Checks
- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] `ty check` passes
- [ ] Tests are deterministic (no flaky tests)

### CI Integration
- [ ] E2E tests run in GitHub Actions
- [ ] Server started before tests
- [ ] Proper cleanup after tests
- [ ] Test results reported

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Code reviewed
- [ ] Task file moved to `tasks/done/`
- [ ] Parent state files updated
- [ ] E2E tests running in CI

## Dependencies

- M1P3_T1 through T5 (all data operations)
- Running server for tests
- boto3 installed

## Estimated Effort

1 day
