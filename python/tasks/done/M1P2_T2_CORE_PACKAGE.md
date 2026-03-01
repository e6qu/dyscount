# Task: Create dyscount-core Package

## Phase
M1 Phase 2: Python Implementation - Control Plane

## Task ID
M1P2-T2

## Description
Implement the dyscount-core package containing shared models, storage backend, and configuration.

## Acceptance Criteria
- [ ] Pydantic models for DynamoDB types (AttributeValue, KeySchema, etc.)
- [ ] Table metadata models
- [ ] Configuration module with pydantic-settings
- [ ] SQLite backend foundation (connection management)
- [ ] All models validated against specs/DATA_TYPES.md
- [ ] Unit tests for models

## Files to Create

### Models (`src/dyscount_core/models/`)
- `__init__.py` - Export all models
- `attribute_value.py` - AttributeValue with all DynamoDB types
- `table.py` - Table, KeySchemaElement, AttributeDefinition
- `operations.py` - Request/response models for Control Plane

### Storage (`src/dyscount_core/storage/`)
- `__init__.py`
- `sqlite_backend.py` - SQLite connection manager
- `table_manager.py` - Table creation/deletion logic

### Config
- `config.py` - Pydantic settings from specs/CONFIG.md

## Key Models

### AttributeValue
```python
class AttributeValue(BaseModel):
    S: Optional[str] = None
    N: Optional[str] = None
    B: Optional[bytes] = None
    BOOL: Optional[bool] = None
    NULL: Optional[bool] = None
    M: Optional[Dict[str, "AttributeValue"]] = None
    L: Optional[List["AttributeValue"]] = None
    SS: Optional[Set[str]] = None
    NS: Optional[Set[str]] = None
    BS: Optional[Set[bytes]] = None
```

### CreateTableRequest/Response
From specs/API_OPERATIONS.md

## Estimated Effort
~25k tokens

## Dependencies On
- M1P2-T1: Set up Python monorepo

## Blocks
- M1P2-T3: Create dyscount-api package
- M1P2-T5: Implement CreateTable
- M1P2-T6: Implement DeleteTable
- M1P2-T7: Implement ListTables
- M1P2-T8: Implement DescribeTable

## Notes
This is the foundation package. All other packages depend on it. Follow specs/DATA_TYPES.md exactly for AttributeValue structure.
