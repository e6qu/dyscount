# Task: Implement CreateTable

## Phase
M1 Phase 2: Python Implementation - Control Plane

## Task ID
M1P2-T5

## Description
Implement the CreateTable DynamoDB operation.

## Acceptance Criteria
- [ ] CreateTable endpoint handler working
- [ ] Request validation (table name, key schema, attributes)
- [ ] SQLite database file created at `/data/{namespace}/{table_name}.db`
- [ ] Metadata table created in SQLite
- [ ] Items table created with pk/sk columns
- [ ] Table status returned as CREATING → ACTIVE
- [ ] Proper error responses (TableAlreadyExistsException, ValidationException)
- [ ] Unit tests
- [ ] E2E test with boto3

## Request/Response

### Request (CreateTable)
```json
{
  "TableName": "string",
  "AttributeDefinitions": [
    {"AttributeName": "string", "AttributeType": "S|N|B"}
  ],
  "KeySchema": [
    {"AttributeName": "string", "KeyType": "HASH|RANGE"}
  ],
  "BillingMode": "PROVISIONED|PAY_PER_REQUEST"
}
```

### Response (CreateTableOutput)
```json
{
  "TableDescription": {
    "TableName": "string",
    "TableStatus": "CREATING|UPDATING|DELETING|ACTIVE",
    "KeySchema": [...],
    "AttributeDefinitions": [...],
    "CreationDateTime": number
  }
}
```

## Implementation Notes

1. Validate table name (3-255 chars, alphanumeric + special chars)
2. Validate key schema (1-2 elements, first must be HASH)
3. Validate attribute definitions match key schema
4. Create directory if not exists
5. Create SQLite file
6. Create tables:
   - `__metadata`: table configuration
   - `items`: pk (BLOB), sk (BLOB), item_data (BLOB)
7. Return TableDescription

## Error Cases
- TableAlreadyExistsException - table already exists
- ValidationException - invalid table name, invalid key schema
- LimitExceededException - too many tables

## Estimated Effort
~20k tokens

## Dependencies On
- M1P2-T1: Set up Python monorepo
- M1P2-T2: Create dyscount-core package
- M1P2-T3: Create dyscount-api package

## Blocks
None

## Notes
Reference `specs/API_OPERATIONS.md` for full specification. This is the first real DynamoDB operation.
