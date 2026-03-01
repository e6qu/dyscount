# Task: Set Up Python Monorepo

## Phase
M1 Phase 2: Python Implementation - Control Plane

## Task ID
M1P2-T1

## Description
Set up the Python project structure using uv workspace for a monorepo with three packages: dyscount-core, dyscount-api, and dyscount-cli.

## Acceptance Criteria
- [ ] Root `pyproject.toml` configured for uv workspace
- [ ] `packages/dyscount-core/` package structure created
- [ ] `packages/dyscount-api/` package structure created
- [ ] `packages/dyscount-cli/` package structure created
- [ ] `uv.lock` generated
- [ ] ruff configuration in pyproject.toml
- [ ] pytest configuration in pyproject.toml
- [ ] All packages installable via `uv pip install`

## Directory Structure
```
python/
├── pyproject.toml              # Root workspace config
├── uv.lock                     # Dependency lock
├── packages/
│   ├── dyscount-core/
│   │   ├── pyproject.toml
│   │   └── src/dyscount_core/
│   │       └── __init__.py
│   ├── dyscount-api/
│   │   ├── pyproject.toml
│   │   └── src/dyscount_api/
│   │       └── __init__.py
│   └── dyscount-cli/
│       ├── pyproject.toml
│       └── src/dyscount_cli/
│           └── __init__.py
└── tests/
    ├── __init__.py
    └── conftest.py
```

## Dependencies

### dyscount-core
- pydantic
- pydantic-settings
- msgpack
- aiosqlite

### dyscount-api
- fastapi
- uvicorn[standard]
- structlog
- prometheus-client
- dyscount-core (local)

### dyscount-cli
- typer
- dyscount-core (local)

## Dev Dependencies (root)
- ruff
- ty
- pytest
- pytest-asyncio
- httpx

## Estimated Effort
~15k tokens

## Dependencies On
None (first task)

## Blocks
- M1P2-T2: Create dyscount-core package
- M1P2-T3: Create dyscount-api package
- M1P2-T4: Create dyscount-cli package

## Notes
Use uv workspace feature for monorepo management. Reference `specs/CONFIG.md` for configuration patterns.
