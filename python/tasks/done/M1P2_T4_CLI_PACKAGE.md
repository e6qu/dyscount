# Task: Create dyscount-cli Package

## Phase
M1 Phase 2: Python Implementation - Control Plane

## Task ID
M1P2-T4

## Description
Implement the dyscount-cli package with a Typer-based CLI for running and managing the server.

## Acceptance Criteria
- [ ] Typer CLI with subcommands
- [ ] `serve` command to start server
- [ ] `config` command to show/validate config
- [ ] `--version` flag
- [ ] `--config` flag to specify config file
- [ ] Proper help documentation

## Files to Create

- `src/dyscount_cli/__init__.py`
- `src/dyscount_cli/main.py` - CLI entry point
- `src/dyscount_cli/commands/__init__.py`
- `src/dyscount_cli/commands/serve.py` - Server command
- `src/dyscount_cli/commands/config.py` - Config command

## Commands

### serve
```bash
dyscount serve [--host HOST] [--port PORT] [--config CONFIG]
```

### config
```bash
dyscount config [validate|show] [--config CONFIG]
```

### version
```bash
dyscount --version
```

## Estimated Effort
~10k tokens

## Dependencies On
- M1P2-T1: Set up Python monorepo
- M1P2-T2: Create dyscount-core package
- M1P2-T3: Create dyscount-api package

## Blocks
None (can proceed in parallel with operation implementations)

## Notes
Keep it simple for now. The serve command should just import and run the FastAPI app via uvicorn.
