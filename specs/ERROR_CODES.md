# Dyscount Error Codes Specification

This document specifies all error codes returned by Dyscount, a DynamoDB-compatible API service. All error responses follow the AWS DynamoDB error format for SDK compatibility.

## Error Response Format

All error responses use the following JSON structure:

```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ErrorCode",
  "message": "Human-readable error description"
}
```

HTTP headers included in error responses:
- `x-amzn-RequestId`: Unique request identifier
- `Content-Type`: `application/x-amz-json-1.0`
- `Content-Length`: Response body length

---

## Error Code Reference

### HTTP 400 - Client Errors

#### ValidationException
- **HTTP Status Code**: `400`
- **Error Code**: `ValidationException`
- **Message Format**: Varies (e.g., "One or more parameter values were invalid", "Missing required parameter")
- **When to Use**:
  - Required parameters are missing
  - Parameter values are out of range
  - Data type mismatches
  - Invalid table names (must be 3-255 characters, alphanumeric plus underscore, hyphen, period)
  - Invalid key schema definitions
  - Invalid attribute definitions
  - Expression syntax errors
  - Attempting to enable a stream on a table that already has a stream
  - Attempting to disable a stream on a table that doesn't have a stream
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ValidationException",
  "message": "One or more parameter values were invalid: TableName must be at least 3 characters long"
}
```

#### ResourceNotFoundException
- **HTTP Status Code**: `400`
- **Error Code**: `ResourceNotFoundException`
- **Message Format**: `Requested resource not found: {resource_type}: {resource_name} not found`
- **When to Use**:
  - Table does not exist
  - Index does not exist on the specified table
  - Table is in `CREATING` state and not yet available
  - Stream does not exist
  - Backup does not exist
  - Resource ARN is invalid or references non-existent resource
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
  "message": "Requested resource not found: Table: Users not found"
}
```

#### ConditionalCheckFailedException
- **HTTP Status Code**: `400`
- **Error Code**: `ConditionalCheckFailedException`
- **Message Format**: `The conditional request failed`
- **When to Use**:
  - Condition expression evaluates to false
  - Attribute value in condition does not match expected value
  - Item does not exist when condition expects it to exist
  - Item exists when condition expects it not to exist
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ConditionalCheckFailedException",
  "message": "The conditional request failed"
}
```

#### ProvisionedThroughputExceededException
- **HTTP Status Code**: `400`
- **Error Code**: `ProvisionedThroughputExceededException`
- **Message Format**: `You exceeded your maximum allowed provisioned throughput for a table or for one or more global secondary indexes`
- **When to Use**:
  - Read/write operations exceed provisioned capacity
  - Global secondary index capacity exceeded
  - Hot partition causing throttling
  - Burst capacity depleted
- **Additional Fields**:
  - `ThrottlingReasons`: Array of reasons including resource ARN and limit type
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ProvisionedThroughputExceededException",
  "message": "You exceeded your maximum allowed provisioned throughput for a table or for one or more global secondary indexes"
}
```

#### ItemCollectionSizeLimitExceededException
- **HTTP Status Code**: `400`
- **Error Code**: `ItemCollectionSizeLimitExceededException`
- **Message Format**: `Collection size exceeded`
- **When to Use**:
  - Item collection (items with same partition key) exceeds 10 GB limit
  - Only applies to tables with local secondary indexes
  - Attempting to add/update item that would exceed the limit
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ItemCollectionSizeLimitExceededException",
  "message": "Collection size exceeded"
}
```

#### LimitExceededException
- **HTTP Status Code**: `400`
- **Error Code**: `LimitExceededException`
- **Message Format**: `Too many operations for a given subscriber`
- **When to Use**:
  - More than 500 simultaneous table operations (CREATE/DELETE/UPDATE)
  - More than 250 simultaneous operations when creating tables with indexes
  - More than 50 simultaneous import table operations
  - More than 2 processes reading from same streams shard
  - GetRecords called with limit > 1000
  - Account table quota (2,500) exceeded
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#LimitExceededException",
  "message": "Too many operations for a given subscriber"
}
```

#### ThrottlingException
- **HTTP Status Code**: `400`
- **Error Code**: `ThrottlingException`
- **Message Format**: `Rate of requests exceeds the allowed throughput`
- **When to Use**:
  - Control plane API operations too rapid
  - On-demand tables receiving requests too fast for auto-scaling
  - Hot keys/partitions causing request throttling
- **Additional Fields**:
  - `ThrottlingReasons`: Array of reasons with resource ARN and operation type
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ThrottlingException",
  "message": "Rate of requests exceeds the allowed throughput"
}
```

#### ResourceInUseException
- **HTTP Status Code**: `400`
- **Error Code**: `ResourceInUseException`
- **Message Format**: `The resource which you are attempting to change is in use`
- **When to Use**:
  - Attempting to create a table that already exists
  - Attempting to delete a table in `CREATING` state
  - Attempting to update a resource already being updated
  - Attempting to create an index that already exists
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ResourceInUseException",
  "message": "The resource which you are attempting to change is in use"
}
```

#### DuplicateItemException
- **HTTP Status Code**: `400`
- **Error Code**: `DuplicateItemException`
- **Message Format**: `Duplicate item found`
- **When to Use**:
  - Attempting to insert an item with the same primary key as an existing item
  - Used in specific transactional contexts where duplicates are not allowed
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#DuplicateItemException",
  "message": "Duplicate item found"
}
```

#### ExpiredIteratorException
- **HTTP Status Code**: `400`
- **Error Code**: `ExpiredIteratorException`
- **Message Format**: `The provided iterator exceeds the maximum age allowed`
- **When to Use**:
  - Shard iterator has expired (15 minutes after retrieval via GetShardIterator)
  - Iterator was not used within the validity period
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ExpiredIteratorException",
  "message": "The provided iterator exceeds the maximum age allowed"
}
```

#### TrimmedDataAccessException
- **HTTP Status Code**: `400`
- **Error Code**: `TrimmedDataAccessException`
- **Message Format**: `The data you are trying to access has been trimmed`
- **When to Use**:
  - Attempting to read stream records older than 24 hours
  - Shard iterator points to trimmed data
  - Records exceeded retention period and were removed
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#TrimmedDataAccessException",
  "message": "The data you are trying to access has been trimmed"
}
```

#### TransactionCanceledException
- **HTTP Status Code**: `400`
- **Error Code**: `TransactionCanceledException`
- **Message Format**: `Transaction cancelled, please refer cancellation reasons for specific reasons`
- **When to Use**:
  - Condition in transaction not met
  - Transaction references tables in different accounts/regions
  - Multiple actions target the same item in a transaction
  - Insufficient provisioned capacity for transaction
  - Item size exceeds 400 KB during transaction
  - Concurrent transaction conflict
  - Validation error during transaction
- **Additional Fields**:
  - `CancellationReasons`: Array of reasons for each item in the transaction
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#TransactionCanceledException",
  "message": "Transaction cancelled, please refer cancellation reasons for specific reasons",
  "CancellationReasons": [
    {
      "Code": "ConditionalCheckFailed",
      "Message": "The conditional request failed"
    }
  ]
}
```

#### TransactionInProgressException
- **HTTP Status Code**: `400`
- **Error Code**: `TransactionInProgressException`
- **Message Format**: `The transaction with the given request token is already in progress`
- **When to Use**:
  - Idempotent retry of a transaction still being processed
  - Client token matches an ongoing transaction
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#TransactionInProgressException",
  "message": "The transaction with the given request token is already in progress"
}
```

#### IdempotentParameterMismatchException
- **HTTP Status Code**: `400`
- **Error Code**: `IdempotentParameterMismatchException`
- **Message Format**: `The request was rejected because the idempotent token was already used with different parameters`
- **When to Use**:
  - Client token reused with different request parameters
  - Same ClientRequestToken but different payload in TransactWriteItems
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#IdempotentParameterMismatchException",
  "message": "The request was rejected because the idempotent token was already used with different parameters"
}
```

#### InvalidEndpointException
- **HTTP Status Code**: `400`
- **Error Code**: `InvalidEndpointException`
- **Message Format**: `The provided endpoint is invalid`
- **When to Use**:
  - Request sent to incorrect endpoint
  - Endpoint does not support the requested operation
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#InvalidEndpointException",
  "message": "The provided endpoint is invalid"
}
```

#### BackupInUseException
- **HTTP Status Code**: `400`
- **Error Code**: `BackupInUseException`
- **Message Format**: `The backup is already being used by another operation`
- **When to Use**:
  - Backup is currently being restored
  - Backup is being copied
  - Conflicting backup control plane operation in progress
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#BackupInUseException",
  "message": "The backup is already being used by another operation"
}
```

#### BackupNotFoundException
- **HTTP Status Code**: `400`
- **Error Code**: `BackupNotFoundException`
- **Message Format**: `Backup not found for the given BackupARN`
- **When to Use**:
  - Specified backup ARN does not exist
  - Backup was deleted
  - Invalid backup ARN format
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#BackupNotFoundException",
  "message": "Backup not found for the given BackupARN: arn:aws:dynamodb:us-east-1:123456789012:table/Users/backup/01234567890123-abcdef"
}
```

#### ContinuousBackupsUnavailableException
- **HTTP Status Code**: `400`
- **Error Code**: `ContinuousBackupsUnavailableException`
- **Message Format**: `Backups have not yet been enabled for this table`
- **When to Use**:
  - Attempting to restore table when continuous backups not enabled
  - Point-in-time recovery not available for the table
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ContinuousBackupsUnavailableException",
  "message": "Backups have not yet been enabled for this table"
}
```

#### ExportNotFoundException
- **HTTP Status Code**: `400`
- **Error Code**: `ExportNotFoundException`
- **Message Format**: `The specified export was not found`
- **When to Use**:
  - Export task with specified ID does not exist
  - Export was cancelled or failed
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ExportNotFoundException",
  "message": "The specified export was not found"
}
```

#### GlobalTableAlreadyExistsException
- **HTTP Status Code**: `400`
- **Error Code**: `GlobalTableAlreadyExistsException`
- **Message Format**: `The specified global table already exists`
- **When to Use**:
  - Attempting to create a global table that already exists
  - Table is already part of a global table
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#GlobalTableAlreadyExistsException",
  "message": "The specified global table already exists"
}
```

#### GlobalTableNotFoundException
- **HTTP Status Code**: `400`
- **Error Code**: `GlobalTableNotFoundException`
- **Message Format**: `The specified global table does not exist`
- **When to Use**:
  - Attempting to update or describe a global table that doesn't exist
  - Global table name not found
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#GlobalTableNotFoundException",
  "message": "The specified global table does not exist"
}
```

#### ImportNotFoundException
- **HTTP Status Code**: `400`
- **Error Code**: `ImportNotFoundException`
- **Message Format**: `The specified import was not found`
- **When to Use**:
  - Import task with specified ID does not exist
  - Import was cancelled or failed
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ImportNotFoundException",
  "message": "The specified import was not found"
}
```

#### IndexNotFoundException
- **HTTP Status Code**: `400`
- **Error Code**: `IndexNotFoundException`
- **Message Format**: `The operation tried to access a nonexistent index`
- **When to Use**:
  - Query or scan references a non-existent GSI or LSI
  - UpdateTable attempts to delete non-existent index
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#IndexNotFoundException",
  "message": "The operation tried to access a nonexistent index"
}
```

#### InvalidRestoreTimeException
- **HTTP Status Code**: `400`
- **Error Code**: `InvalidRestoreTimeException`
- **Message Format**: `An invalid restore time was specified`
- **When to Use**:
  - Restore time is before EarliestRestorableDateTime
  - Restore time is after LatestRestorableDateTime
  - Restore time is not within point-in-time recovery window
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#InvalidRestoreTimeException",
  "message": "An invalid restore time was specified. RestoreDateTime must be between EarliestRestorableDateTime and LatestRestorableDateTime"
}
```

#### PointInTimeRecoveryUnavailableException
- **HTTP Status Code**: `400`
- **Error Code**: `PointInTimeRecoveryUnavailableException`
- **Message Format**: `Point in time recovery has not yet been enabled for this source table`
- **When to Use**:
  - Attempting point-in-time restore on table without PITR enabled
  - PITR was disabled for the table
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#PointInTimeRecoveryUnavailableException",
  "message": "Point in time recovery has not yet been enabled for this source table"
}
```

#### ReplicaAlreadyExistsException
- **HTTP Status Code**: `400`
- **Error Code**: `ReplicaAlreadyExistsException`
- **Message Format**: `The specified replica is already part of the global table`
- **When to Use**:
  - Attempting to add a region that is already a replica
  - Table in target region is already part of global table
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ReplicaAlreadyExistsException",
  "message": "The specified replica is already part of the global table"
}
```

#### ReplicaNotFoundException
- **HTTP Status Code**: `400`
- **Error Code**: `ReplicaNotFoundException`
- **Message Format**: `The specified replica is no longer part of the global table`
- **When to Use**:
  - Attempting to update a replica that doesn't exist in the global table
  - Replica was removed from global table
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#ReplicaNotFoundException",
  "message": "The specified replica is no longer part of the global table"
}
```

#### TableAlreadyExistsException
- **HTTP Status Code**: `400`
- **Error Code**: `TableAlreadyExistsException`
- **Message Format**: `Table already exists: {table_name}`
- **When to Use**:
  - CreateTable with a table name that already exists
  - Table creation conflict
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#TableAlreadyExistsException",
  "message": "Table already exists: Users"
}
```

#### TableInUseException
- **HTTP Status Code**: `400`
- **Error Code**: `TableInUseException`
- **Message Format**: `Table is being created or deleted: {table_name}`
- **When to Use**:
  - Attempting operations on a table in `CREATING` or `DELETING` state
  - Table is undergoing creation/deletion process
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#TableInUseException",
  "message": "Table is being created or deleted: Users"
}
```

#### TableNotFoundException
- **HTTP Status Code**: `400`
- **Error Code**: `TableNotFoundException`
- **Message Format**: `Table not found: {table_name}`
- **When to Use**:
  - Specified table does not exist in the account/region
  - Table was deleted
  - Table name is misspelled
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#TableNotFoundException",
  "message": "Table not found: Users"
}
```

---

### HTTP 500 - Server Errors

#### InternalServerError
- **HTTP Status Code**: `500`
- **Error Code**: `InternalServerError`
- **Message Format**: `The server encountered an internal error trying to fulfill the request`
- **When to Use**:
  - Unexpected server-side errors
  - Database connection failures
  - Unhandled exceptions in request processing
  - Service temporarily unavailable
- **Retry Behavior**: Yes, with exponential backoff
- **Example Response**:
```json
{
  "__type": "com.amazonaws.dynamodb.v20120810#InternalServerError",
  "message": "The server encountered an internal error trying to fulfill the request"
}
```

---

## Common Error Scenarios and Mapping

### Table Operations

| Scenario | Error Code |
|----------|------------|
| Create table that already exists | `TableAlreadyExistsException` or `ResourceInUseException` |
| Delete table that doesn't exist | `ResourceNotFoundException` |
| Delete table in CREATING state | `ResourceInUseException` |
| Describe table that doesn't exist | `ResourceNotFoundException` |
| Update table that's in CREATING/DELETING | `ResourceInUseException` |
| Table name too short (< 3 chars) | `ValidationException` |
| Table name too long (> 255 chars) | `ValidationException` |
| Invalid table name characters | `ValidationException` |
| Missing required key schema | `ValidationException` |

### Item Operations

| Scenario | Error Code |
|----------|------------|
| PutItem to non-existent table | `ResourceNotFoundException` |
| GetItem from non-existent table | `ResourceNotFoundException` |
| UpdateItem with failed condition | `ConditionalCheckFailedException` |
| DeleteItem with failed condition | `ConditionalCheckFailedException` |
| Item size exceeds 400 KB | `ValidationException` |
| Attribute name empty or invalid | `ValidationException` |
| Invalid UpdateExpression | `ValidationException` |
| Invalid ConditionExpression | `ValidationException` |

### Query/Scan Operations

| Scenario | Error Code |
|----------|------------|
| Query on non-existent table | `ResourceNotFoundException` |
| Query on non-existent index | `IndexNotFoundException` |
| Invalid KeyConditionExpression | `ValidationException` |
| Invalid FilterExpression | `ValidationException` |
| ProjectionExpression references unknown attribute | `ValidationException` |

### Batch Operations

| Scenario | Error Code |
|----------|------------|
| BatchWriteItem with > 25 items | `ValidationException` |
| BatchGetItem with > 100 items | `ValidationException` |
| Individual item failure | Returns in `UnprocessedItems`/`UnprocessedKeys` |

### Transaction Operations

| Scenario | Error Code |
|----------|------------|
| TransactWriteItems with > 100 items | `ValidationException` |
| TransactWriteItems targeting same item twice | `ValidationException` |
| Transaction exceeds 4 MB | `ValidationException` |
| Condition check fails | `TransactionCanceledException` |
| Concurrent transaction conflict | `TransactionCanceledException` |
| Same token, different payload | `IdempotentParameterMismatchException` |
| Transaction still in progress | `TransactionInProgressException` |

### Stream Operations

| Scenario | Error Code |
|----------|------------|
| GetRecords with expired iterator (> 15 min) | `ExpiredIteratorException` |
| GetRecords with trimmed data (> 24 hours old) | `TrimmedDataAccessException` |
| GetRecords limit > 1000 | `LimitExceededException` |
| Multiple consumers on same shard | `LimitExceededException` |
| DescribeStream on non-existent stream | `ResourceNotFoundException` |

### Backup/Restore Operations

| Scenario | Error Code |
|----------|------------|
| Restore to time without PITR enabled | `PointInTimeRecoveryUnavailableException` |
| Restore time outside recovery window | `InvalidRestoreTimeException` |
| Backup not found | `BackupNotFoundException` |
| Backup in use | `BackupInUseException` |
| Continuous backups not enabled | `ContinuousBackupsUnavailableException` |

### Global Table Operations

| Scenario | Error Code |
|----------|------------|
| Create global table that already exists | `GlobalTableAlreadyExistsException` |
| Update non-existent global table | `GlobalTableNotFoundException` |
| Add existing replica | `ReplicaAlreadyExistsException` |
| Update non-existent replica | `ReplicaNotFoundException` |
| Table already in different global table | `ValidationException` |

### Throttling Scenarios

| Scenario | Error Code |
|----------|------------|
| Exceed provisioned RCUs/WCUs | `ProvisionedThroughputExceededException` |
| On-demand scaling can't keep up | `ThrottlingException` |
| Too many control plane operations | `ThrottlingException` |
| Account-level throughput limit | `LimitExceededException` |

---

## Retry Guidance

| Error Code | Retryable | Strategy |
|------------|-----------|----------|
| ValidationException | No | Fix request and retry |
| ResourceNotFoundException | No | Verify resource exists |
| ConditionalCheckFailedException | No | Review condition logic |
| ProvisionedThroughputExceededException | Yes | Exponential backoff |
| ItemCollectionSizeLimitExceededException | Yes | Exponential backoff |
| LimitExceededException | Yes | Exponential backoff |
| ThrottlingException | Yes | Exponential backoff |
| ResourceInUseException | No | Wait and retry |
| TransactionCanceledException | Conditional | Review cancellation reasons |
| TransactionInProgressException | Yes | Wait and retry after 5 seconds |
| InternalServerError | Yes | Exponential backoff |

---

## Implementation Notes

1. **Error Type Format**: The `__type` field must use the exact format `com.amazonaws.dynamodb.v20120810#ErrorCode` for AWS SDK compatibility.

2. **Request ID**: Always include `x-amzn-RequestId` header with a unique UUID for each request.

3. **Message Consistency**: While messages can vary, keeping them consistent with AWS DynamoDB helps SDK compatibility.

4. **Throttling Headers**: For throttling errors, include `Retry-After` header when possible.

5. **Cancellation Reasons**: TransactionCanceledException should include detailed cancellation reasons for each item.

6. **Validation Details**: ValidationException messages should be as specific as possible about what parameter failed validation.
