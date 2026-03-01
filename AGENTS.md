# Dyscount Project - Agent Guidelines

## Project Overview

Dyscount is a DynamoDB-compatible API service implementation backed by SQLite, implemented in 4 languages: Python, Go, Rust, and Zig.

## State Management System

This project uses a **state file system** to maintain context across sessions and subagents. **CRITICAL**: The 4 state files must be updated after each phase/task.

### Root State Files (in project root)

| File | Purpose | When to Update |
|------|---------|----------------|
| `PLAN.md` | Overall project roadmap, milestones, phases | When plans change, phases added/removed |
| `STATUS.md` | Current status of each milestone/phase | At start and end of each phase/task |
| `WHAT_WE_DID.md` | Log of completed work with timestamps | After completing any work |
| `DO_NEXT.md` | Immediate next steps and priorities | After completing work, when priorities shift |

**⚠️ IMPORTANT**: After completing ANY phase or task, you MUST update all 4 state files.

### Per-Language State Files

Each language directory (`python/`, `go/`, `rust/`, `zig/`) has its own set:

| File | Purpose |
|------|---------|
| `{lang}/PLAN.md` | Language-specific roadmap |
| `{lang}/STATUS.md` | Current status for this implementation |
| `{lang}/WHAT_WE_DID.md` | Completed work for this language |
| `{lang}/DO_NEXT.md` | Next steps for this language |

### Task Files

- **Active tasks**: `tasks/TASK_NAME.md` or `{lang}/tasks/TASK_NAME.md`
- **Completed tasks**: **MUST** be moved to `tasks/done/` or `{lang}/tasks/done/`

## Workflow: State File Updates (REQUIRED)

### After Completing a Phase:

1. **Update STATUS.md**:
   - Mark phase as complete
   - Update progress percentages
   - Mark tasks as done

2. **Update WHAT_WE_DID.md**:
   - Add section with timestamp
   - List all completed work
   - Include metrics (lines of code, tests, etc.)

3. **Update PLAN.md** (if needed):
   - Mark phase as complete
   - Update any changed plans

4. **Update DO_NEXT.md**:
   - Clear completed items
   - Set next priorities
   - Update current phase info

5. **Move Task Files**:
   - Move `tasks/TASK_NAME.md` → `tasks/done/TASK_NAME.md`

### After Completing a Task:

1. **Update STATUS.md**: Mark task complete
2. **Update WHAT_WE_DID.md**: Log the completed task
3. **Move task file**: `tasks/TASK.md` → `tasks/done/TASK.md`
4. **Update DO_NEXT.md** if this task was a blocker

## Git Workflow (REQUIRED)

### Branch Protection Rules

The repository has branch protection on `main`:
- No force push allowed
- Linear history required
- Only merge via pull request
- Only squash and rebase merges allowed

### Phase Completion Git Workflow

**After completing each phase, you MUST:**

1. **Ensure local `main` is in sync with `origin/main`**:
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create a new branch for the phase**, rebased from `origin/main`:
   ```bash
   git checkout -b phase/M1-P2-python-control-plane origin/main
   # or
   git checkout main
   git pull origin main
   git checkout -b phase/M1-P2-python-control-plane
   ```

3. **Commit all changes**:
   ```bash
   git add .
   git commit -m "feat: M1 Phase 2 - Python Control Plane

   - Implement CreateTable, DeleteTable, ListTables, DescribeTable, DescribeEndpoints
   - Setup monorepo with uv
   - Add dyscount-core, dyscount-api, dyscount-cli packages
   - Add tests and Dockerfile"
   ```

4. **Push branch to origin**:
   ```bash
   git push -u origin phase/M1-P2-python-control-plane
   ```

5. **Create a GitHub Pull Request**:
   - Use `gh pr create` or GitHub web interface
   - Title format: `M1 Phase 2: Python Control Plane`
   - Include summary of changes
   - Reference any related issues

6. **Wait for PR review and merge**:
   - Address any review comments
   - PR will be squash-merged to maintain linear history
   - After merge, sync local main:
     ```bash
     git checkout main
     git pull origin main
     ```

### Branch Naming Convention

| Pattern | Use Case |
|---------|----------|
| `phase/M{X}-P{Y}-{description}` | Full phases |
| `feature/{description}` | Individual features |
| `fix/{description}` | Bug fixes |
| `docs/{description}` | Documentation updates |

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `chore`: Maintenance

## Agent Workflow

1. **Before starting work**: 
   - Read relevant state files to understand current context
   - Read `DEFINITION_OF_DONE.md` for completion criteria
   - Read `ACCEPTANCE_CRITERIA.md` for quality standards
   - Ensure local `main` is synced with `origin/main`
   - Create new branch from `origin/main`

2. **During work**: 
   - Update state files as progress is made
   - Create task files for discrete units of work
   - Make regular commits with descriptive messages

3. **After completing work**: 
   - **REQUIRED**: Update all 4 state files (STATUS, WHAT_WE_DID, PLAN, DO_NEXT)
   - **REQUIRED**: Move task files to `tasks/done/`
   - **REQUIRED**: Commit changes and create GitHub PR
   - Verify against `DEFINITION_OF_DONE.md`
   - Verify against `ACCEPTANCE_CRITERIA.md`

## Subagent Usage

- Language-specific work should use subagents spawned in that language's directory
- E.g., for Python work: spawn subagent in `python/` directory
- Subagents should read local state files before starting
- Subagents should update state files after completing work
- Subagents should follow Git workflow (commits, branch management)

## Project Structure

```
dyscount/
├── AGENTS.md              # This file
├── DEFINITION_OF_DONE.md  # Completion criteria
├── ACCEPTANCE_CRITERIA.md # Quality standards
├── PLAN.md                # Root project plan
├── STATUS.md              # Overall status
├── WHAT_WE_DID.md         # Completed work log
├── DO_NEXT.md             # Next priorities
├── specs/                 # API specifications
├── tasks/                 # Root-level tasks
│   └── done/              # Completed tasks
├── e2e/                   # End-to-end tests (shared)
├── python/                # Python implementation
│   ├── PLAN.md
│   ├── STATUS.md
│   ├── WHAT_WE_DID.md
│   ├── DO_NEXT.md
│   ├── tasks/
│   │   └── done/
│   ├── src/               # Source code
│   └── tests/             # Unit tests
├── go/                    # Go implementation
│   └── ... (same structure)
├── rust/                  # Rust implementation
│   └── ... (same structure)
└── zig/                   # Zig implementation
    └── ... (same structure)
```

## Work Hierarchy

```
Milestone
  └── Phase (~100k tokens budget)
        └── Task (discrete unit of work)
```

## Key Principles

1. **ALWAYS update the 4 state files** after completing work
2. **ALWAYS move task files** to `tasks/done/` when complete
3. **ALWAYS create a GitHub PR** after completing a phase
4. **ALWAYS sync local `main` with `origin/main`** before starting new work
5. **ALWAYS create new branches rebased from `origin/main`**
6. **Keep tasks small and focused** - should fit in ~100k tokens
7. **Specs are the source of truth** - implement against specs/
8. **E2E tests must pass** for all language implementations
9. **Document decisions** in state files when trade-offs are made
10. **Follow DEFINITION_OF_DONE.md** for completion criteria
11. **Meet ACCEPTANCE_CRITERIA.md** for quality standards

## DynamoDB API Target

- Protocol: JSON over HTTP (DynamoDB API format)
- Port: 8000 (DynamoDB Local compatible)
- Authentication: Accept dummy AWS credentials (like DynamoDB Local)
- Target SDKs: boto3, AWS CLI, AWS SDK for Go v2, AWS SDK for Rust, etc.
