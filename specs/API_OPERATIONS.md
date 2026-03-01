# DynamoDB API Operations Reference

This document provides a comprehensive reference of all Amazon DynamoDB API operations organized by category.

> **Source**: AWS DynamoDB API Reference  
> **Last Updated**: March 2026

---

## Table of Contents

1. [Common Request/Response Format](#common-requestresponse-format)
2. [Control Plane Operations (Table Operations)](#control-plane-operations-table-operations)
3. [Data Plane Operations (Item Operations)](#data-plane-operations-item-operations)
4. [Batch Operations](#batch-operations)
5. [Transaction Operations](#transaction-operations)
6. [Stream Operations](#stream-operations)
7. [Backup/Restore Operations](#backuprestore-operations)
8. [Import/Export Operations](#importexport-operations)
9. [Global Table Operations](#global-table-operations)
10. [Tagging Operations](#tagging-operations)
11. [Utility Operations](#utility-operations)
12. [PartiQL Operations](#partiql-operations)

---

## Common Request/Response Format

All DynamoDB API operations use:
- **HTTP Method**: POST
- **Protocol**: JSON over HTTP/HTTPS
- **Content-Type**: `application/x-amz-json-1.0`
- **Authentication**: AWS Signature Version 4
- **X-Amz-Target Header**: `DynamoDB_20120810.<OperationName>`

### Common Parameters

Most operations support these optional parameters:

| Parameter | Description |
|-----------|-------------|
| `ReturnConsumedCapacity` | `INDEXES` \| `TOTAL` \| `NONE` - Level of throughput consumption detail |
| `ReturnItemCollectionMetrics` | `SIZE` \| `NONE` - Whether to return item collection metrics |

### Common Response Elements

| Element | Description |
|---------|-------------|
| `ConsumedCapacity` | Throughput capacity consumed by the operation |

---

## Control Plane Operations (Table Operations)

### CreateTable
Creates a new DynamoDB table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.CreateTable` |

**Required Parameters:**
- `TableName` (String) - Name of the table (1-1024 chars)

**Optional Parameters:**
- `AttributeDefinitions` (Array) - Attributes describing key schema
- `KeySchema` (Array) - Primary key attributes (1-2 elements)
- `BillingMode` (String) - `PROVISIONED` (default) or `PAY_PER_REQUEST`
- `ProvisionedThroughput` (Object) - `{ ReadCapacityUnits: number, WriteCapacityUnits: number }`
- `GlobalSecondaryIndexes` (Array) - Up to 20 GSI definitions
- `LocalSecondaryIndexes` (Array) - Up to 5 LSI definitions
- `StreamSpecification` (Object) - Enable DynamoDB Streams
- `SSESpecification` (Object) - Server-side encryption settings
- `Tags` (Array) - Tags to assign to the table
- `TableClass` (String) - `STANDARD` or `STANDARD_INFREQUENT_ACCESS`
- `DeletionProtectionEnabled` (Boolean) - Protect from accidental deletion
- `OnDemandThroughput` (Object) - Max throughput for on-demand mode
- `WarmThroughput` (Object) - Pre-warm throughput settings
- `ResourcePolicy` (String) - Resource-based policy document

**Response Elements:**
- `TableDescription` (Object) - Complete table information including:
  - `TableName`, `TableArn`, `TableId`, `TableStatus`
  - `ItemCount`, `TableSizeBytes`
  - `KeySchema`, `AttributeDefinitions`
  - `ProvisionedThroughput`, `BillingModeSummary`
  - `GlobalSecondaryIndexes`, `LocalSecondaryIndexes`
  - `StreamSpecification`, `LatestStreamArn`
  - `SSEDescription`, `CreationDateTime`

---

### DescribeTable
Returns information about a table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DescribeTable` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table

**Optional Parameters:**
- None

**Response Elements:**
- `Table` (Object) - Complete table description (same structure as CreateTable response)

---

### UpdateTable
Modifies the provisioned throughput settings, global secondary indexes, or DynamoDB Streams settings for a given table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.UpdateTable` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table

**Optional Parameters:**
- `AttributeDefinitions` (Array) - New attribute definitions
- `BillingMode` (String) - Change billing mode
- `ProvisionedThroughput` (Object) - Update capacity units
- `GlobalSecondaryIndexUpdates` (Array) - Create, Update, or Delete GSIs
- `StreamSpecification` (Object) - Enable/disable streams
- `SSESpecification` (Object) - Update encryption
- `DeletionProtectionEnabled` (Boolean) - Toggle deletion protection
- `OnDemandThroughput` (Object) - Update on-demand limits
- `WarmThroughput` (Object) - Update warm throughput

**Response Elements:**
- `TableDescription` (Object) - Updated table information

---

### DeleteTable
Deletes a table and all of its items.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DeleteTable` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table

**Optional Parameters:**
- None

**Response Elements:**
- `TableDescription` (Object) - Information about the deleted table

---

### ListTables
Returns an array of table names associated with the current account and endpoint.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.ListTables` |

**Required Parameters:**
- None

**Optional Parameters:**
- `ExclusiveStartTableName` (String) - Start after this table (pagination)
- `Limit` (Number) - Maximum number of tables to return (1-100)

**Response Elements:**
- `TableNames` (Array) - List of table names
- `LastEvaluatedTableName` (String) - For pagination

---

### DescribeLimits
Returns the current provisioned-capacity limits for your AWS account in a region.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DescribeLimits` |

**Required Parameters:**
- None

**Optional Parameters:**
- None

**Response Elements:**
- `AccountMaxReadCapacityUnits` (Number)
- `AccountMaxWriteCapacityUnits` (Number)
- `TableMaxReadCapacityUnits` (Number)
- `TableMaxWriteCapacityUnits` (Number)

---

### DescribeTimeToLive
Gives a description of the Time to Live (TTL) status on the specified table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DescribeTimeToLive` |

**Required Parameters:**
- `TableName` (String) - Name of the table

**Optional Parameters:**
- None

**Response Elements:**
- `TimeToLiveDescription` (Object)
  - `AttributeName` (String) - TTL attribute name
  - `TimeToLiveStatus` (String) - `ENABLING`, `DISABLING`, `ENABLED`, `DISABLED`

---

### UpdateTimeToLive
Enables or disables TTL for the specified table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.UpdateTimeToLive` |

**Required Parameters:**
- `TableName` (String) - Name of the table
- `TimeToLiveSpecification` (Object)
  - `AttributeName` (String) - Attribute to use for TTL
  - `Enabled` (Boolean) - Enable or disable TTL

**Optional Parameters:**
- None

**Response Elements:**
- `TimeToLiveSpecification` (Object) - The updated TTL specification

---

### DescribeContinuousBackups
Checks the status of continuous backups and point in time recovery on the specified table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DescribeContinuousBackups` |

**Required Parameters:**
- `TableName` (String) - Name of the table

**Optional Parameters:**
- None

**Response Elements:**
- `ContinuousBackupsDescription` (Object)
  - `ContinuousBackupsStatus` (String) - `ENABLED` or `DISABLED`
  - `PointInTimeRecoveryDescription` (Object) - PITR status and settings

---

### UpdateContinuousBackups
Enables or disables point in time recovery for the specified table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.UpdateContinuousBackups` |

**Required Parameters:**
- `TableName` (String) - Name of the table
- `PointInTimeRecoverySpecification` (Object)
  - `PointInTimeRecoveryEnabled` (Boolean)
  - `RecoveryPeriodInDays` (Number) - 1-35 days

**Optional Parameters:**
- None

**Response Elements:**
- `ContinuousBackupsDescription` (Object) - Updated backup settings

---

### DescribeTableReplicaAutoScaling
Describes auto scaling settings across replicas of the global table at once.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DescribeTableReplicaAutoScaling` |

**Required Parameters:**
- `TableName` (String) - Name of the table

**Optional Parameters:**
- None

**Response Elements:**
- `TableAutoScalingDescription` (Object)
  - `TableName`, `TableStatus`
  - `Replicas` (Array) - Per-replica auto scaling settings

---

### UpdateTableReplicaAutoScaling
Updates auto scaling settings on your replica table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.UpdateTableReplicaAutoScaling` |

**Required Parameters:**
- `TableName` (String) - Name of the table

**Optional Parameters:**
- `GlobalSecondaryIndexUpdates` (Array) - GSI auto scaling updates
- `ProvisionedWriteCapacityAutoScalingUpdate` (Object)
- `ReplicaUpdates` (Array) - Replica-specific auto scaling updates

**Response Elements:**
- `TableAutoScalingDescription` (Object) - Updated auto scaling settings

---

### DescribeContributorInsights
Returns information about contributor insights for a table or global secondary index.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DescribeContributorInsights` |

**Required Parameters:**
- `TableName` (String) - Name of the table

**Optional Parameters:**
- `IndexName` (String) - Name of the GSI

**Response Elements:**
- `TableName`, `IndexName`
- `ContributorInsightsStatus` (String) - `ENABLED`, `DISABLED`, `ENABLING`, `DISABLING`
- `FailureException` (Object) - Error details if enabling failed
- `LastUpdateDateTime` (Number)

---

### UpdateContributorInsights
Enables or disables contributor insights for a table or global secondary index.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.UpdateContributorInsights` |

**Required Parameters:**
- `TableName` (String) - Name of the table
- `ContributorInsightsAction` (String) - `ENABLE` or `DISABLE`

**Optional Parameters:**
- `IndexName` (String) - Name of the GSI

**Response Elements:**
- `TableName`, `IndexName`
- `ContributorInsightsStatus` (String)

---

### ListContributorInsights
Returns a list of contributor insights for a table and all its global secondary indexes.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.ListContributorInsights` |

**Required Parameters:**
- `TableName` (String) - Name of the table

**Optional Parameters:**
- `NextToken` (String) - Pagination token
- `MaxResults` (Number) - Maximum results to return

**Response Elements:**
- `ContributorInsightsSummaries` (Array)
  - `TableName`, `IndexName`, `ContributorInsightsStatus`
- `NextToken` (String) - For pagination

---

## Data Plane Operations (Item Operations)

### GetItem
Retrieves a single item from a table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.GetItem` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table
- `Key` (Object) - Primary key of the item to retrieve
  - Format: `{ "<key>": { "S": "value" } }` (or other type descriptor)

**Optional Parameters:**
- `AttributesToGet` (Array) - Legacy: specific attributes to retrieve
- `ProjectionExpression` (String) - Expression defining attributes to retrieve
- `ExpressionAttributeNames` (Object) - Substitution tokens for attribute names
- `ConsistentRead` (Boolean) - `true` for strongly consistent read
- `ReturnConsumedCapacity` (String)

**Response Elements:**
- `Item` (Object) - The retrieved item (empty if not found)
- `ConsumedCapacity` (Object)

---

### PutItem
Creates a new item or replaces an old item with a new item.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.PutItem` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table
- `Item` (Object) - Complete item to write
  - Format: `{ "<attr>": { "<type>": "value" } }`
  - Must include primary key attributes

**Optional Parameters:**
- `Expected` (Object) - Legacy condition expression
- `ConditionExpression` (String) - Condition for the operation
- `ExpressionAttributeNames` (Object)
- `ExpressionAttributeValues` (Object)
- `ReturnValues` (String) - `NONE` (default), `ALL_OLD`, `UPDATED_OLD`, `ALL_NEW`, `UPDATED_NEW`
- `ReturnConsumedCapacity` (String)
- `ReturnItemCollectionMetrics` (String)
- `ConditionalOperator` (String) - Legacy: `AND` or `OR`

**Response Elements:**
- `Attributes` (Object) - Old/new values (if ReturnValues specified)
- `ConsumedCapacity` (Object)
- `ItemCollectionMetrics` (Object) - Item collection size info

---

### UpdateItem
Edits an existing item's attributes or adds a new item.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.UpdateItem` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table
- `Key` (Object) - Primary key of the item to update

**Optional Parameters:**
- `UpdateExpression` (String) - Expression defining updates
  - SET, REMOVE, ADD, DELETE actions
  - Example: `"SET #a = :val, #b = #b + :inc"`
- `ConditionExpression` (String) - Condition for the update
- `ExpressionAttributeNames` (Object) - Name substitutions (e.g., `{"#a": "Age"}`)
- `ExpressionAttributeValues` (Object) - Value substitutions (e.g., `{":val": {"N": "25"}}`)
- `ReturnValues` (String) - Which values to return
- `ReturnConsumedCapacity` (String)
- `ReturnItemCollectionMetrics` (String)

**Response Elements:**
- `Attributes` (Object) - Requested return values
- `ConsumedCapacity` (Object)
- `ItemCollectionMetrics` (Object)

---

### DeleteItem
Deletes a single item in a table by primary key.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DeleteItem` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table
- `Key` (Object) - Primary key of the item to delete

**Optional Parameters:**
- `ConditionExpression` (String) - Condition for deletion
- `ExpressionAttributeNames` (Object)
- `ExpressionAttributeValues` (Object)
- `ReturnValues` (String)
- `ReturnConsumedCapacity` (String)
- `ReturnItemCollectionMetrics` (String)

**Response Elements:**
- `Attributes` (Object) - Deleted item attributes (if ReturnValues specified)
- `ConsumedCapacity` (Object)
- `ItemCollectionMetrics` (Object)

---

### Query
Retrieves items using the primary key or a secondary index.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.Query` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table

**Optional Parameters:**
- `IndexName` (String) - GSI or LSI name to query
- `Select` (String) - `ALL_ATTRIBUTES`, `ALL_PROJECTED_ATTRIBUTES`, `SPECIFIC_ATTRIBUTES`, `COUNT`
- `AttributesToGet` (Array) - Legacy: attributes to retrieve
- `Limit` (Number) - Maximum items to evaluate
- `ConsistentRead` (Boolean) - Strongly consistent reads (not supported on GSIs)
- `KeyConditionExpression` (String) - Condition on partition/sort key
  - Example: `"pk = :pkval AND sk BETWEEN :start AND :end"`
- `FilterExpression` (String) - Filter applied after query
- `ProjectionExpression` (String) - Attributes to retrieve
- `ExpressionAttributeNames` (Object)
- `ExpressionAttributeValues` (Object)
- `ExclusiveStartKey` (Object) - Pagination key
- `ReturnConsumedCapacity` (String)
- `ScanIndexForward` (Boolean) - `true` for ascending (default), `false` for descending

**Response Elements:**
- `Items` (Array) - List of matching items
- `Count` (Number) - Number of items returned
- `ScannedCount` (Number) - Number of items evaluated
- `LastEvaluatedKey` (Object) - Pagination key for next request
- `ConsumedCapacity` (Object)

---

### Scan
Returns one or more items by accessing every item in a table or index.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.Scan` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table

**Optional Parameters:**
- `IndexName` (String) - GSI or LSI to scan
- `AttributesToGet` (Array) - Legacy
- `Limit` (Number) - Maximum items to evaluate
- `Select` (String) - What to return
- `ScanFilter` (Object) - Legacy filter
- `ConditionalOperator` (String) - Legacy: `AND` or `OR`
- `ExclusiveStartKey` (Object) - Pagination key
- `ReturnConsumedCapacity` (String)
- `TotalSegments` (Number) - For parallel scan (1-1000000)
- `Segment` (Number) - Segment number for this worker (0 to TotalSegments-1)
- `ProjectionExpression` (String)
- `FilterExpression` (String) - Filter applied after scan
- `ExpressionAttributeNames` (Object)
- `ExpressionAttributeValues` (Object)
- `ConsistentRead` (Boolean)

**Response Elements:**
- `Items` (Array) - List of matching items
- `Count` (Number) - Number of items returned (after filter)
- `ScannedCount` (Number) - Number of items evaluated (before filter)
- `LastEvaluatedKey` (Object) - Pagination key
- `ConsumedCapacity` (Object)

---

## Batch Operations

### BatchGetItem
Retrieves multiple items from one or more tables.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.BatchGetItem` |

**Required Parameters:**
- `RequestItems` (Object) - Map of table names to request specs
  ```json
  {
    "TableName": {
      "Keys": [{ "pk": {"S": "val"} }],
      "ProjectionExpression": "...",
      "ExpressionAttributeNames": {},
      "ConsistentRead": true
    }
  }
  ```

**Optional Parameters:**
- `ReturnConsumedCapacity` (String)

**Response Elements:**
- `Responses` (Object) - Map of table names to retrieved items
- `UnprocessedKeys` (Object) - Keys that weren't processed (throttling, limit)
- `ConsumedCapacity` (Object)

**Limits:**
- Up to 100 items per request
- Up to 16 MB total response size

---

### BatchWriteItem
Writes or deletes multiple items in one or more tables.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.BatchWriteItem` |

**Required Parameters:**
- `RequestItems` (Object) - Map of table names to write requests
  ```json
  {
    "TableName": [
      { "PutRequest": { "Item": { ... } } },
      { "DeleteRequest": { "Key": { ... } } }
    ]
  }
  ```

**Optional Parameters:**
- `ReturnConsumedCapacity` (String)
- `ReturnItemCollectionMetrics` (String)

**Response Elements:**
- `UnprocessedItems` (Object) - Items not processed
- `ItemCollectionMetrics` (Object)
- `ConsumedCapacity` (Object)

**Limits:**
- Up to 25 items per request
- Up to 16 MB total request size
- Up to 400 KB per individual item

---

## Transaction Operations

### TransactGetItems
Retrieves multiple items in an atomic, all-or-nothing operation.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.TransactGetItems` |

**Required Parameters:**
- `TransactItems` (Array) - Up to 100 Get operations
  ```json
  [
    {
      "Get": {
        "TableName": "...",
        "Key": { ... },
        "ProjectionExpression": "...",
        "ExpressionAttributeNames": {}
      }
    }
  ]
  ```

**Optional Parameters:**
- `ReturnConsumedCapacity` (String)

**Response Elements:**
- `Responses` (Array) - Retrieved items in request order
- `ConsumedCapacity` (Object)

**Limits:**
- Up to 100 items per transaction
- Up to 4 MB total items size
- Items must be in same AWS account and Region

---

### TransactWriteItems
Writes multiple items in an atomic, all-or-nothing operation.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.TransactWriteItems` |

**Required Parameters:**
- `TransactItems` (Array) - Up to 100 actions
  ```json
  [
    { "ConditionCheck": { "TableName": "...", "Key": {}, "ConditionExpression": "..." } },
    { "Put": { "TableName": "...", "Item": {} } },
    { "Update": { "TableName": "...", "Key": {}, "UpdateExpression": "..." } },
    { "Delete": { "TableName": "...", "Key": {} } }
  ]
  ```

**Optional Parameters:**
- `ClientRequestToken` (String) - Idempotency token (1-36 chars, valid 10 minutes)
- `ReturnConsumedCapacity` (String)
- `ReturnItemCollectionMetrics` (String)

**Response Elements:**
- `ConsumedCapacity` (Array)
- `ItemCollectionMetrics` (Object)

**Limits:**
- Up to 100 actions per transaction
- Up to 4 MB total items size
- No two actions can target the same item
- Items must be in same AWS account and Region

---

## Stream Operations

### ListStreams
Returns an array of stream ARNs.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDBStreams_20120810.ListStreams` |

**Required Parameters:**
- None

**Optional Parameters:**
- `TableName` (String) - Only return streams for this table
- `ExclusiveStartStreamArn` (String) - Pagination token
- `Limit` (Number) - Maximum streams to return (1-100)

**Response Elements:**
- `Streams` (Array)
  - `StreamArn` (String)
  - `TableName` (String)
  - `StreamLabel` (String)
- `LastEvaluatedStreamArn` (String) - For pagination

---

### DescribeStream
Returns information about a stream.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDBStreams_20120810.DescribeStream` |

**Required Parameters:**
- `StreamArn` (String) - ARN of the stream

**Optional Parameters:**
- `ExclusiveStartShardId` (String) - Pagination token
- `Limit` (Number) - Maximum shards to return
- `ShardFilter` (Object) - Filter shards by type or ID

**Response Elements:**
- `StreamDescription` (Object)
  - `StreamArn`, `StreamLabel`, `StreamStatus`
  - `StreamViewType` - `NEW_IMAGE`, `OLD_IMAGE`, `NEW_AND_OLD_IMAGES`, `KEYS_ONLY`
  - `CreationRequestDateTime` (Number)
  - `TableName` (String)
  - `KeySchema` (Array)
  - `Shards` (Array) - Shard information with sequence number ranges
  - `LastEvaluatedShardId` (String) - For pagination

---

### GetShardIterator
Returns a shard iterator for retrieving stream records.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDBStreams_20120810.GetShardIterator` |

**Required Parameters:**
- `StreamArn` (String) - ARN of the stream
- `ShardId` (String) - ID of the shard
- `ShardIteratorType` (String) - `TRIM_HORIZON`, `LATEST`, `AT_SEQUENCE_NUMBER`, `AFTER_SEQUENCE_NUMBER`

**Optional Parameters:**
- `SequenceNumber` (String) - Required for `AT_SEQUENCE_NUMBER` or `AFTER_SEQUENCE_NUMBER`

**Response Elements:**
- `ShardIterator` (String) - Iterator for GetRecords

---

### GetRecords
Retrieves stream records using a shard iterator.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDBStreams_20120810.GetRecords` |

**Required Parameters:**
- `ShardIterator` (String) - Iterator from GetShardIterator

**Optional Parameters:**
- `Limit` (Number) - Maximum records to return (1-1000)

**Response Elements:**
- `Records` (Array) - Stream records
  - `eventID` (String)
  - `eventName` (String) - `INSERT`, `MODIFY`, `REMOVE`
  - `eventVersion` (String)
  - `eventSource` (String)
  - `awsRegion` (String)
  - `dynamodb` (Object)
    - `ApproximateCreationDateTime` (Number)
    - `Keys` (Object) - Primary key
    - `NewImage` (Object) - New item image (if view type includes it)
    - `OldImage` (Object) - Old item image (if view type includes it)
    - `SequenceNumber` (String)
    - `SizeBytes` (Number)
    - `StreamViewType` (String)
- `NextShardIterator` (String) - For continuous reading
- `MillisBehindLatest` (Number) - Lag time in milliseconds

---

## Backup/Restore Operations

### CreateBackup
Creates a backup for an existing table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.CreateBackup` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table
- `BackupName` (String) - Name for the backup (3-255 chars)

**Optional Parameters:**
- None

**Response Elements:**
- `BackupDetails` (Object)
  - `BackupArn` (String)
  - `BackupName` (String)
  - `BackupStatus` (String) - `CREATING`, `DELETED`, `AVAILABLE`
  - `BackupType` (String) - `USER`, `SYSTEM`, `AWS_BACKUP`
  - `BackupCreationDateTime` (Number)
  - `BackupExpiryDateTime` (Number) - For automatic deletion
  - `BackupSizeBytes` (Number)

---

### DescribeBackup
Describes an existing backup.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DescribeBackup` |

**Required Parameters:**
- `BackupArn` (String) - ARN of the backup

**Optional Parameters:**
- None

**Response Elements:**
- `BackupDescription` (Object)
  - `BackupDetails` (Object) - Backup metadata
  - `SourceTableDetails` (Object) - Original table info
  - `SourceTableFeatureDetails` (Object) - GSI, LSI, stream settings

---

### DeleteBackup
Deletes an existing backup.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DeleteBackup` |

**Required Parameters:**
- `BackupArn` (String) - ARN of the backup

**Optional Parameters:**
- None

**Response Elements:**
- `BackupDescription` (Object) - Description of deleted backup

---

### ListBackups
Lists DynamoDB backups for the current account.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.ListBackups` |

**Required Parameters:**
- None

**Optional Parameters:**
- `TableName` (String) - Only list backups for this table
- `BackupType` (String) - `USER`, `SYSTEM`, `AWS_BACKUP`, `ALL`
- `ExclusiveStartBackupArn` (String) - Pagination token
- `Limit` (Number) - Maximum results (1-100)
- `TimeRangeLowerBound` (Number) - Inclusive start time
- `TimeRangeUpperBound` (Number) - Exclusive end time

**Response Elements:**
- `BackupSummaries` (Array)
  - `BackupArn`, `BackupName`, `BackupStatus`
  - `BackupType`, `BackupSizeBytes`
  - `BackupCreationDateTime`, `BackupExpiryDateTime`
  - `TableName`, `TableId`, `TableArn`
- `LastEvaluatedBackupArn` (String) - For pagination

---

### RestoreTableFromBackup
Restores a table from a backup.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.RestoreTableFromBackup` |

**Required Parameters:**
- `BackupArn` (String) - ARN of the backup
- `TargetTableName` (String) - Name for the restored table

**Optional Parameters:**
- `BillingModeOverride` (String) - Override billing mode
- `GlobalSecondaryIndexOverride` (Array) - Override GSI settings
- `LocalSecondaryIndexOverride` (Array) - Override LSI settings
- `ProvisionedThroughputOverride` (Object) - Override throughput
- `OnDemandThroughputOverride` (Object) - Override on-demand settings
- `SSESpecificationOverride` (Object) - Override encryption

**Response Elements:**
- `TableDescription` (Object) - Description of restored table

---

### RestoreTableToPointInTime
Restores a table to a point in time.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.RestoreTableToPointInTime` |

**Required Parameters (choose one):**
- `SourceTableArn` (String) - ARN of source table
- `SourceTableName` (String) - Name of source table
- `RecoveryTargetName` (String) - Name for the restored table

**Optional Parameters:**
- `UseLatestRestorableTime` (Boolean) - Use latest available time
- `RestoreDateTime` (Number) - Specific time to restore to
- `TargetTableName` (String) - Alias for RecoveryTargetName
- `BillingModeOverride` (String)
- `GlobalSecondaryIndexOverride` (Array)
- `LocalSecondaryIndexOverride` (Array)
- `ProvisionedThroughputOverride` (Object)
- `OnDemandThroughputOverride` (Object)
- `SSESpecificationOverride` (Object)

**Response Elements:**
- `TableDescription` (Object) - Description of restored table

---

## Import/Export Operations

### ImportTable
Imports table data from an S3 bucket.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.ImportTable` |

**Required Parameters:**
- `InputFormat` (String) - `DYNAMODB_JSON`, `ION`, or `CSV`
- `S3BucketSource` (Object)
  - `S3Bucket` (String) - Bucket name
  - `S3BucketOwner` (String) - Account ID (required for cross-account)
  - `S3KeyPrefix` (String) - Path prefix
- `TableCreationParameters` (Object)
  - `TableName` (String)
  - `AttributeDefinitions` (Array)
  - `KeySchema` (Array)
  - `BillingMode` (String)
  - `ProvisionedThroughput` (Object)
  - `OnDemandThroughput` (Object)
  - `GlobalSecondaryIndexes` (Array)
  - `SSESpecification` (Object)

**Optional Parameters:**
- `ClientToken` (String) - Idempotency token (valid 8 hours)
- `InputCompressionType` (String) - `GZIP`, `ZSTD`, or `NONE`
- `InputFormatOptions` (Object) - CSV-specific options
  - `Csv` (Object)
    - `Delimiter` (String)
    - `HeaderList` (Array)

**Response Elements:**
- `ImportTableDescription` (Object)
  - `ImportArn` (String)
  - `ImportStatus` (String) - `IN_PROGRESS`, `COMPLETED`, `CANCELLING`, `CANCELLED`, `FAILED`
  - `TableName`, `TableArn`, `TableId`
  - `S3BucketSource`, `InputFormat`, `InputCompressionType`
  - `StartTime`, `EndTime`
  - `ImportedItemCount`, `ProcessedItemCount`, `ErrorCount`
  - `ProcessedSizeBytes`, `FailureCode`, `FailureMessage`
  - `CloudWatchLogGroupArn`

---

### DescribeImport
Describes the status of an import.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DescribeImport` |

**Required Parameters:**
- `ImportArn` (String) - ARN of the import

**Optional Parameters:**
- None

**Response Elements:**
- `ImportTableDescription` (Object) - Same as ImportTable response

---

### ListImports
Lists completed and ongoing imports.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.ListImports` |

**Required Parameters:**
- None

**Optional Parameters:**
- `TableArn` (String) - Only list imports for this table
- `PageSize` (Number) - Results per page
- `NextToken` (String) - Pagination token

**Response Elements:**
- `ImportSummaryList` (Array)
  - `ImportArn`, `ImportStatus`
  - `TableArn`, `TableId`
  - `S3BucketSource`
  - `ImportType` - `INCREMENTAL` or `FULL`
- `NextToken` (String) - For pagination

---

### ExportTableToPointInTime
Exports table data to S3.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.ExportTableToPointInTime` |

**Required Parameters:**
- `TableArn` (String) - ARN of the table
- `S3Bucket` (String) - Destination S3 bucket

**Optional Parameters:**
- `ExportTime` (Number) - Point-in-time to export (must be within PITR window)
- `ClientToken` (String) - Idempotency token (valid 8 hours)
- `S3Prefix` (String) - Prefix for export files
- `S3BucketOwner` (String) - Account ID for cross-account exports
- `ExportFormat` (String) - `DYNAMODB_JSON` (default) or `ION`
- `ExportType` (String) - `FULL_EXPORT` (default) or `INCREMENTAL_EXPORT`
- `IncrementalExportSpecification` (Object) - Required for incremental
  - `ExportFromTime` (Number)
  - `ExportToTime` (Number)
  - `ExportViewType` (String) - `NEW_IMAGE` or `NEW_AND_OLD_IMAGES`
- `S3SseAlgorithm` (String) - `AES256` or `KMS`
- `S3SseKmsKeyId` (String) - KMS key ID for encryption

**Response Elements:**
- `ExportDescription` (Object)
  - `ExportArn` (String)
  - `ExportStatus` (String) - `IN_PROGRESS`, `COMPLETED`, `FAILED`, `CANCELLED`
  - `ExportType`, `ExportFormat`
  - `TableArn`, `TableId`
  - `S3Bucket`, `S3Prefix`, `S3BucketOwner`, `S3SseAlgorithm`, `S3SseKmsKeyId`
  - `ExportTime`, `StartTime`, `EndTime`
  - `ItemCount`, `BilledSizeBytes`, `ProcessedSizeBytes`
  - `ExportManifest` (String) - Manifest file location
  - `FailureCode`, `FailureMessage`
  - `IncrementalExportSpecification`

---

### DescribeExport
Describes an export.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DescribeExport` |

**Required Parameters:**
- `ExportArn` (String) - ARN of the export

**Optional Parameters:**
- None

**Response Elements:**
- `ExportDescription` (Object) - Same as ExportTableToPointInTime response

---

### ListExports
Lists completed and ongoing exports.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.ListExports` |

**Required Parameters:**
- None

**Optional Parameters:**
- `TableArn` (String) - Only list exports for this table
- `MaxResults` (Number) - Maximum results to return
- `NextToken` (String) - Pagination token

**Response Elements:**
- `ExportSummaries` (Array)
  - `ExportArn`, `ExportStatus`
  - `ExportType`, `ExportType`
- `NextToken` (String) - For pagination

---

## Global Table Operations

### CreateGlobalTable
Creates a global table from an existing table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.CreateGlobalTable` |

**Required Parameters:**
- `GlobalTableName` (String) - Name of the global table (3-255 chars)
- `ReplicationGroup` (Array) - Regions to replicate to
  - Each element: `{ "RegionName": "us-west-2" }`

**Optional Parameters:**
- None

**Response Elements:**
- `GlobalTableDescription` (Object)
  - `GlobalTableName`, `GlobalTableArn`, `GlobalTableStatus`
  - `CreationDateTime`
  - `ReplicationGroup` (Array) - Per-replica status
    - `RegionName`, `ReplicaStatus`, `ReplicaStatusDescription`
    - `ReplicaStatusPercentProgress`
    - `KMSMasterKeyId`
    - `ProvisionedThroughputOverride`
    - `OnDemandThroughputOverride`
    - `GlobalSecondaryIndexes` (Array)
    - `ReplicaInaccessibleDateTime`
    - `ReplicaTableClassSummary`

---

### UpdateGlobalTable
Adds or removes replicas in a global table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.UpdateGlobalTable` |

**Required Parameters:**
- `GlobalTableName` (String) - Name of the global table
- `ReplicaUpdates` (Array)
  - `{ "Create": { "RegionName": "..." } }` - Add replica
  - `{ "Delete": { "RegionName": "..." } }` - Remove replica
  - `{ "Update": { "RegionName": "...", ... } }` - Update replica

**Optional Parameters:**
- None

**Response Elements:**
- `GlobalTableDescription` (Object) - Updated global table info

---

### DescribeGlobalTable
Returns information about a global table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DescribeGlobalTable` |

**Required Parameters:**
- `GlobalTableName` (String) - Name of the global table

**Optional Parameters:**
- None

**Response Elements:**
- `GlobalTableDescription` (Object)

---

### ListGlobalTables
Returns a list of global tables.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.ListGlobalTables` |

**Required Parameters:**
- None

**Optional Parameters:**
- `ExclusiveStartGlobalTableName` (String) - Pagination token
- `Limit` (Number) - Maximum results (1-100)
- `RegionName` (String) - List tables with replica in this region

**Response Elements:**
- `GlobalTables` (Array)
  - `GlobalTableName`, `ReplicationGroup` (Array of regions)
- `LastEvaluatedGlobalTableName` (String) - For pagination

---

### UpdateGlobalTableSettings
Updates settings for a global table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.UpdateGlobalTableSettings` |

**Required Parameters:**
- `GlobalTableName` (String) - Name of the global table

**Optional Parameters:**
- `GlobalTableBillingMode` (String)
- `GlobalTableProvisionedWriteCapacityUnits` (Number)
- `GlobalTableProvisionedWriteCapacityAutoScalingSettingsUpdate` (Object)
- `GlobalTableGlobalSecondaryIndexSettingsUpdate` (Array)
- `ReplicaSettingsUpdate` (Array)

**Response Elements:**
- `GlobalTableName`
- `ReplicaSettings` (Array)

---

### DescribeGlobalTableSettings
Describes settings for a global table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DescribeGlobalTableSettings` |

**Required Parameters:**
- `GlobalTableName` (String) - Name of the global table

**Optional Parameters:**
- None

**Response Elements:**
- `GlobalTableName`
- `ReplicaSettings` (Array) - Per-replica settings

---

## Tagging Operations

### TagResource
Associates tags with a DynamoDB resource.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.TagResource` |

**Required Parameters:**
- `ResourceArn` (String) - ARN of the resource (table, index, or stream)
- `Tags` (Array) - Tags to add
  - Each element: `{ "Key": "...", "Value": "..." }`

**Optional Parameters:**
- None

**Response Elements:**
- Empty response (HTTP 200)

---

### UntagResource
Removes tags from a DynamoDB resource.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.UntagResource` |

**Required Parameters:**
- `ResourceArn` (String) - ARN of the resource
- `TagKeys` (Array) - Keys of tags to remove

**Optional Parameters:**
- None

**Response Elements:**
- Empty response (HTTP 200)

---

### ListTagsOfResource
Returns a list of tags associated with a resource.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.ListTagsOfResource` |

**Required Parameters:**
- `ResourceArn` (String) - ARN of the resource

**Optional Parameters:**
- `NextToken` (String) - Pagination token
- `Limit` (Number) - Maximum results

**Response Elements:**
- `Tags` (Array) - List of tags
  - Each element: `{ "Key": "...", "Value": "..." }`
- `NextToken` (String) - For pagination

---

## Utility Operations

### DescribeEndpoints
Returns the regional endpoint information.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DescribeEndpoints` |

**Required Parameters:**
- None

**Optional Parameters:**
- None

**Response Elements:**
- `Endpoints` (Array)
  - `Address` (String) - Endpoint hostname
  - `CachePeriodInMinutes` (Number) - How long to cache this endpoint

---

### PutResourcePolicy
Attaches a resource-based policy to a table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.PutResourcePolicy` |

**Required Parameters:**
- `ResourceArn` (String) - ARN of the table
- `Policy` (String) - JSON policy document (max 20 KB)

**Optional Parameters:**
- `ExpectedRevisionId` (String) - Conditional update

**Response Elements:**
- `RevisionId` (String) - Revision ID of the policy

---

### GetResourcePolicy
Retrieves the resource-based policy attached to a table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.GetResourcePolicy` |

**Required Parameters:**
- `ResourceArn` (String) - ARN of the table

**Optional Parameters:**
- None

**Response Elements:**
- `Policy` (String) - The policy document
- `RevisionId` (String)
- `CreationDateTime` (Number)
- `LastModifiedDateTime` (Number)

---

### DeleteResourcePolicy
Deletes a resource-based policy from a table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DeleteResourcePolicy` |

**Required Parameters:**
- `ResourceArn` (String) - ARN of the table

**Optional Parameters:**
- `ExpectedRevisionId` (String) - Conditional delete

**Response Elements:**
- Empty response (HTTP 200)

---

## PartiQL Operations

### ExecuteStatement
Executes a PartiQL statement.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.ExecuteStatement` |

**Required Parameters:**
- `Statement` (String) - PartiQL statement
  - `SELECT`, `INSERT`, `UPDATE`, `DELETE`

**Optional Parameters:**
- `Parameters` (Array) - Parameter values for parameterized queries
- `ConsistentRead` (Boolean)
- `NextToken` (String) - Pagination token
- `ReturnConsumedCapacity` (String)
- `Limit` (Number) - Maximum items to return

**Response Elements:**
- `Items` (Array) - Result items
- `NextToken` (String) - For pagination
- `ConsumedCapacity` (Object)

---

### BatchExecuteStatement
Executes multiple PartiQL statements in a batch.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.BatchExecuteStatement` |

**Required Parameters:**
- `Statements` (Array)
  ```json
  [
    {
      "Statement": "SELECT * FROM Table WHERE pk = ?",
      "Parameters": [{ "S": "value" }]
    }
  ]
  ```

**Optional Parameters:**
- `ReturnConsumedCapacity` (String)

**Response Elements:**
- `Responses` (Array) - Results for each statement
  - `Item` (Object) - For SELECT
  - `Error` (Object) - Error if statement failed
- `ConsumedCapacity` (Object)

**Limits:**
- Up to 25 statements per batch

---

### ExecuteTransaction
Executes multiple PartiQL statements as a transaction.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.ExecuteTransaction` |

**Required Parameters:**
- `TransactStatements` (Array)
  ```json
  [
    {
      "Statement": "UPDATE Table SET x = ? WHERE pk = ?",
      "Parameters": [{ "N": "1" }, { "S": "key" }]
    }
  ]
  ```

**Optional Parameters:**
- `ClientRequestToken` (String) - Idempotency token
- `ReturnConsumedCapacity` (String)

**Response Elements:**
- `Responses` (Array) - Results for each statement
- `ConsumedCapacity` (Array)

**Limits:**
- Up to 100 statements per transaction

---

## Kinesis Data Streams Integration

### EnableKinesisStreamingDestination
Enables Kinesis Data Streams for a table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.EnableKinesisStreamingDestination` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table
- `StreamArn` (String) - ARN of the Kinesis stream

**Optional Parameters:**
- None

**Response Elements:**
- `TableName`, `StreamArn`
- `DestinationStatus` (String) - `ENABLING`, `ACTIVE`, `DISABLED`, `DISABLING`

---

### DisableKinesisStreamingDestination
Disables Kinesis Data Streams for a table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DisableKinesisStreamingDestination` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table
- `StreamArn` (String) - ARN of the Kinesis stream

**Optional Parameters:**
- None

**Response Elements:**
- `TableName`, `StreamArn`, `DestinationStatus`

---

### DescribeKinesisStreamingDestination
Returns the status of Kinesis Data Streams for a table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.DescribeKinesisStreamingDestination` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table

**Optional Parameters:**
- None

**Response Elements:**
- `TableName`
- `KinesisDataStreamDestinations` (Array)
  - `StreamArn`, `DestinationStatus`, `DestinationStatusDescription`

---

### UpdateKinesisStreamingDestination
Updates the status of Kinesis Data Streams for a table.

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **X-Amz-Target** | `DynamoDB_20120810.UpdateKinesisStreamingDestination` |

**Required Parameters:**
- `TableName` (String) - Name or ARN of the table
- `StreamArn` (String) - ARN of the Kinesis stream
- `DestinationStatusUpdate` (String) - `ENABLE` or `DISABLE`

**Optional Parameters:**
- None

**Response Elements:**
- `DestinationStatus`, `TableName`, `StreamArn`

---

## Data Type Reference

### AttributeValue
DynamoDB uses type descriptors for all attribute values:

| Type | Format | Example |
|------|--------|---------|
| String | `{"S": "value"}` | `{"Name": {"S": "John"}}` |
| Number | `{"N": "123.45"}` | `{"Age": {"N": "25"}}` |
| Binary | `{"B": "base64encoded"}` | `{"Data": {"B": "dGVzdA=="}}` |
| Boolean | `{"BOOL": true}` | `{"Active": {"BOOL": true}}` |
| Null | `{"NULL": true}` | `{"Empty": {"NULL": true}}` |
| List | `{"L": [...]}` | `{"Tags": {"L": [{"S": "a"}]}}` |
| Map | `{"M": {...}}` | `{"Addr": {"M": {"City": {"S": "NYC"}}}}` |
| String Set | `{"SS": ["a", "b"]}` | `{"Tags": {"SS": ["red", "blue"]}}` |
| Number Set | `{"NS": ["1", "2"]}` | `{"Scores": {"NS": ["95", "87"]}}` |
| Binary Set | `{"BS": ["a==", "b=="]}` | `{"Data": {"BS": ["dGVzdA=="]}}` |

### Common Objects

**ProvisionedThroughput:**
```json
{
  "ReadCapacityUnits": 5,
  "WriteCapacityUnits": 5
}
```

**KeySchemaElement:**
```json
{
  "AttributeName": "UserId",
  "KeyType": "HASH"  // or "RANGE"
}
```

**AttributeDefinition:**
```json
{
  "AttributeName": "UserId",
  "AttributeType": "S"  // S, N, or B
}
```

**Projection:**
```json
{
  "ProjectionType": "INCLUDE",  // KEYS_ONLY, INCLUDE, ALL
  "NonKeyAttributes": ["attr1", "attr2"]
}
```

---

## Operation Summary by Category

| Category | Operations | Count |
|----------|------------|-------|
| Control Plane | CreateTable, DescribeTable, UpdateTable, DeleteTable, ListTables, DescribeLimits, DescribeTimeToLive, UpdateTimeToLive, DescribeContinuousBackups, UpdateContinuousBackups, DescribeTableReplicaAutoScaling, UpdateTableReplicaAutoScaling, DescribeContributorInsights, UpdateContributorInsights, ListContributorInsights | 15 |
| Data Plane | GetItem, PutItem, UpdateItem, DeleteItem, Query, Scan | 6 |
| Batch | BatchGetItem, BatchWriteItem | 2 |
| Transaction | TransactGetItems, TransactWriteItems | 2 |
| Stream | ListStreams, DescribeStream, GetShardIterator, GetRecords | 4 |
| Backup/Restore | CreateBackup, DescribeBackup, DeleteBackup, ListBackups, RestoreTableFromBackup, RestoreTableToPointInTime | 6 |
| Import/Export | ImportTable, DescribeImport, ListImports, ExportTableToPointInTime, DescribeExport, ListExports | 6 |
| Global Tables | CreateGlobalTable, UpdateGlobalTable, DescribeGlobalTable, ListGlobalTables, UpdateGlobalTableSettings, DescribeGlobalTableSettings | 6 |
| Tagging | TagResource, UntagResource, ListTagsOfResource | 3 |
| PartiQL | ExecuteStatement, BatchExecuteStatement, ExecuteTransaction | 3 |
| Kinesis | EnableKinesisStreamingDestination, DisableKinesisStreamingDestination, DescribeKinesisStreamingDestination, UpdateKinesisStreamingDestination | 4 |
| Utility | DescribeEndpoints, PutResourcePolicy, GetResourcePolicy, DeleteResourcePolicy | 4 |
| **Total** | | **61 operations** |

---

## References

- [AWS DynamoDB API Reference](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/)
- [DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/)
- [DynamoDB Streams API Reference](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_Operations_Amazon_DynamoDB_Streams.html)
