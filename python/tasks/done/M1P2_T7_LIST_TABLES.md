# Task: Implement ListTables

## Phase
M1 Phase 2: Python Implementation - Control Plane

## Task ID
M1P2-T7

## Description
Implement the ListTables DynamoDB operation.

## Acceptance Criteria
- [ ] ListTables endpoint handler working
- [ ] Scan data directory for .db files
- [ ] Support pagination (ExclusiveStartTableName, Limit)
- [ ] Return table names in alphabetical order
- [ ] Return LastEvaluatedTableName if more tables exist
- [ ] Proper error responses
- [ ] Unit tests
- [ ] E2E test with boto3

## Request/Response

### Request (ListTables)
```json
{
  "ExclusiveStartTableName": "string",
  "Limit": number
}
```

### Response (ListTablesOutput)
```json
{
  "TableNames": ["string", ...],
  "LastEvaluatedTableName": "string"
}
```

## Implementation Notes

1. Scan `/data/{namespace}/` for `*.db` files
2. Extract table names from filenames (remove .db extension)
3. Sort alphabetically
4. Handle pagination:
   - If ExclusiveStartTableName provided, start after it
   - Return at most Limit tables (default: 100)
   - Return LastEvaluatedTableName if more exist
5. Return TableNames array

## Error Cases
- ValidationException - invalid table name in ExclusiveStartTableName

## Estimated Effort
~10k tokens

## Dependencies On
- M1P2-T1 through M1P2-T3: Setup tasks
- M1P2-T5: CreateTable (to create tables for testing)

## Blocks
None

## Notes
Pagination is important for tables with many tables. Follow DynamoDB's pagination pattern exactly.
