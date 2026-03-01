# Definition of Done

## Overview

This document defines what "done" means for each type of work in the Dyscount project.

## Phase Completion Criteria

A phase is considered **Done** when ALL of the following are true:

### 1. Code Complete
- [ ] All planned operations/features implemented
- [ ] All code follows language-specific style guidelines (enforced by linters)
- [ ] No TODO comments left in code (unless explicitly marked as future work)
- [ ] All error cases handled according to `specs/ERROR_CODES.md`

### 2. Tests Pass
- [ ] Unit tests written for all new functionality (>80% coverage)
- [ ] All unit tests pass
- [ ] Integration tests pass (if applicable)
- [ ] E2E tests pass (if operations are testable via E2E framework)

### 3. Documentation Updated
- [ ] Inline code documentation (docstrings/comments) complete
- [ ] API documentation generated (OpenAPI/Swagger)
- [ ] README updated if new features added
- [ ] Changelog updated

### 4. Quality Checks Pass
- [ ] Linter checks pass (ruff, golangci-lint, clippy, etc.)
- [ ] Type checker passes (ty, go vet, rustc, etc.)
- [ ] Formatter run (consistent code style)
- [ ] No security vulnerabilities (cargo audit, safety check, etc.)

### 5. State Files Updated
- [ ] `STATUS.md` updated with phase completion status
- [ ] `WHAT_WE_DID.md` updated with completed work log
- [ ] `PLAN.md` updated if plans changed
- [ ] `DO_NEXT.md` updated with next priorities
- [ ] Task files moved to `tasks/done/`

## Task Completion Criteria

A task is considered **Done** when:

1. Implementation complete per task specification
2. Tests written and passing
3. Code reviewed (if applicable)
4. Task file moved to `tasks/done/`
5. Parent state files updated

## Operation Implementation Criteria

A DynamoDB API operation is **Done** when:

1. **Request/Response Handling**
   - Request validation matches DynamoDB spec
   - Response format matches DynamoDB spec
   - Proper error responses for invalid requests

2. **Functionality**
   - Core logic implemented per `specs/API_OPERATIONS.md`
   - Edge cases handled
   - Proper error handling

3. **Testing**
   - Unit tests for happy path
   - Unit tests for error cases
   - E2E test with boto3/AWS CLI

4. **Documentation**
   - Docstrings/comments explaining logic
   - Any deviations from spec documented

## Specification Completion Criteria

A specification document is **Done** when:

1. Covers all aspects of the topic
2. References official AWS documentation where applicable
3. Includes examples
4. Reviewed and approved

## Checklist Template

Use this template when marking a phase/task complete:

```markdown
## Phase X.Y: [Name] - DONE ✅

### Code Complete
- [x] All operations implemented (list them)
- [x] Style guidelines followed
- [x] No stray TODOs
- [x] Error handling complete

### Tests
- [x] Unit tests written (X tests)
- [x] All tests passing
- [x] E2E tests passing

### Documentation
- [x] Code documented
- [x] OpenAPI updated
- [x] README updated

### Quality
- [x] Linter passing
- [x] Type checker passing
- [x] Formatter run

### State Files
- [x] STATUS.md updated
- [x] WHAT_WE_DID.md updated
- [x] DO_NEXT.md updated
- [x] Task files moved to done/
```

## Sign-off

A phase requires sign-off from the user (or self-sign-off if user delegates) to be considered officially complete.
