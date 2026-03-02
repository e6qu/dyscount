# Task: M1P3_T4 - Implement UpdateItem Operation

## Status

- [ ] Planned
- [ ] In Progress
- [ ] Code Review
- [ ] Done

## Description

Implement the DynamoDB UpdateItem operation for modifying item attributes with update expressions.

## Requirements

### API Specification

- **Operation**: `DynamoDB_20120810.UpdateItem`
- **HTTP Method**: POST

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| TableName | String | Yes | Name of the table |
| Key | Map<String, AttributeValue> | Yes | Primary key |
| UpdateExpression | String | Yes | Expression for update (SET, REMOVE, ADD, DELETE) |
| ConditionExpression | String | No | Condition for update |
| ExpressionAttributeNames | Map<String, String> | No | Name placeholders |
| ExpressionAttributeValues | Map<String, AttributeValue> | No | Value placeholders |
| ReturnConsumedCapacity | String | No | Capacity tracking |
| ReturnValues | String | No | NONE, ALL_OLD, ALL_NEW, UPDATED_OLD, UPDATED_NEW |

### UpdateExpression Operators

- **SET**: Set attribute values
  - `SET #n = :val, #n2 = :val2`
  - `SET #n = #n + :inc`
  - `SET #n = list_append(#n, :list)`
- **REMOVE**: Remove attributes
  - `REMOVE #n, #n2`
- **ADD**: Add to numbers or sets
  - `ADD #n :num`
  - `ADD #s :set_val`
- **DELETE**: Remove from sets
  - `DELETE #s :set_val`

### Response Format

```json
{
  "Attributes": {
    "pk": {"S": "user#123"},
    "counter": {"N": "42"}
  },
  "ConsumedCapacity": {
    "TableName": "Users",
    "CapacityUnits": 1.0
  }
}
```

## Implementation Steps

1. **Add UpdateItem models** in `dyscount_core/models/operations.py`

2. **Create expression module** `dyscount_core/expressions/`
   - `parser.py` - Parse UpdateExpression into AST
   - `evaluator.py` - Evaluate AST against item
   - Support SET, REMOVE, ADD, DELETE clauses
   - Handle functions (list_append, if_not_exists)

3. **Implement storage method** in `dyscount_core/storage/table_manager.py`
   - `update_item(table_name, key, update_expression, ...)`
   - Execute parsed expression against item

4. **Add service method** in `dyscount_core/services/table_service.py`

5. **Add API route** handler for UpdateItem

6. **Add tests** in `tests/test_update_item.py`
   - SET operations
   - REMOVE operations
   - ADD operations (numbers and sets)
   - DELETE operations (sets)
   - list_append function
   - if_not_exists function
   - All ReturnValues options
   - Conditional updates

## Acceptance Criteria

Per `DEFINITION_OF_DONE.md` and `ACCEPTANCE_CRITERIA.md`:

### Code Complete
- [ ] UpdateItem operation implemented per `specs/API_OPERATIONS.md`
- [ ] UpdateExpression parser supports: SET, REMOVE, ADD, DELETE
- [ ] UpdateExpression functions: list_append, if_not_exists
- [ ] Request/Response validation matches DynamoDB spec
- [ ] Error handling per `specs/ERROR_CODES.md`:
  - `ResourceNotFoundException` - Table doesn't exist
  - `ValidationException` - Invalid expression, invalid key
  - `ConditionalCheckFailedException` - Condition not met
- [ ] Code follows style guidelines (ruff, ty)
- [ ] No TODO comments

### Testing
- [ ] Unit tests written (>80% coverage)
- [ ] All tests passing:
  - SET scalar attributes
  - SET with arithmetic (+, -)
  - SET with list_append
  - SET with if_not_exists
  - REMOVE attributes
  - ADD to numbers (increment)
  - ADD to sets
  - DELETE from sets
  - All ReturnValues options (NONE, ALL_OLD, ALL_NEW, UPDATED_OLD, UPDATED_NEW)
  - Conditional updates
  - Invalid expression errors
- [ ] E2E test with boto3

### Documentation
- [ ] Docstrings for all public methods
- [ ] Expression parser documented
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

- M1P3_T1, T2, T3 (other item operations)
- M1P3_T5 (Condition Expressions) - can be done in parallel
- Expression parser implementation

## Estimated Effort

3 days (complex due to expression parsing)
