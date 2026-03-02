# Task: M1P3_T2 - Implement PutItem Operation

## Status

- [x] Done

## Description

Implement the DynamoDB PutItem operation for creating or replacing an item.

## Requirements

### API Specification

- **Operation**: `DynamoDB_20120810.PutItem`
- **HTTP Method**: POST
- **Response**: JSON with item attributes (or empty if ReturnValues=NONE)

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| TableName | String | Yes | Name of the table |
| Item | Map<String, AttributeValue> | Yes | Item to put |
| ConditionExpression | String | No | Condition for put operation |
| ExpressionAttributeNames | Map<String, String> | No | Name placeholders |
| ExpressionAttributeValues | Map<String, AttributeValue> | No | Value placeholders |
| ReturnConsumedCapacity | String | No | INDEXES, TOTAL, or NONE |
| ReturnItemCollectionMetrics | String | No | SIZE or NONE |
| ReturnValues | String | No | NONE, ALL_OLD |

### Response Format

```json
{
  "Attributes": {
    "pk": {"S": "user#123"},
    "sk": {"S": "profile"}
  },
  "ConsumedCapacity": {
    "TableName": "Users",
    "CapacityUnits": 1.0
  }
}
```

## Implementation Steps

1. **Add PutItem models** in `dyscount_core/models/operations.py`
   - `PutItemRequest` with validation
   - `PutItemResponse`

2. **Implement storage method** in `dyscount_core/storage/table_manager.py`
   - `put_item(table_name, item, condition_expression=None)`
   - Handle item serialization
   - Support conditional expressions (basic support)

3. **Add service method** in `dyscount_core/services/table_service.py`
   - `put_item(request)` with validation
   - Handle ReturnValues (ALL_OLD)

4. **Add API route** handler for PutItem operation

5. **Add tests** in `tests/test_put_item.py`
   - Put new item
   - Replace existing item
   - Conditional put (success and failure)
   - ReturnValues options

## Acceptance Criteria

Per `DEFINITION_OF_DONE.md` and `ACCEPTANCE_CRITERIA.md`:

### Code Complete
- [ ] PutItem operation implemented per `specs/API_OPERATIONS.md`
- [ ] Request/Response validation matches DynamoDB spec
- [ ] Error handling per `specs/ERROR_CODES.md`:
  - `ResourceNotFoundException` - Table doesn't exist
  - `ValidationException` - Invalid item, missing key attributes
  - `ConditionalCheckFailedException` - Condition not met (if condition expressions implemented)
- [ ] Code follows style guidelines (ruff, ty)
- [ ] No TODO comments

### Testing
- [ ] Unit tests written (>80% coverage)
- [ ] All tests passing:
  - Put new item (happy path)
  - Replace existing item
  - Put with all AttributeValue types
  - ReturnValues=NONE (default)
  - ReturnValues=ALL_OLD returns previous attributes
  - Invalid table name error
  - Missing key attributes error
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

- M1 Phase 2 (Table operations)
- M1P3_T1 (GetItem - for ALL_OLD support)

## Estimated Effort

1.5 days
