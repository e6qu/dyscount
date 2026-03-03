# M4 Phase 2: Python Polish & Production Readiness

## Task ID
M4P2

## Description
Polish the Python implementation for v1.0 release. Focus on performance benchmarks, security hardening, complete documentation, and Docker distribution. Python is already feature-complete (87% API coverage); this phase makes it production-ready.

## Reference
See `PYTHON_PRODUCTION_READY.md` for the complete assessment confirming Python is production-ready with 53/61 operations.

## Acceptance Criteria
- [ ] Performance benchmarks documented
- [ ] Security audit completed
- [ ] Complete documentation (user guide, API reference, examples)
- [ ] Docker multi-arch builds
- [ ] E2E test suite passes with real AWS SDK
- [ ] Ready for v1.0 release

## Definition of Done
- [ ] All polish tasks complete
- [ ] Performance meets targets (< 10ms p99 for queries)
- [ ] Documentation is comprehensive
- [ ] Docker image published
- [ ] State files updated
- [ ] Task file moved to done/

---

## Tasks

### T1: Performance Benchmarks & Optimization
**Estimated Effort**: 2 days

**Goals**:
- Establish performance baselines
- Optimize SQLite queries
- Tune connection pooling
- Document performance characteristics

**Deliverables**:
- `benchmarks/` directory with benchmark scripts
- Performance report (latency at 1K, 100K, 1M items)
- SQLite optimization (indexes, WAL mode tuning)
- Connection pool tuning recommendations

**Success Criteria**:
- Query latency < 10ms p99 for tables up to 1M items
- PutItem latency < 5ms p99
- Scan rate > 10,000 items/second

---

### T2: Security Audit & Hardening
**Estimated Effort**: 2 days

**Goals**:
- Review all input validation
- Ensure safe file path handling
- Verify AWS SigV4 auth
- Check for SQL injection vectors

**Deliverables**:
- Security audit report
- Input validation improvements
- Path traversal prevention
- Auth verification fixes (if needed)

**Security Checklist**:
- [ ] Table name validation (prevent path traversal)
- [ ] Item size limits enforced (400KB)
- [ ] Expression length limits
- [ ] SQL injection prevention in SQLite queries
- [ ] Safe temporary file handling
- [ ] AWS SigV4 signature verification
- [ ] Rate limiting (optional)

---

### T3: Complete Documentation
**Estimated Effort**: 3 days

**Goals**:
- User guide for local development
- Complete API reference
- Configuration guide
- Docker usage examples
- Troubleshooting guide

**Deliverables**:
- `docs/user-guide.md` - Getting started, basic usage
- `docs/api-reference.md` - All 53 operations documented
- `docs/configuration.md` - Env vars, config file options
- `docs/docker.md` - Docker and Docker Compose examples
- `docs/examples/` - Code examples in Python, Node.js, Go
- `docs/troubleshooting.md` - Common issues and solutions

**Documentation Structure**:
```
docs/
├── README.md              # Documentation index
├── user-guide.md          # Getting started
├── api-reference.md       # Complete API docs
├── configuration.md       # Configuration options
├── docker.md              # Docker usage
├── examples/
│   ├── python/
│   ├── nodejs/
│   ├── go/
│   └── java/
└── troubleshooting.md
```

---

### T4: Docker Distribution
**Estimated Effort**: 1 day

**Goals**:
- Multi-architecture Docker builds (amd64, arm64)
- Docker Compose example
- Kubernetes manifests
- Health checks

**Deliverables**:
- Updated `Dockerfile` with multi-stage build
- `.dockerignore` optimization
- `docker-compose.yml` example
- Kubernetes deployment manifest
- Health check endpoint verification

**Docker Checklist**:
- [ ] Multi-arch build (docker buildx)
- [ ] Minimal image size (< 200MB)
- [ ] Non-root user
- [ ] Volume persistence
- [ ] Health check configured
- [ ] Proper signal handling (SIGTERM)

---

### T5: E2E Testing Suite
**Estimated Effort**: 2 days

**Goals**:
- Comprehensive E2E tests with real AWS SDK
- Integration with CI/CD
- Performance regression tests

**Deliverables**:
- `e2e/` test suite using boto3
- Tests for all 53 operations
- CI integration (GitHub Actions)
- Performance regression detection

**E2E Test Coverage**:
- [ ] All control plane operations
- [ ] All data plane operations
- [ ] Batch operations
- [ ] Transactions
- [ ] TTL functionality
- [ ] Backup/restore
- [ ] PartiQL queries
- [ ] Import/export

---

## Implementation Notes

### Performance Benchmark Setup

```python
# benchmarks/latency_test.py
"""Measure operation latency at different table sizes."""

import time
import statistics
from dyscount_core.services.table_service import TableService
from dyscount_core.services.item_service import ItemService

class LatencyBenchmark:
    def __init__(self, config):
        self.table_service = TableService(config)
        self.item_service = ItemService(config)
    
    async def benchmark_getitem(self, table_name, key, iterations=1000):
        """Measure GetItem latency."""
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await self.item_service.get_item(...)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        return {
            'p50': statistics.median(times),
            'p99': sorted(times)[int(len(times) * 0.99)],
            'mean': statistics.mean(times),
        }
```

### Security Audit Checklist

```python
# security/audit.py
"""Security audit checks."""

import re

class SecurityAuditor:
    def check_table_name_validation(self):
        """Ensure table names can't traverse directories."""
        dangerous_names = [
            '../../../etc/passwd',
            '..\\..\\windows\\system32',
            'table; DROP TABLE users; --',
        ]
        # Verify all are rejected
    
    def check_sql_injection(self):
        """Verify SQL injection prevention."""
        # Check all SQL queries use parameterized statements
```

### Documentation Template

```markdown
# User Guide

## Quick Start

```bash
# Using Docker
docker run -p 8000:8000 dyscount:latest

# Using Python
pip install dyscount
dyscount serve
```

## First Table

```python
import boto3

dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')

# Create table
table = dynamodb.create_table(
    TableName='Users',
    KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
    AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
    BillingMode='PAY_PER_REQUEST'
)

# Put item
table.put_item(Item={'id': '1', 'name': 'Alice'})

# Get item
response = table.get_item(Key={'id': '1'})
print(response['Item'])
```
```

---

## Status
🟡 **IN PROGRESS**

## Dependencies
- M4 Phase 1 complete (Import/Export)
- Gap analysis complete

## Notes
- Focus on Python only (not Go/Rust/Zig)
- Python is already feature-complete
- Goal is v1.0 release readiness
- MinIO is the model: one excellent implementation
