# Python Implementation - Next Steps

## Current Phase: M1 Phase 3 (Core Data Plane)

### Immediate Tasks (Priority Order)

1. **M1P3_T1: GetItem Operation**
   - Add GetItem models (request/response)
   - Implement storage.get_item()
   - Add API route handler
   - Write tests

2. **M1P3_T2: PutItem Operation**
   - Add PutItem models
   - Implement storage.put_item()
   - Support ReturnValues
   - Write tests

3. **M1P3_T3: DeleteItem Operation**
   - Add DeleteItem models
   - Implement storage.delete_item()
   - Support ReturnValues=ALL_OLD
   - Write tests

4. **M1P3_T5: Condition Expressions**
   - Create expression parser module
   - Implement comparison operators
   - Implement functions (attribute_exists, begins_with, etc.)
   - Write tests

5. **M1P3_T4: UpdateItem Operation**
   - Add UpdateItem models
   - Implement UpdateExpression parser (SET, REMOVE, ADD, DELETE)
   - Support list_append, if_not_exists
   - Write tests

6. **M1P3_T6: E2E Tests**
   - Create boto3-based E2E tests
   - Test all data operations
   - Add to CI pipeline

### Technical Decisions Needed

1. **Expression Parser**: Hand-written recursive descent vs PEG parser
2. **UpdateExpression**: Support all clauses initially or incrementally
3. **ReturnValues**: Implementation strategy for returning old/new values

### Notes

- CI/CD workflows are now in place (see .github/workflows/)
- Test isolation is handled via temp directories
- Follow existing patterns from control plane implementation
