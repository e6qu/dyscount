# Python Implementation - Next Steps

## Current Phase: M1 Phase 3 (Core Data Plane)

### Completed ✅

**M1P3_T1: GetItem Operation** (PR #3 merged)
- GetItem models (GetItemRequest, GetItemResponse, ConsumedCapacity)
- storage.get_item() implementation
- ItemService.get_item() service method
- API route handler for GetItem
- 10 comprehensive tests

### Next Task 🟡

**M1P3_T2: PutItem Operation**

#### Implementation Checklist
- [ ] Add PutItem models (PutItemRequest, PutItemResponse)
- [ ] Implement storage.put_item() method in table_manager.py
- [ ] Add ItemService.put_item() service method
- [ ] Add API route handler for PutItem
- [ ] Support ReturnValues (NONE, ALL_OLD)
- [ ] Calculate ConsumedCapacity (1 WCU)
- [ ] Write comprehensive tests (>80% coverage)

#### Acceptance Criteria (from M1P3_T2_PUT_ITEM.md)
- [ ] PutItem creates new item
- [ ] PutItem replaces existing item with same key
- [ ] ReturnValues=ALL_OLD returns previous attributes
- [ ] ConsumedCapacity calculated correctly
- [ ] All error cases handled per ERROR_CODES.md

### Remaining Tasks

3. **M1P3_T3: DeleteItem Operation**
   - DeleteItem models
   - storage.delete_item()
   - ReturnValues=ALL_OLD support

4. **M1P3_T5: Condition Expressions**
   - Expression parser module
   - Comparison operators
   - Functions (attribute_exists, begins_with, etc.)

5. **M1P3_T4: UpdateItem Operation**
   - UpdateItem models
   - UpdateExpression parser (SET, REMOVE, ADD, DELETE)
   - list_append, if_not_exists support

6. **M1P3_T6: E2E Tests**
   - boto3-based E2E tests
   - Test all data operations

### Technical Decisions Needed

1. **Expression Parser**: Hand-written recursive descent vs PEG parser
2. **UpdateExpression**: Support all clauses initially or incrementally
3. **ReturnValues**: Implementation strategy for returning old/new values

### Notes

- CI/CD workflows are now in place (see .github/workflows/)
- Test isolation is handled via temp directories
- Follow existing patterns from control plane implementation
- Task file: `python/tasks/todo/M1P3_T2_PUT_ITEM.md`
