# Dyscount Project Plan

## Vision

A DynamoDB-compatible API service that runs locally, backed by SQLite, implemented in 4 languages (Python, Go, Rust, Zig). Must pass tests with official AWS SDKs and CLI tools.

**Target:** Full DynamoDB API compatibility (61 operations)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│              AWS SDK / CLI / boto3 / Other SDKs             │
│         (Signature V4 Auth, JSON over HTTP/HTTPS)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP (JSON protocol)
┌─────────────────────────────────────────────────────────────┐
│                      Dyscount Service                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Python    │  │     Go      │  │    Rust     │  Zig    │
│  │  (Reference)│  │             │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
│  Components: HTTP Server → Auth Layer → Request Router       │
│              ↓ Expression Parser → SQLite Backend            │
│              ↓ Index Manager → Metrics/Logging               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ SQLite (one file per table)
                    /data/<namespace>/<table_name>.db
```

## Key Design Decisions

| Aspect | Decision |
|--------|----------|
| **Storage** | One SQLite file per DynamoDB table |
| **Serialization** | MessagePack for item storage |
| **Auth** | AWS Signature V4 (configurable local mode) |
| **IAM** | AWS IAM-style policies |
| **Config** | JSON config file + env vars |
| **Metrics** | Prometheus endpoint |
| **Logging** | Structured JSON logs |
| **Default Region** | `eu-west-1` |
| **Default Namespace** | `default` |
| **Python Stack** | uv, ty, ruff, FastAPI, uvicorn, async |
| **Python Structure** | Monorepo with packages (core, api, cli) |
| **Go Stack** | Gin + gin-swagger (OpenAPI from code) |
| **Rust Stack** | Axum + utoipa (OpenAPI from code) |
| **Zig Stack** | TBD (async http + sqlite C bindings) |
| **Expression Parser** | Custom recursive descent parser |
| **LSP** | Standalone LSP server for DynamoDB expressions |
| **OpenAPI** | Generate from code, validate against AWS specs |
| **Testing** | Matrix testing (all 4 implementations in CI) |

## Milestones

### Milestone 1: Foundation & Core Operations
**Goal**: Core DynamoDB API operations working in all 4 languages
**Estimated Token Budget**: ~850k tokens across 10 phases

#### M1 Phase 1: Specifications & E2E Framework ✅
**Budget**: ~60k tokens
**Deliverables**:
- [x] `specs/API_OPERATIONS.md` - 61 DynamoDB operations documented
- [x] `specs/DATA_TYPES.md` - Type system & JSON protocol
- [x] `specs/SQLITE_SCHEMA.md` - Storage architecture
- [x] `specs/AUTH_IAM.md` - Authentication & IAM
- [x] `specs/CONFIG.md` - Configuration schema
- [x] `specs/METRICS.md` - Prometheus metrics spec
- [x] `specs/ERROR_CODES.md` - DynamoDB error responses
- [x] `specs/TREE_SITTER.md` - Expression grammar
- [x] `specs/LSP.md` - LSP server specification

**Operations Covered**: None (specification only)

#### M1 Phase 2: Python - HTTP Server & Control Plane ✅
**Budget**: ~145k tokens
**Status**: ✅ **COMPLETE** - 100%

**Deliverables**:
- Python monorepo with uv workspace
- dyscount-core, dyscount-api, dyscount-cli packages
- HTTP server with FastAPI
- Request routing based on X-Amz-Target header
- JSON request/response handling
- SQLite connection management

**Operations to Implement**:
| Category | Operations |
|----------|------------|
| Control Plane | CreateTable, DeleteTable, ListTables, DescribeTable |
| Utility | DescribeEndpoints |

**Total**: 5 operations

#### M1 Phase 3: Python - Core Data Plane ✅
**Budget**: ~90k tokens
**Status**: ✅ **COMPLETE** - 100%

**Deliverables**:
- Item serialization/deserialization (MessagePack)
- Primary key handling (partition key, sort key)
- Expression parsing foundation
- Error handling framework
- Condition expressions
- E2E tests with boto3

**Operations to Implement**:
| Category | Operations | Status |
|----------|------------|--------|
| Data Plane | GetItem | ✅ Complete |
| Data Plane | PutItem | ✅ Complete |
| Data Plane | DeleteItem | ✅ Complete |
| Data Plane | UpdateItem | ✅ Complete |
| Condition Expressions | For Put/Delete/Update | ✅ Complete |
| E2E Tests | boto3 integration | ✅ Complete |

**Total**: 4 operations + condition expressions + E2E tests (9 cumulative)

#### M1 Phase 4: Python - Query, Scan & Expressions 🟡
**Budget**: ~90k tokens
**Status**: 🟡 **STARTING**

**Deliverables**:
- Expression parser (KeyConditionExpression, FilterExpression)
- Query operation with key conditions
- Scan operation with filters
- ProjectionExpression support
- Pagination (Limit, ExclusiveStartKey)

**Operations to Implement**:
| Category | Operations |
|----------|------------|
| Data Plane | Query, Scan |

**Total**: 2 operations (11 cumulative)

#### M1 Phase 5: Python - Batch, Transactions & Indexes
**Budget**: ~90k tokens
**Deliverables**:
- Batch operations handling
- Transaction support
- LSI (Local Secondary Index) implementation
- GSI (Global Secondary Index) implementation
- Index maintenance on write operations

**Operations to Implement**:
| Category | Operations |
|----------|------------|
| Batch | BatchGetItem, BatchWriteItem |
| Transaction | TransactGetItems, TransactWriteItems |
| Control Plane | UpdateTable (for adding GSI) |

**Total**: 5 operations (16 cumulative)

#### M1 Phase 6: Python - Auth, IAM, Logging & Metrics
**Budget**: ~80k tokens
**Deliverables**:
- AWS Signature V4 verification
- IAM policy evaluation engine
- Local mode (bypass auth) support
- Structured JSON logging
- Prometheus metrics endpoint
- Configuration management

**Operations to Implement**:
| Category | Operations |
|----------|------------|
| Tagging | TagResource, UntagResource, ListTagsOfResource |
| Resource Policy | PutResourcePolicy, GetResourcePolicy, DeleteResourcePolicy |

**Total**: 6 operations (22 cumulative)

#### M1 Phase 7: Go Implementation
**Budget**: ~100k tokens
**Approach**: Port Python implementation to Go

**Libraries/Frameworks** (TBD):
- HTTP: stdlib net/http vs Gin/Echo
- SQLite: mattn/go-sqlite3
- MessagePack: msgpack/v5

**Implement all 22 operations from M1 Phases 2-6**

#### M1 Phase 8: Rust Implementation
**Budget**: ~100k tokens
**Approach**: Port to Rust

**Libraries/Frameworks** (TBD):
- HTTP: Axum/Actix-web
- SQLite: sqlx/rusqlite
- MessagePack: rmp-serde

**Implement all 22 operations from M1 Phases 2-6**

#### M1 Phase 9: Zig Implementation
**Budget**: ~100k tokens
**Approach**: Port to Zig

**Libraries/Frameworks** (TBD):
- HTTP: stdlib http (Zig 0.12+) or custom
- SQLite: C bindings
- MessagePack: Custom or existing library

**Implement all 22 operations from M1 Phases 2-6**

#### M1 Phase 10: E2E Testing & Validation
**Budget**: ~60k tokens
**Deliverables**:
- Comprehensive E2E test suite covering all 22 operations
- Performance benchmarks vs DynamoDB Local
- Documentation (API usage, deployment, configuration)
- CI/CD pipeline

**Test Coverage**:
- All implemented operations with boto3
- AWS CLI compatibility
- SDK compatibility (Go, Rust, JavaScript)
- Auth scenarios (valid/invalid signatures, IAM policies)
- Error handling validation

---

### Milestone 2: Advanced Operations
**Goal**: Full feature parity for remaining common operations

#### M2 Phase 1: TimeToLive & Continuous Backups
- DescribeTimeToLive, UpdateTimeToLive
- DescribeContinuousBackups, UpdateContinuousBackups

#### M2 Phase 2: Backup & Restore
- CreateBackup, DescribeBackup, DeleteBackup, ListBackups
- RestoreTableFromBackup, RestoreTableToPointInTime

#### M2 Phase 3: PartiQL Support
- ExecuteStatement (SELECT, INSERT, UPDATE, DELETE)
- BatchExecuteStatement
- ExecuteTransaction

#### M2 Phase 4: Advanced Features
- DescribeLimits
- DescribeContributorInsights, UpdateContributorInsights, ListContributorInsights
- DescribeTableReplicaAutoScaling, UpdateTableReplicaAutoScaling

---

### Milestone 3: Global Tables & Streams
**Goal**: Multi-region and event-driven capabilities

#### M3 Phase 1: Global Tables
- CreateGlobalTable, UpdateGlobalTable, DescribeGlobalTable
- ListGlobalTables, UpdateGlobalTableSettings, DescribeGlobalTableSettings

#### M3 Phase 2: DynamoDB Streams
- ListStreams, DescribeStream, GetShardIterator, GetRecords

#### M3 Phase 3: Kinesis Integration
- EnableKinesisStreamingDestination, DisableKinesisStreamingDestination
- DescribeKinesisStreamingDestination, UpdateKinesisStreamingDestination

---

### Milestone 4: Import/Export & Polish
**Goal**: Complete API coverage and production readiness

#### M4 Phase 1: Import/Export Operations
- ImportTable, DescribeImport, ListImports
- ExportTableToPointInTime, DescribeExport, ListExports

#### M4 Phase 2: Performance Optimization
- Query plan optimization
- Connection pooling improvements
- Caching layer (optional)

#### M4 Phase 3: Production Hardening
- Comprehensive error handling
- Rate limiting
- Resource quotas
- Documentation completion

---

## Language-Specific Roadmaps

Detailed implementation plans for each language:
- `python/PLAN.md` - Reference implementation
- `go/PLAN.md`
- `rust/PLAN.md`
- `zig/PLAN.md`

## Success Criteria

1. **API Coverage**: All 61 DynamoDB operations implemented
2. **Compatibility**: Passes E2E tests with boto3, AWS CLI, and official AWS SDKs
3. **Performance**: Within 2x of DynamoDB Local for single-node operations
4. **Reliability**: SQLite backend supports databases up to 10GB per table
5. **Observability**: Prometheus metrics + structured logging available
6. **Security**: AWS SigV4 auth with IAM policy support

## Progress Tracking

| Milestone | Phases | Status | Progress |
|-----------|--------|--------|----------|
| M1: Foundation | 10 | 🟡 In Progress | 80% |
| M2: Advanced | 4 | ⚪ Planned | 0% |
| M3: Global/Streams | 3 | ⚪ Planned | 0% |
| M4: Import/Export | 3 | ⚪ Planned | 0% |
| **Total** | **20** | | **40%** |

## API Operations Coverage

| Phase | New Ops | Cumulative | % of 61 |
|-------|---------|------------|---------|
| M1 P2 | 5 | 5 | 8% |
| M1 P3 | 4 | 9 | 15% |
| M1 P4 | 2 | 11 | 18% |
| M1 P5 | 5 | 16 | 26% |
| M1 P6 | 6 | 22 | 36% |
| M2-M4 | 39 | 61 | 100% |
