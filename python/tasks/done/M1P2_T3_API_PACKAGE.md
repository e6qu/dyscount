# Task: Create dyscount-api Package

## Phase
M1 Phase 2: Python Implementation - Control Plane

## Task ID
M1P2-T3

## Description
Implement the dyscount-api package with FastAPI HTTP server, request routing, and table operation handlers.

## Acceptance Criteria
- [ ] FastAPI app factory with lifespan management
- [ ] X-Amz-Target header routing
- [ ] JSON request/response handling
- [ ] Dependency injection for config
- [ ] Structured logging with structlog
- [ ] OpenAPI documentation available
- [ ] Uvicorn entry point working

## Files to Create

### Main
- `src/dyscount_api/__init__.py`
- `src/dyscount_api/main.py` - FastAPI app factory
- `src/dyscount_api/dependencies.py` - Request dependencies
- `src/dyscount_api/logging.py` - Structured logging setup

### Routes
- `src/dyscount_api/routes/__init__.py`
- `src/dyscount_api/routes/tables.py` - Table operation handlers (stubs)
- `src/dyscount_api/routes/middleware.py` - Logging middleware

### Tests
- `tests/test_api_basic.py` - Basic API tests

## Key Implementation

### App Factory
```python
def create_app(config: Config) -> FastAPI:
    app = FastAPI(title="Dyscount")
    # Setup logging, routes, middleware
    return app
```

### X-Amz-Target Routing
DynamoDB uses `X-Amz-Target` header with format `DynamoDB_20120810.<OperationName>`

Route based on this header to appropriate handler.

## Estimated Effort
~20k tokens

## Dependencies On
- M1P2-T1: Set up Python monorepo
- M1P2-T2: Create dyscount-core package

## Blocks
- M1P2-T5 through M1P2-T9: Table operation implementations

## Notes
Focus on the HTTP layer and routing. Business logic goes in separate functions that will be implemented in subsequent tasks.
