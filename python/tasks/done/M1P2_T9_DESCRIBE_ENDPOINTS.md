# Task: Implement DescribeEndpoints

## Phase
M1 Phase 2: Python Implementation - Control Plane

## Task ID
M1P2-T9

## Description
Implement the DescribeEndpoints DynamoDB operation.

## Acceptance Criteria
- [ ] DescribeEndpoints endpoint handler working
- [ ] Return service endpoint
- [ ] Cache endpoints for performance
- [ ] Unit tests
- [ ] E2E test with boto3

## Request/Response

### Request (DescribeEndpoints)
Empty request body or `{}`

### Response (DescribeEndpointsOutput)
```json
{
  "Endpoints": [
    {
      "Address": "localhost:8000",
      "CachePeriodInMinutes": 1440
    }
  ]
}
```

## Implementation Notes

1. Get host and port from config
2. Return endpoint address
3. CachePeriodInMinutes can be fixed (24 hours = 1440)
4. Simple operation - no database access needed

## Error Cases
None expected for this operation.

## Estimated Effort
~5k tokens

## Dependencies On
- M1P2-T1 through M1P2-T3: Setup tasks

## Blocks
None

## Notes
This is the simplest operation. It's used by SDKs to discover endpoints (mainly for global tables in real DynamoDB).
