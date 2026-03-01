# Task: Implement DeleteTable

## Phase
M1 Phase 2: Python Implementation - Control Plane

## Task ID
M1P2-T6

## Description
Implement the DeleteTable DynamoDB operation.

## Acceptance Criteria
- [ ] DeleteTable endpoint handler working
- [ ] Request validation (table name)
- [ ] Close SQLite connections before deletion
- [ ] Delete SQLite database file
- [ ] Return TableDescription of deleted table
- [ ] Proper error responses (ResourceNotFoundException)
- [ ] Unit tests
- [ ] E2E test with boto3

## Request/Response

### Request (DeleteTable)
```json
{
  "TableName": "string"
}
```

### Response (DeleteTableOutput)
```json
{
  "TableDescription": {
    "TableName": "string",
    "TableStatus": "DELETING",
    "KeySchema": [...],
    "AttributeDefinitions": [...],
    "CreationDateTime": number
  }
}
```

## Implementation Notes

1. Validate table name
2. Check table exists (ResourceNotFoundException if not)
3. Get table metadata for response
4. Close all connections to this database
5. Delete the SQLite file
6. Return TableDescription

## Error Cases
- ResourceNotFoundException - table doesn't exist
- ValidationException - invalid table name

## Estimated Effort
~10k tokens

## Dependencies On
- M1P2-T1 through M1P2-T3: Setup tasks
- M1P2-T5: CreateTable (to create tables for testing)

## Blocks
None

## Notes
Need to handle connection management carefully to avoid "database locked" errors.
