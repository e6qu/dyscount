# Task: Implement DescribeTable

## Phase
M1 Phase 2: Python Implementation - Control Plane

## Task ID
M1P2-T8

## Description
Implement the DescribeTable DynamoDB operation.

## Acceptance Criteria
- [ ] DescribeTable endpoint handler working
- [ ] Read table metadata from SQLite
- [ ] Return complete TableDescription
- [ ] Proper error responses (ResourceNotFoundException)
- [ ] Unit tests
- [ ] E2E test with boto3

## Request/Response

### Request (DescribeTable)
```json
{
  "TableName": "string"
}
```

### Response (DescribeTableOutput)
```json
{
  "Table": {
    "TableName": "string",
    "TableStatus": "ACTIVE",
    "KeySchema": [...],
    "AttributeDefinitions": [...],
    "CreationDateTime": number,
    "ItemCount": number,
    "TableSizeBytes": number
  }
}
```

## Implementation Notes

1. Validate table name
2. Open SQLite database
3. Read from `__metadata` table:
   - table_name
   - key_schema
   - attribute_definitions
   - creation_date_time
   - table_status
4. Count items in `items` table for ItemCount
5. Calculate table size (or approximate)
6. Return Table description

## Error Cases
- ResourceNotFoundException - table doesn't exist

## Estimated Effort
~15k tokens

## Dependencies On
- M1P2-T1 through M1P2-T3: Setup tasks
- M1P2-T5: CreateTable (to create tables for testing)

## Blocks
None

## Notes
ItemCount and TableSizeBytes are approximate in DynamoDB. For SQLite, we can get exact counts.
