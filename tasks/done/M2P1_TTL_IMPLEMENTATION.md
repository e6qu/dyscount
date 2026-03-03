# M2 Phase 1: Time-to-Live (TTL) Implementation

## Task ID
M2P1

## Description
Implement DynamoDB Time-to-Live (TTL) feature to automatically expire and delete items after a specified timestamp.

## Acceptance Criteria
- [ ] UpdateTimeToLive operation to enable/disable TTL on tables
- [ ] DescribeTimeToLive operation to get TTL configuration
- [ ] Store TTL attribute name in table metadata
- [ ] Background process to scan and delete expired items
- [ ] Integration with PutItem and UpdateItem to set expiration
- [ ] Proper error handling for invalid TTL attributes
- [ ] Comprehensive test coverage

## Definition of Done
- [ ] All TTL tests passing
- [ ] Background cleanup process running efficiently
- [ ] Items expire correctly based on timestamp
- [ ] Documentation updated

## Tasks

### M2P1-T1: TTL Operations
**Estimated Effort**: 2 days

**Deliverables**:
- UpdateTimeToLive API endpoint
- DescribeTimeToLive API endpoint
- Table metadata storage for TTL configuration
- TTL attribute validation

### M2P1-T2: Expiration Management
**Estimated Effort**: 1.5 days

**Deliverables**:
- Background cleanup process
- Expired item detection
- Automatic deletion of expired items
- Metrics for TTL operations

## Implementation Notes

### TTL Architecture
```
┌─────────────────────────────────────────┐
│  Table Metadata (__table_metadata)      │
│  - ttl_attribute: String (e.g., "exp")  │
│  - ttl_enabled: Boolean                 │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  Items Table                            │
│  - pk, sk, data, created_at, updated_at │
│  - expiration_time: INTEGER (Unix ts)   │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  Background Cleaner                     │
│  - Runs every N minutes                 │
│  - Scans for expired items              │
│  - Deletes expired items in batches     │
└─────────────────────────────────────────┘
```

### TTL Workflow
1. User calls `UpdateTimeToLive` to enable TTL with attribute name
2. System stores TTL configuration in table metadata
3. When items are created/updated with TTL attribute, store expiration timestamp
4. Background process periodically scans and deletes expired items
5. User can call `DescribeTimeToLive` to check configuration

### API Operations

**UpdateTimeToLive**:
```json
{
  "TableName": "MyTable",
  "TimeToLiveSpecification": {
    "AttributeName": "exp",
    "Enabled": true
  }
}
```

**DescribeTimeToLive**:
```json
{
  "TableName": "MyTable"
}
```

Response:
```json
{
  "TimeToLiveDescription": {
    "AttributeName": "exp",
    "TimeToLiveStatus": "ENABLED"
  }
}
```

## Test Plan
- Test enabling/disabling TTL on tables
- Test setting TTL attribute on items
- Test automatic expiration
- Test background cleanup process
- Test edge cases (past dates, invalid attributes)

## Status
🟡 **IN PROGRESS**

## Dependencies
- M1 Complete (all control and data plane operations)

## Notes
- TTL typically has a 48-hour delay in real DynamoDB
- For local implementation, we can make it immediate or configurable
- Need to handle timezone correctly (always use Unix timestamp)
