# Dyscount Prometheus Metrics Specification

This document defines the Prometheus-compatible metrics for Dyscount, a DynamoDB-compatible API service backed by SQLite.

## Overview

Dyscount exposes metrics in Prometheus exposition format at the `/metrics` endpoint (default port: 9090). All custom metrics use the `dyscount_` prefix to avoid collisions.

## Metric Naming Conventions

Following [Prometheus best practices](https://prometheus.io/docs/practices/naming/):

1. **Prefix**: All Dyscount-specific metrics use `dyscount_` prefix
2. **Units**: Base units only (seconds, bytes, ratio) - no milliseconds, kilobytes, etc.
3. **Suffixes**:
   - `_total` for accumulating counters (e.g., `dyscount_requests_total`)
   - `_seconds` for durations (e.g., `dyscount_operation_duration_seconds`)
   - `_bytes` for sizes (e.g., `dyscount_response_size_bytes`)
   - `_ratio` for percentages (0-1 range)
4. **Labels**: Used for dimensions, not metric names (e.g., `operation="GetItem"` not `dyscount_getitem_duration`)

## Label Guidelines

### Standard Labels (used across multiple metrics)

| Label | Description | Example Values |
|-------|-------------|----------------|
| `operation` | DynamoDB operation name | `GetItem`, `PutItem`, `Query`, `Scan`, `UpdateItem`, `DeleteItem`, `BatchGetItem`, `BatchWriteItem`, `TransactGetItems`, `TransactWriteItems`, `CreateTable`, `DeleteTable`, `ListTables`, `DescribeTable` |
| `table` | Table name | `users`, `orders`, `products` |
| `index` | Global secondary index name (for index operations) | `email-index`, `status-index` |
| `status_code` | HTTP status code | `200`, `400`, `404`, `500` |
| `error_type` | Error classification | `ValidationException`, `ResourceNotFoundException`, `ProvisionedThroughputExceededException`, `InternalServerError` |
| `throttle_type` | Type of throttling | `Read`, `Write`, `AccountLimit` |
| `endpoint` | API endpoint path | `/`, `/tables/{name}`, `/tables/{name}/items` |
| `method` | HTTP method | `GET`, `POST`, `PUT`, `DELETE` |

### Cardinality Warnings

⚠️ **IMPORTANT**: Avoid high-cardinality labels:
- ❌ DO NOT use: user IDs, session IDs, request IDs, item keys, timestamps
- ✅ DO use: bounded sets like operation types, status codes, error types, table names

## Metrics Endpoint

```
GET /metrics
Content-Type: text/plain; version=0.0.4
```

### Configuration

```yaml
# config.yaml
metrics:
  enabled: true
  bind_address: "0.0.0.0:9090"
  path: "/metrics"
  # Optional: authentication
  basic_auth:
    username: "prometheus"
    password: "${METRICS_PASSWORD}"
```

---

## 1. Standard HTTP Metrics

### Request Duration Histogram

```prometheus
# HELP dyscount_http_request_duration_seconds HTTP request latency distribution
# TYPE dyscount_http_request_duration_seconds histogram
dyscount_http_request_duration_seconds_bucket{method="POST",endpoint="/",status_code="200",le="0.005"} 1024
dyscount_http_request_duration_seconds_bucket{method="POST",endpoint="/",status_code="200",le="0.01"} 2048
dyscount_http_request_duration_seconds_bucket{method="POST",endpoint="/",status_code="200",le="0.025"} 4096
dyscount_http_request_duration_seconds_bucket{method="POST",endpoint="/",status_code="200",le="0.05"} 8192
dyscount_http_request_duration_seconds_bucket{method="POST",endpoint="/",status_code="200",le="0.1"} 9500
dyscount_http_request_duration_seconds_bucket{method="POST",endpoint="/",status_code="200",le="0.25"} 9900
dyscount_http_request_duration_seconds_bucket{method="POST",endpoint="/",status_code="200",le="0.5"} 9950
dyscount_http_request_duration_seconds_bucket{method="POST",endpoint="/",status_code="200",le="1"} 9980
dyscount_http_request_duration_seconds_bucket{method="POST",endpoint="/",status_code="200",le="2.5"} 9995
dyscount_http_request_duration_seconds_bucket{method="POST",endpoint="/",status_code="200",le="5"} 9999
dyscount_http_request_duration_seconds_bucket{method="POST",endpoint="/",status_code="200",le="10"} 10000
dyscount_http_request_duration_seconds_bucket{method="POST",endpoint="/",status_code="200",le="+Inf"} 10000
dyscount_http_request_duration_seconds_sum{method="POST",endpoint="/",status_code="200"} 450.5
dyscount_http_request_duration_seconds_count{method="POST",endpoint="/",status_code="200"} 10000
```

**Buckets**: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10 seconds

### Request Count

```prometheus
# HELP dyscount_http_requests_total Total HTTP requests received
# TYPE dyscount_http_requests_total counter
dyscount_http_requests_total{method="POST",endpoint="/",status_code="200"} 10000
dyscount_http_requests_total{method="POST",endpoint="/",status_code="400"} 150
dyscount_http_requests_total{method="POST",endpoint="/",status_code="500"} 5
```

**Labels**: `method`, `endpoint`, `status_code`

### Request Size

```prometheus
# HELP dyscount_http_request_size_bytes HTTP request body size distribution
# TYPE dyscount_http_request_size_bytes histogram
dyscount_http_request_size_bytes_bucket{method="POST",endpoint="/",le="1024"} 5000
dyscount_http_request_size_bytes_bucket{method="POST",endpoint="/",le="4096"} 8500
dyscount_http_request_size_bytes_bucket{method="POST",endpoint="/",le="16384"} 9800
dyscount_http_request_size_bytes_bucket{method="POST",endpoint="/",le="65536"} 9990
dyscount_http_request_size_bytes_bucket{method="POST",endpoint="/",le="262144"} 9999
dyscount_http_request_size_bytes_bucket{method="POST",endpoint="/",le="1.048576e+06"} 10000
dyscount_http_request_size_bytes_bucket{method="POST",endpoint="/",le="+Inf"} 10000
dyscount_http_request_size_bytes_sum{method="POST",endpoint="/"} 52428800
dyscount_http_request_size_bytes_count{method="POST",endpoint="/"} 10000
```

**Buckets**: 1KB, 4KB, 16KB, 64KB, 256KB, 1MB, 4MB (DynamoDB item limit ~400KB)

### Response Size

```prometheus
# HELP dyscount_http_response_size_bytes HTTP response body size distribution
# TYPE dyscount_http_response_size_bytes histogram
dyscount_http_response_size_bytes_bucket{method="POST",endpoint="/",status_code="200",le="1024"} 3000
dyscount_http_response_size_bytes_bucket{method="POST",endpoint="/",status_code="200",le="4096"} 7000
dyscount_http_response_size_bytes_bucket{method="POST",endpoint="/",status_code="200",le="16384"} 9500
dyscount_http_response_size_bytes_bucket{method="POST",endpoint="/",status_code="200",le="65536"} 9950
dyscount_http_response_size_bytes_bucket{method="POST",endpoint="/",status_code="200",le="+Inf"} 10000
dyscount_http_response_size_bytes_sum{method="POST",endpoint="/",status_code="200"} 104857600
dyscount_http_response_size_bytes_count{method="POST",endpoint="/",status_code="200"} 10000
```

### Active Connections

```prometheus
# HELP dyscount_http_active_connections Number of active HTTP connections
# TYPE dyscount_http_active_connections gauge
dyscount_http_active_connections 42
```

---

## 2. DynamoDB-Specific Metrics

### Operation Latency

```prometheus
# HELP dyscount_dynamodb_operation_duration_seconds DynamoDB operation latency distribution
# TYPE dyscount_dynamodb_operation_duration_seconds histogram
dyscount_dynamodb_operation_duration_seconds_bucket{operation="GetItem",table="users",le="0.001"} 5000
dyscount_dynamodb_operation_duration_seconds_bucket{operation="GetItem",table="users",le="0.005"} 9500
dyscount_dynamodb_operation_duration_seconds_bucket{operation="GetItem",table="users",le="0.01"} 9900
dyscount_dynamodb_operation_duration_seconds_bucket{operation="GetItem",table="users",le="0.025"} 9990
dyscount_dynamodb_operation_duration_seconds_bucket{operation="GetItem",table="users",le="0.05"} 9999
dyscount_dynamodb_operation_duration_seconds_bucket{operation="GetItem",table="users",le="+Inf"} 10000
dyscount_dynamodb_operation_duration_seconds_sum{operation="GetItem",table="users"} 25.5
dyscount_dynamodb_operation_duration_seconds_count{operation="GetItem",table="users"} 10000

dyscount_dynamodb_operation_duration_seconds_bucket{operation="Query",table="users",le="0.001"} 2000
dyscount_dynamodb_operation_duration_seconds_bucket{operation="Query",table="users",le="0.005"} 8000
dyscount_dynamodb_operation_duration_seconds_bucket{operation="Query",table="users",le="0.01"} 9500
dyscount_dynamodb_operation_duration_seconds_bucket{operation="Query",table="users",le="0.025"} 9900
dyscount_dynamodb_operation_duration_seconds_bucket{operation="Query",table="users",le="+Inf"} 10000
dyscount_dynamodb_operation_duration_seconds_sum{operation="Query",table="users"} 45.2
dyscount_dynamodb_operation_duration_seconds_count{operation="Query",table="users"} 10000
```

**Buckets**: 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5 seconds

**Labels**: `operation`, `table`, optionally `index` for GSI queries

### Operation Count

```prometheus
# HELP dyscount_dynamodb_operations_total Total DynamoDB operations executed
# TYPE dyscount_dynamodb_operations_total counter
dyscount_dynamodb_operations_total{operation="GetItem",table="users"} 50000
dyscount_dynamodb_operations_total{operation="PutItem",table="users"} 25000
dyscount_dynamodb_operations_total{operation="Query",table="users"} 15000
dyscount_dynamodb_operations_total{operation="Scan",table="users"} 1000
dyscount_dynamodb_operations_total{operation="UpdateItem",table="users"} 5000
dyscount_dynamodb_operations_total{operation="DeleteItem",table="users"} 2000
dyscount_dynamodb_operations_total{operation="BatchWriteItem",table="users"} 500
dyscount_dynamodb_operations_total{operation="Query",table="users",index="email-index"} 3000
```

### Error Count by Type

```prometheus
# HELP dyscount_dynamodb_errors_total Total DynamoDB errors by type
# TYPE dyscount_dynamodb_errors_total counter
dyscount_dynamodb_errors_total{error_type="ValidationException",operation="PutItem"} 50
dyscount_dynamodb_errors_total{error_type="ResourceNotFoundException",operation="GetItem"} 10
dyscount_dynamodb_errors_total{error_type="ConditionalCheckFailedException",operation="PutItem"} 100
dyscount_dynamodb_errors_total{error_type="ProvisionedThroughputExceededException",operation="Query"} 25
dyscount_dynamodb_errors_total{error_type="InternalServerError",operation="BatchWriteItem"} 2
dyscount_dynamodb_errors_total{error_type="ThrottlingException",operation="GetItem"} 15
```

**Error Types** (mapping to AWS DynamoDB exceptions):
- `ValidationException` - Invalid parameter values
- `ResourceNotFoundException` - Table or index not found
- `ConditionalCheckFailedException` - Conditional write failed
- `ProvisionedThroughputExceededException` - Capacity exceeded (for compatibility)
- `ThrottlingException` - Request throttled
- `InternalServerError` - Unexpected server error
- `SerializationException` - JSON parsing errors

### Throttled Requests

```prometheus
# HELP dyscount_dynamodb_throttled_requests_total Total throttled DynamoDB requests
# TYPE dyscount_dynamodb_throttled_requests_total counter
dyscount_dynamodb_throttled_requests_total{operation="GetItem",table="users",throttle_type="Read"} 15
dyscount_dynamodb_throttled_requests_total{operation="PutItem",table="users",throttle_type="Write"} 8
dyscount_dynamodb_throttled_requests_total{operation="Query",table="users",throttle_type="Read"} 25
dyscount_dynamodb_throttled_requests_total{operation="BatchWriteItem",table="users",throttle_type="Write"} 5
dyscount_dynamodb_throttled_requests_total{operation="GetItem",throttle_type="AccountLimit"} 2
```

**Throttle Types**:
- `Read` - Read capacity/limit exceeded
- `Write` - Write capacity/limit exceeded
- `AccountLimit` - Account-wide limit exceeded
- `ResourceLimit` - Per-resource limit exceeded

### Capacity Units Consumed

```prometheus
# HELP dyscount_dynamodb_consumed_capacity_units_total Total consumed capacity units (RCU/WCU)
# TYPE dyscount_dynamodb_consumed_capacity_units_total counter
dyscount_dynamodb_consumed_capacity_units_total{operation="GetItem",table="users",capacity_type="read"} 50000
dyscount_dynamodb_consumed_capacity_units_total{operation="Query",table="users",capacity_type="read"} 150000
dyscount_dynamodb_consumed_capacity_units_total{operation="PutItem",table="users",capacity_type="write"} 25000
dyscount_dynamodb_consumed_capacity_units_total{operation="BatchWriteItem",table="users",capacity_type="write"} 50000
dyscount_dynamodb_consumed_capacity_units_total{operation="Query",table="users",index="email-index",capacity_type="read"} 30000
```

**Capacity Types**: `read`, `write`

### Conditional Check Failures

```prometheus
# HELP dyscount_dynamodb_conditional_check_failed_total Total conditional check failures
# TYPE dyscount_dynamodb_conditional_check_failed_total counter
dyscount_dynamodb_conditional_check_failed_total{operation="PutItem",table="users"} 50
dyscount_dynamodb_conditional_check_failed_total{operation="UpdateItem",table="users"} 30
dyscount_dynamodb_conditional_check_failed_total{operation="DeleteItem",table="users"} 10
```

### Returned Items/Bytes

```prometheus
# HELP dyscount_dynamodb_returned_items_total Total items returned by operations
# TYPE dyscount_dynamodb_returned_items_total counter
dyscount_dynamodb_returned_items_total{operation="GetItem",table="users"} 50000
dyscount_dynamodb_returned_items_total{operation="Query",table="users"} 150000
dyscount_dynamodb_returned_items_total{operation="Scan",table="users"} 500000
dyscount_dynamodb_returned_items_total{operation="BatchGetItem",table="users"} 25000
dyscount_dynamodb_returned_items_total{operation="Query",table="users",index="email-index"} 30000

# HELP dyscount_dynamodb_returned_bytes_total Total bytes returned by operations
# TYPE dyscount_dynamodb_returned_bytes_total counter
dyscount_dynamodb_returned_bytes_total{operation="Query",table="users"} 157286400
dyscount_dynamodb_returned_bytes_total{operation="Scan",table="users"} 524288000
```

### Transaction Conflicts

```prometheus
# HELP dyscount_dynamodb_transaction_conflicts_total Total transaction conflicts
# TYPE dyscount_dynamodb_transaction_conflicts_total counter
dyscount_dynamodb_transaction_conflicts_total{table="users"} 5
```

---

## 3. SQLite Metrics

### Query Latency

```prometheus
# HELP dyscount_sqlite_query_duration_seconds SQLite query latency distribution
# TYPE dyscount_sqlite_query_duration_seconds histogram
dyscount_sqlite_query_duration_seconds_bucket{query_type="select",table="users",le="0.0001"} 5000
dyscount_sqlite_query_duration_seconds_bucket{query_type="select",table="users",le="0.0005"} 9500
dyscount_sqlite_query_duration_seconds_bucket{query_type="select",table="users",le="0.001"} 9900
dyscount_sqlite_query_duration_seconds_bucket{query_type="select",table="users",le="0.005"} 9990
dyscount_sqlite_query_duration_seconds_bucket{query_type="select",table="users",le="0.01"} 9999
dyscount_sqlite_query_duration_seconds_bucket{query_type="select",table="users",le="+Inf"} 10000
dyscount_sqlite_query_duration_seconds_sum{query_type="select",table="users"} 2.5
dyscount_sqlite_query_duration_seconds_count{query_type="select",table="users"} 10000

dyscount_sqlite_query_duration_seconds_bucket{query_type="insert",table="users",le="0.0001"} 8000
dyscount_sqlite_query_duration_seconds_bucket{query_type="insert",table="users",le="0.0005"} 9900
dyscount_sqlite_query_duration_seconds_bucket{query_type="insert",table="users",le="+Inf"} 10000
dyscount_sqlite_query_duration_seconds_sum{query_type="insert",table="users"} 1.2
dyscount_sqlite_query_duration_seconds_count{query_type="insert",table="users"} 10000
```

**Query Types**: `select`, `insert`, `update`, `delete`, `create`, `drop`, `pragma`, `transaction`

**Buckets**: 0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5 seconds

### Query Count

```prometheus
# HELP dyscount_sqlite_queries_total Total SQLite queries executed
# TYPE dyscount_sqlite_queries_total counter
dyscount_sqlite_queries_total{query_type="select",table="users"} 50000
dyscount_sqlite_queries_total{query_type="insert",table="users"} 25000
dyscount_sqlite_queries_total{query_type="update",table="users"} 5000
dyscount_sqlite_queries_total{query_type="delete",table="users"} 2000
dyscount_sqlite_queries_total{query_type="transaction_begin"} 10000
dyscount_sqlite_queries_total{query_type="transaction_commit"} 9995
dyscount_sqlite_queries_total{query_type="transaction_rollback"} 5
```

### Connection Pool Stats

```prometheus
# HELP dyscount_sqlite_connections_active Active SQLite connections
# TYPE dyscount_sqlite_connections_active gauge
dyscount_sqlite_connections_active{database="main"} 10

# HELP dyscount_sqlite_connections_idle Idle SQLite connections in pool
# TYPE dyscount_sqlite_connections_idle gauge
dyscount_sqlite_connections_idle{database="main"} 5

# HELP dyscount_sqlite_connections_max Maximum allowed SQLite connections
# TYPE dyscount_sqlite_connections_max gauge
dyscount_sqlite_connections_max{database="main"} 20

# HELP dyscount_sqlite_connection_wait_duration_seconds Time spent waiting for available connection
# TYPE dyscount_sqlite_connection_wait_duration_seconds histogram
dyscount_sqlite_connection_wait_duration_seconds_bucket{database="main",le="0.001"} 9900
dyscount_sqlite_connection_wait_duration_seconds_bucket{database="main",le="0.01"} 9999
dyscount_sqlite_connection_wait_duration_seconds_bucket{database="main",le="+Inf"} 10000
dyscount_sqlite_connection_wait_duration_seconds_sum{database="main"} 1.5
dyscount_sqlite_connection_wait_duration_seconds_count{database="main"} 10000

# HELP dyscount_sqlite_connection_wait_total Total connection pool wait events
# TYPE dyscount_sqlite_connection_wait_total counter
dyscount_sqlite_connection_wait_total{database="main"} 100
```

### Database Size

```prometheus
# HELP dyscount_sqlite_database_size_bytes SQLite database file size
# TYPE dyscount_sqlite_database_size_bytes gauge
dyscount_sqlite_database_size_bytes{database="main"} 1073741824

# HELP dyscount_sqlite_table_size_bytes Estimated size per table
# TYPE dyscount_sqlite_table_size_bytes gauge
dyscount_sqlite_table_size_bytes{table="users"} 524288000
dyscount_sqlite_table_size_bytes{table="orders"} 268435456
dyscount_sqlite_table_size_bytes{table="products"} 134217728

# HELP dyscount_sqlite_index_size_bytes Estimated index size
# TYPE dyscount_sqlite_index_size_bytes gauge
dyscount_sqlite_index_size_bytes{table="users",index="PRIMARY"} 104857600
dyscount_sqlite_index_size_bytes{table="users",index="email-index"} 52428800

# HELP dyscount_sqlite_wal_size_bytes WAL file size
# TYPE dyscount_sqlite_wal_size_bytes gauge
dyscount_sqlite_wal_size_bytes{database="main"} 67108864
```

### WAL Checkpoint Stats

```prometheus
# HELP dyscount_sqlite_checkpoint_total Total WAL checkpoints performed
# TYPE dyscount_sqlite_checkpoint_total counter
dyscount_sqlite_checkpoint_total{database="main",checkpoint_type="passive"} 1000
dyscount_sqlite_checkpoint_total{database="main",checkpoint_type="full"} 50
dyscount_sqlite_checkpoint_total{database="main",checkpoint_type="restart"} 10
dyscount_sqlite_checkpoint_total{database="main",checkpoint_type="truncate"} 100

# HELP dyscount_sqlite_checkpoint_duration_seconds WAL checkpoint duration
# TYPE dyscount_sqlite_checkpoint_duration_seconds histogram
dyscount_sqlite_checkpoint_duration_seconds_bucket{database="main",checkpoint_type="passive",le="0.001"} 900
dyscount_sqlite_checkpoint_duration_seconds_bucket{database="main",checkpoint_type="passive",le="0.01"} 990
dyscount_sqlite_checkpoint_duration_seconds_bucket{database="main",checkpoint_type="passive",le="0.1"} 999
dyscount_sqlite_checkpoint_duration_seconds_bucket{database="main",checkpoint_type="passive",le="+Inf"} 1000
dyscount_sqlite_checkpoint_duration_seconds_sum{database="main",checkpoint_type="passive"} 5.2
dyscount_sqlite_checkpoint_duration_seconds_count{database="main",checkpoint_type="passive"} 1000

# HELP dyscount_sqlite_checkpoint_pages_checkpointed Total pages written during checkpoint
# TYPE dyscount_sqlite_checkpoint_pages_checkpointed counter
dyscount_sqlite_checkpoint_pages_checkpointed{database="main"} 5242880

# HELP dyscount_sqlite_wal_frames Total frames in WAL
# TYPE dyscount_sqlite_wal_frames gauge
dyscount_sqlite_wal_frames{database="main"} 1024
```

**Checkpoint Types**: `passive`, `full`, `restart`, `truncate`

### Cache Stats

```prometheus
# HELP dyscount_sqlite_cache_pages_total Total cache pages
# TYPE dyscount_sqlite_cache_pages_total gauge
dyscount_sqlite_cache_pages_total{database="main"} 4096

# HELP dyscount_sqlite_cache_pages_used Used cache pages
# TYPE dyscount_sqlite_cache_pages_used gauge
dyscount_sqlite_cache_pages_used{database="main"} 2048

# HELP dyscount_sqlite_cache_hits_total Total cache hits
# TYPE dyscount_sqlite_cache_hits_total counter
dyscount_sqlite_cache_hits_total{database="main"} 950000

# HELP dyscount_sqlite_cache_misses_total Total cache misses
# TYPE dyscount_sqlite_cache_misses_total counter
dyscount_sqlite_cache_misses_total{database="main"} 50000

# HELP dyscount_sqlite_cache_hit_ratio Cache hit ratio (0-1)
# TYPE dyscount_sqlite_cache_hit_ratio gauge
dyscount_sqlite_cache_hit_ratio{database="main"} 0.95

# HELP dyscount_sqlite_cache_spills_total Total dirty cache page spills
# TYPE dyscount_sqlite_cache_spills_total counter
dyscount_sqlite_cache_spills_total{database="main"} 100
```

### SQLite Errors

```prometheus
# HELP dyscount_sqlite_errors_total Total SQLite errors
# TYPE dyscount_sqlite_errors_total counter
dyscount_sqlite_errors_total{error_code="BUSY",error_name="database is locked"} 10
dyscount_sqlite_errors_total{error_code="CONSTRAINT",error_name="UNIQUE constraint failed"} 5
dyscount_sqlite_errors_total{error_code="FULL",error_name="database or disk is full"} 1
```

---

## 4. System Metrics

### Memory Usage

```prometheus
# HELP dyscount_process_memory_bytes Process memory usage
# TYPE dyscount_process_memory_bytes gauge
dyscount_process_memory_bytes{type="rss"} 134217728
dyscount_process_memory_bytes{type="vms"} 1073741824
dyscount_process_memory_bytes{type="heap"} 67108864
dyscount_process_memory_bytes{type="stack"} 8388608

# HELP dyscount_process_memory_limit_bytes Process memory limit (if set)
# TYPE dyscount_process_memory_limit_bytes gauge
dyscount_process_memory_limit_bytes 2147483648
```

**Types**: `rss` (resident), `vms` (virtual), `heap`, `stack`

### Goroutine/Thread Count

```prometheus
# HELP dyscount_process_goroutines_total Number of goroutines
# TYPE dyscount_process_goroutines_total gauge
dyscount_process_goroutines_total 50

# HELP dyscount_process_threads_total Number of OS threads
# TYPE dyscount_process_threads_total gauge
dyscount_process_threads_total 12

# HELP dyscount_process_threads_max Maximum OS threads allowed
# TYPE dyscount_process_threads_max gauge
dyscount_process_threads_max 10000
```

### GC Stats

```prometheus
# HELP dyscount_process_gc_collections_total Total GC collections
# TYPE dyscount_process_gc_collections_total counter
dyscount_process_gc_collections_total 150

# HELP dyscount_process_gc_pause_seconds_total Total GC pause time
# TYPE dyscount_process_gc_pause_seconds_total counter
dyscount_process_gc_pause_seconds_total 0.5

# HELP dyscount_process_gc_duration_seconds Last GC pause duration
# TYPE dyscount_process_gc_duration_seconds gauge
dyscount_process_gc_duration_seconds 0.003

# HELP dyscount_process_gc_heap_objects Number of allocated heap objects
# TYPE dyscount_process_gc_heap_objects gauge
dyscount_process_gc_heap_objects 100000

# HELP dyscount_process_gc_heap_bytes Heap allocation bytes
# TYPE dyscount_process_gc_heap_bytes gauge
dyscount_process_gc_heap_bytes{type="alloc"} 67108864
dyscount_process_gc_heap_bytes{type="sys"} 134217728
dyscount_process_gc_heap_bytes{type="idle"} 33554432
dyscount_process_gc_heap_bytes{type="inuse"} 33554432

# HELP dyscount_process_gc_target_heap_bytes Next GC target heap size
# TYPE dyscount_process_gc_target_heap_bytes gauge
dyscount_process_gc_target_heap_bytes 134217728

# HELP dyscount_process_gc_cpu_fraction_ratio GC CPU usage ratio (0-1)
# TYPE dyscount_process_gc_cpu_fraction_ratio gauge
dyscount_process_gc_cpu_fraction_ratio 0.02
```

### CPU Usage

```prometheus
# HELP dyscount_process_cpu_seconds_total Total CPU time consumed
# TYPE dyscount_process_cpu_seconds_total counter
dyscount_process_cpu_seconds_total{mode="user"} 120.5
dyscount_process_cpu_seconds_total{mode="system"} 45.3
```

### File Descriptors

```prometheus
# HELP dyscount_process_open_fds Number of open file descriptors
# TYPE dyscount_process_open_fds gauge
dyscount_process_open_fds 25

# HELP dyscount_process_max_fds Maximum allowed file descriptors
# TYPE dyscount_process_max_fds gauge
dyscount_process_max_fds 1048576
```

### Process Info

```prometheus
# HELP dyscount_build_info Build information
# TYPE dyscount_build_info gauge
dyscount_build_info{version="0.1.0",goversion="go1.21.0",revision="abc123",branch="main"} 1

# HELP dyscount_process_start_time_seconds Process start time
# TYPE dyscount_process_start_time_seconds gauge
dyscount_process_start_time_seconds 1699999999

# HELP dyscount_process_uptime_seconds Process uptime
# TYPE dyscount_process_uptime_seconds counter
dyscount_process_uptime_seconds 86400
```

---

## 5. Example Prometheus Scraping Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'dyscount'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s
    
    # Optional: relabeling
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        
# Optional: service discovery for multiple instances
  - job_name: 'dyscount-cluster'
    consul_sd_configs:
      - server: 'localhost:8500'
        services: ['dyscount']
```

---

## 6. Example Alerting Rules

```yaml
# dyscount-alerts.yml
groups:
  - name: dyscount-alerts
    rules:
      # High error rate
      - alert: DyscountHighErrorRate
        expr: |
          (
            sum(rate(dyscount_http_requests_total{status_code=~"5.."}[5m])) 
            / 
            sum(rate(dyscount_http_requests_total[5m]))
          ) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on Dyscount"
          description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes"

      # High latency p99
      - alert: DyscountHighLatency
        expr: |
          histogram_quantile(0.99, 
            sum(rate(dyscount_dynamodb_operation_duration_seconds_bucket[5m])) by (operation, le)
          ) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High DynamoDB operation latency"
          description: "p99 latency for {{ $labels.operation }} is {{ $value }}s"

      # Throttling events
      - alert: DyscountThrottling
        expr: sum(rate(dyscount_dynamodb_throttled_requests_total[5m])) by (operation, table) > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Dyscount throttling detected"
          description: "Throttling on {{ $labels.operation }} for table {{ $labels.table }}"

      # SQLite connection pool exhaustion
      - alert: DyscountSQLitePoolExhaustion
        expr: |
          dyscount_sqlite_connections_active / dyscount_sqlite_connections_max > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "SQLite connection pool near exhaustion"
          description: "{{ $labels.database }} pool is {{ $value | humanizePercentage }} full"

      # WAL checkpoint taking too long
      - alert: DyscountSlowCheckpoint
        expr: |
          histogram_quantile(0.99, 
            sum(rate(dyscount_sqlite_checkpoint_duration_seconds_bucket[5m])) by (le)
          ) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow SQLite WAL checkpoint"
          description: "p99 checkpoint duration is {{ $value }}s"

      # Low cache hit ratio
      - alert: DyscountLowCacheHitRatio
        expr: dyscount_sqlite_cache_hit_ratio < 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low SQLite cache hit ratio"
          description: "Cache hit ratio is {{ $value | humanizePercentage }}"

      # Memory usage high
      - alert: DyscountHighMemoryUsage
        expr: |
          dyscount_process_memory_bytes{type="rss"} / dyscount_process_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Dyscount high memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      # GC pressure
      - alert: DyscountHighGCPressure
        expr: dyscount_process_gc_cpu_fraction_ratio > 0.2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High GC pressure"
          description: "GC is using {{ $value | humanizePercentage }} of CPU"
```

---

## 7. Example Grafana Dashboard Queries

### Request Rate by Operation

```promql
sum(rate(dyscount_dynamodb_operations_total[5m])) by (operation)
```

### Error Rate

```promql
sum(rate(dyscount_dynamodb_errors_total[5m])) by (error_type)
/
sum(rate(dyscount_dynamodb_operations_total[5m])) by (error_type)
```

### P99 Latency Heatmap

```promql
histogram_quantile(0.99,
  sum(rate(dyscount_dynamodb_operation_duration_seconds_bucket[5m])) by (operation, le)
)
```

### Capacity Units Consumption

```promql
sum(rate(dyscount_dynamodb_consumed_capacity_units_total[5m])) by (capacity_type, table)
```

### SQLite Query Performance

```promql
histogram_quantile(0.95,
  sum(rate(dyscount_sqlite_query_duration_seconds_bucket[5m])) by (query_type, le)
)
```

### Active Connections Over Time

```promql
dyscount_sqlite_connections_active{database="main"}
```

---

## 8. Implementation Notes

### Metric Collection Strategy

1. **HTTP Metrics**: Collected via middleware wrapping all HTTP handlers
2. **DynamoDB Metrics**: Collected at the API layer before/after operation execution
3. **SQLite Metrics**: Collected via connection wrapper and query interceptor
4. **System Metrics**: Collected via Go runtime and process stats

### Performance Considerations

- Use buffered channels for async metric recording (if needed)
- Histograms have performance cost - use appropriate bucket sizes
- Avoid high-cardinality labels to prevent time series explosion
- Consider metric sampling for very high-throughput scenarios

### Testing Metrics

```go
// Example test assertion
func TestMetricsIncrement(t *testing.T) {
    // Before operation
    before := testutil.ToFloat64(dyscount_dynamodb_operations_total.WithLabelValues("GetItem", "test-table"))
    
    // Execute operation
    // ...
    
    // After operation
    after := testutil.ToFloat64(dyscount_dynamodb_operations_total.WithLabelValues("GetItem", "test-table"))
    
    if after != before + 1 {
        t.Errorf("Expected metric to increment by 1")
    }
}
```

---

## References

- [Prometheus Metric Naming Best Practices](https://prometheus.io/docs/practices/naming/)
- [AWS DynamoDB CloudWatch Metrics](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html)
- [Prometheus Histograms](https://prometheus.io/docs/practices/histograms/)
- [SQLite Performance Metrics](https://www.sqlite.org/dbstat.html)
