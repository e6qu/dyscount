# Task: Complete Go M2 Phase 1 - GSI and UpdateExpression

## Task ID
GO-M2-P1-COMPLETE

## Description
Complete the remaining 2 operations from Go M2 Phase 1:
1. UpdateTable with Global Secondary Index (GSI) support
2. Complete UpdateExpression with ADD/DELETE/REMOVE operations

## Current State

**Go Implementation**: 20/61 operations (33%)
- Control Plane: 5 ops
- Data Plane: 15 ops (including batch + transactions)
- Expression parser: Condition + Filter (basic)
- UpdateExpression: SET only

## Target State

**Go Implementation**: 22/61 operations (36%)
- Add UpdateTable with GSI
- Complete UpdateExpression (SET/ADD/DELETE/REMOVE)

## Task 1: UpdateTable with GSI Support

### Requirements
- Add GlobalSecondaryIndex to existing tables
- Support Create, Update, Delete GSI operations
- Update table metadata
- Backfill existing items to GSI

### Implementation

#### New Types (models/table.go)
```go
type UpdateTableRequest struct {
    TableName              string
    AttributeDefinitions   []AttributeDefinition
    GlobalSecondaryIndexUpdates []GlobalSecondaryIndexUpdate
    ProvisionedThroughput  *ProvisionedThroughput
}

type GlobalSecondaryIndexUpdate struct {
    Create *CreateGlobalSecondaryIndexAction
    Update *UpdateGlobalSecondaryIndexAction
    Delete *DeleteGlobalSecondaryIndexAction
}
```

#### Storage Changes (storage/table_manager.go)
- Add UpdateTable method
- Add createGSI, updateGSI, deleteGSI helpers
- Add backfillItemsToGSI for existing data

#### Handler Changes (handlers/dynamodb.go)
- Add handleUpdateTable handler
- Route "UpdateTable" operation

## Task 2: Complete UpdateExpression

### Requirements
Support all DynamoDB UpdateExpression actions:
- SET: Set attribute values (✅ already done)
- ADD: Add numbers or add to sets
- DELETE: Remove from sets
- REMOVE: Remove attributes

### Implementation

#### Expression Parser Extension (expression/update.go)
```go
type UpdateAction struct {
    Action string // SET, ADD, DELETE, REMOVE
    Path   string
    Value  models.AttributeValue
}
```

#### Storage Changes (storage/item_manager.go)
- Extend applyUpdateExpression to handle all actions
- Add applyADD, applyDELETE, applyREMOVE helpers
- Handle set operations (SS, NS, BS)

### UpdateExpression Grammar
```
UpdateExpression ::= SET Action | ADD Action | DELETE Action | REMOVE Action
SET Action ::= "SET" Path "=" Value ("," Path "=" Value)*
ADD Action ::= "ADD" Path Value ("," Path Value)*
DELETE Action ::= "DELETE" Path Value ("," Path Value)*
REMOVE Action ::= "REMOVE" Path ("," Path)*
```

## Acceptance Criteria

- [ ] UpdateTable can add a GSI to existing table
- [ ] UpdateTable can update GSI provisioned throughput
- [ ] UpdateTable can delete a GSI
- [ ] Existing items are backfilled to new GSI
- [ ] UpdateExpression supports SET (already done)
- [ ] UpdateExpression supports ADD (numbers and sets)
- [ ] UpdateExpression supports DELETE (sets only)
- [ ] UpdateExpression supports REMOVE (attributes)
- [ ] All existing tests still pass
- [ ] New tests for GSI operations
- [ ] New tests for UpdateExpression actions

## Definition of Done

- [ ] Code complete with tests
- [ ] PR merged to main
- [ ] Task file moved to done/

## Estimated Effort

**3-4 days**
- UpdateTable GSI: 2 days
- UpdateExpression completion: 1-2 days
