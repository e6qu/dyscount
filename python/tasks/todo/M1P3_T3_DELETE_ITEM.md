# Task: M1P3_T3 - Implement DeleteItem Operation

## Status

- [ ] Planned
- [ ] In Progress
- [ ] Code Review
- [ ] Done

## Description

Implement the DynamoDB DeleteItem operation for deleting a single item by primary key.

## Requirements

### API Specification

- **Operation**: `DynamoDB_20120810.DeleteItem`
- **HTTP Method**: POST

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| TableName | String | Yes | Name of the table |
| Key | Map<String, AttributeValue> | Yes | Primary key of item to delete |
| ConditionExpression | String | No | Condition for delete |
| ExpressionAttributeNames | Map<String, String> | No | Name placeholders |
| ExpressionAttributeValues | Map<String, AttributeValue> | No | Value placeholders |
| ReturnConsumedCapacity | String | No | Capacity tracking |
| ReturnItemCollectionMetrics | String | No | Metrics option |
| ReturnValues | String | No | NONE, ALL_OLD |

### Response Format

```json
{
  "Attributes": {
    "pk": {"S": "user#123"},
    "sk": {"S": "profile"},
    "name": {"S": "John"}
  },
  "ConsumedCapacity": {
    "TableName": "Users",
    "CapacityUnits": 1.0
  }
}
```

## Implementation Steps

1. **Add DeleteItem models** in `dyscount_core/models/operations.py`
   - `DeleteItemRequest` and `DeleteItemResponse`

2. **Implement storage method** in `dyscount_core/storage/table_manager.py`
   - `delete_item(table_name, key, condition_expression=None)`
   - Return deleted item for ALL_OLD

3. **Add service method** in `dyscount_core/services/table_service.py`
   - `delete_item(request)`

4. **Add API route** handler for DeleteItem operation

5. **Add tests** in `tests/test_delete_item.py`
   - Delete existing item
   - Delete non-existent item (no error)
   - Conditional delete
   - ReturnValues=ALL_OLD

## Acceptance Criteria

Per `DEFINITION_OF_DONE.md` and `ACCEPTANCE_CRITERIA.md`:

### Code Complete
- [ ] DeleteItem operation implemented per `specs/API_OPERATIONS.md`
- [ ] Request/Response validation matches DynamoDB spec
- [ ] Error handling per `specs/ERROR_CODES.md`:
  - `ResourceNotFoundException` - Table doesn't exist
  - `ValidationException` - Invalid key
  - `ConditionalCheckFailedException` - Condition not met
- [ ] Code follows style guidelines (ruff, ty)
- [ ] No TODO comments

### Testing
- [ ] Unit tests written (>80% coverage)
- [ ] All tests passing:
  - Delete existing item (happy path)
  - Delete non-existent item (silent success)
  - ReturnValues=NONE (default, empty response)
  - ReturnValues=ALL_OLD returns deleted attributes
  - Invalid table name error
  - Invalid key format error
- [ ] E2E test with boto3

### Documentation
- [ ] Docstrings for all public methods
- [ ] Inline comments for complex logic

### Quality Checks
- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] `ty check` passes
- [ ] No security vulnerabilities

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Code reviewed
- [ ] Task file moved to `tasks/done/`
- [ ] Parent state files updated

## Dependencies

- M1P3_T1 (GetItem)
- M1P3_T2 (PutItem - for test setup)

## Estimated Effort

1 day
