# Task: M1P3_T5 - Implement Condition Expressions

## Status

- [ ] Planned
- [ ] In Progress
- [ ] Code Review
- [ ] Done

## Description

Implement condition expression parsing and evaluation for conditional PutItem, DeleteItem, and UpdateItem operations.

## Requirements

### Condition Expression Syntax

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equal | `#a = :val` |
| `<>` | Not equal | `#a <> :val` |
| `<` | Less than | `#a < :val` |
| `<=` | Less than or equal | `#a <= :val` |
| `>` | Greater than | `#a > :val` |
| `>=` | Greater than or equal | `#a >= :val` |
| `BETWEEN` | Range check | `#a BETWEEN :x AND :y` |
| `IN` | Set membership | `#a IN (:x, :y)` |
| `attribute_exists` | Check attribute exists | `attribute_exists(#a)` |
| `attribute_not_exists` | Check attribute missing | `attribute_not_exists(#a)` |
| `begins_with` | String prefix check | `begins_with(#a, :prefix)` |
| `contains` | Check substring/element | `contains(#a, :val)` |
| `size` | Get attribute size | `size(#a) > :n` |
| `AND` | Logical AND | `cond1 AND cond2` |
| `OR` | Logical OR | `cond1 OR cond2` |
| `NOT` | Logical NOT | `NOT cond` |

### Functions

- `attribute_exists(path)` - Check if attribute exists
- `attribute_not_exists(path)` - Check if attribute doesn't exist
- `attribute_type(path, type)` - Check DynamoDB type
- `begins_with(path, substring)` - String prefix check
- `contains(path, operand)` - Substring or set membership
- `size(path)` - Return size of string/list/map/binary

## Implementation Steps

1. **Create expression module** `dyscount_core/expressions/`
   - `parser.py` - Parse expression string into AST
   - `evaluator.py` - Evaluate AST against item
   - `functions.py` - Built-in functions (attribute_exists, begins_with, etc.)

2. **Implement parser** supporting:
   - Comparison operators
   - Logical operators (AND, OR, NOT)
   - Functions with parentheses
   - Placeholders (#names, :values)

3. **Implement evaluator**:
   - Walk AST and evaluate against item
   - Handle AttributeValue types correctly
   - Type coercion for comparisons

4. **Add error handling**:
   - `ConditionalCheckFailedException`
   - `ValidationException` for syntax errors

5. **Add tests** in `tests/test_condition_expressions.py`
   - Each operator
   - Each function
   - Nested logical expressions
   - Error cases

## Acceptance Criteria

Per `DEFINITION_OF_DONE.md` and `ACCEPTANCE_CRITERIA.md`:

### Code Complete
- [ ] Condition expression parser implemented
- [ ] All comparison operators: =, <>, <, <=, >, >=
- [ ] Logical operators: AND, OR, NOT
- [ ] Range operator: BETWEEN
- [ ] Set operator: IN
- [ ] All functions:
  - attribute_exists, attribute_not_exists
  - attribute_type
  - begins_with
  - contains
  - size
- [ ] Error handling per `specs/ERROR_CODES.md`:
  - `ValidationException` - Syntax errors, undefined placeholders
  - `ConditionalCheckFailedException` - Condition evaluates to false
- [ ] Code follows style guidelines (ruff, ty)
- [ ] No TODO comments

### Testing
- [ ] Unit tests written (>80% coverage)
- [ ] All tests passing:
  - Each comparison operator
  - Each logical operator
  - Each function
  - Nested expressions (AND/OR combinations)
  - Placeholder resolution
  - Type coercion for comparisons
  - Syntax error cases
  - Undefined placeholder errors
- [ ] Integration tests with PutItem/DeleteItem/UpdateItem

### Documentation
- [ ] Docstrings for all public methods
- [ ] Expression grammar documented
- [ ] Inline comments for parser/evaluator logic

### Quality Checks
- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] `ty check` passes
- [ ] No security vulnerabilities

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Code reviewed
- [ ] Task file moved to `tasks/done/`
- [ ] Parent state files updated

## Dependencies

- AttributeValue model
- Can be developed in parallel with UpdateItem

## Estimated Effort

2 days
