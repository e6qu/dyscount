# Task: M1P3_T1 - Implement GetItem Operation

## Status

- [ ] Planned
- [ ] In Progress
- [ ] Code Review
- [ ] Done

## Description

Implement the DynamoDB GetItem operation for retrieving a single item by its primary key.

## Requirements

### API Specification

- **Operation**: `DynamoDB_20120810.GetItem`
- **HTTP Method**: POST
- **Response**: JSON with item data or empty response if not found

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| TableName | String | Yes | Name of the table |
| Key | Map<String, AttributeValue> | Yes | Primary key of the item |
| AttributesToGet | List<String> | No | Specific attributes to retrieve |
| ConsistentRead | Boolean | No | Strongly consistent read (default: false) |
| ProjectionExpression | String | No | Expression to limit returned attributes |
| ExpressionAttributeNames | Map<String, String> | No | Name placeholders |

### Response Format

```json
{
  "Item": {
    "pk": {"S": "user#123"},
    "sk": {"S": "profile"},
    "name": {"S": "John Doe"},
    "email": {"S": "john@example.com"}
  },
  "ConsumedCapacity": {
    "TableName": "Users",
    "CapacityUnits": 0.5
  }
}
```

## Implementation Steps

1. **Add GetItem models** in `dyscount_core/models/operations.py`
   - `GetItemRequest` with validation
   - `GetItemResponse` with item data

2. **Implement storage method** in `dyscount_core/storage/table_manager.py`
   - `get_item(table_name, key, consistent_read=False)`
   - Serialize/deserialize AttributeValue
   - Handle projection expressions

3. **Add service method** in `dyscount_core/services/table_service.py`
   - `get_item(request)` with validation
   - Calculate consumed capacity

4. **Add API route** in `dyscount_api/routes/items.py` (or extend tables.py)
   - Handle GetItem operation
   - Return proper response format

5. **Add tests** in `tests/test_get_item.py`
   - Get existing item
   - Get non-existent item (empty response)
   - Projection expression filtering
   - Consistent read behavior

## Acceptance Criteria

Per `DEFINITION_OF_DONE.md` and `ACCEPTANCE_CRITERIA.md`:

### Code Complete
- [ ] GetItem operation implemented per `specs/API_OPERATIONS.md`
- [ ] Request/Response validation matches DynamoDB spec
- [ ] Error handling per `specs/ERROR_CODES.md`:
  - `ResourceNotFoundException` - Table doesn't exist
  - `ValidationException` - Invalid key, malformed request
- [ ] Code follows style guidelines (ruff, ty)
- [ ] No TODO comments (unless marked as future work)

### Testing
- [ ] Unit tests written (>80% coverage for new code)
- [ ] All tests passing:
  - Get existing item (happy path)
  - Get non-existent item (empty response)
  - AttributesToGet filtering
  - ProjectionExpression filtering
  - Invalid table name error
  - Invalid key format error
- [ ] E2E test with boto3

### Documentation
- [ ] Docstrings for all public methods
- [ ] Inline comments for complex logic
- [ ] OpenAPI spec updated (if applicable)

### Quality Checks
- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] `ty check` passes
- [ ] No security vulnerabilities

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Code reviewed
- [ ] Task file moved to `tasks/done/`
- [ ] Parent state files updated (STATUS.md, WHAT_WE_DID.md, DO_NEXT.md)

## Dependencies

- M1 Phase 2 (Table operations)
- AttributeValue serialization
- SQLite storage layer

## Estimated Effort

1 day
