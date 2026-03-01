# Dyscount Configuration Specification

This document defines the configuration schema for Dyscount, a DynamoDB-compatible API service backed by SQLite. The configuration system supports JSON config files, environment variables, and sensible defaults.

---

## Table of Contents

1. [Configuration Sources & Priority](#1-configuration-sources--priority)
2. [Configuration Sections](#2-configuration-sections)
3. [Default Values](#3-default-values)
4. [JSON Schema](#4-json-schema)
5. [Environment Variables](#5-environment-variables)
6. [Example Configurations](#6-example-configurations)
7. [Implementation Notes](#7-implementation-notes)

---

## 1. Configuration Sources & Priority

Dyscount reads configuration from three sources, with later sources overriding earlier ones:

| Priority | Source | Description |
|----------|--------|-------------|
| 1 (lowest) | **Built-in Defaults** | Hardcoded sensible defaults for all settings |
| 2 | **JSON Config File** | `dyscount.json` or path specified via `--config` flag |
| 3 (highest) | **Environment Variables** | Variables with `DYSCOUNT_` prefix |

### Configuration File Discovery

The configuration file is discovered in the following order:

1. Path specified via `--config` / `-c` command-line flag
2. `DYSCOUNT_CONFIG_FILE` environment variable
3. `./dyscount.json` (current working directory)
4. `~/.config/dyscount/config.json` (user config directory)
5. `/etc/dyscount/config.json` (system-wide config)

If no config file is found, all settings use defaults (potentially overridden by environment variables).

---

## 2. Configuration Sections

### 2.1 Server Section

HTTP server settings for the DynamoDB-compatible API endpoint.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `port` | integer | `8000` | TCP port to listen on |
| `host` | string | `"0.0.0.0"` | Bind address (use `127.0.0.1` for localhost-only) |
| `workers` | integer | auto | Number of worker processes/threads (auto = CPU count) |
| `timeout` | object | see below | Request timeout settings |
| `timeout.read` | integer | `30` | Read timeout in seconds |
| `timeout.write` | integer | `30` | Write timeout in seconds |
| `timeout.idle` | integer | `120` | Idle connection timeout in seconds |
| `max_request_size` | integer | `16777216` | Max request body size in bytes (16 MB) |
| `keep_alive` | boolean | `true` | Enable HTTP keep-alive |

**Notes:**
- Port 8000 is chosen for DynamoDB Local compatibility
- Workers: Python uses processes (uvicorn workers), Go/Rust/Zig use threads/goroutines

### 2.2 Storage Section

SQLite storage backend configuration.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `data_directory` | string | `"./data"` | Root directory for SQLite database files |
| `namespace` | string | `"default"` | Logical namespace for table isolation |
| `sqlite_mode` | string | `"wal"` | SQLite journal mode: `wal` or `normal` |
| `persistence_mode` | string | `"balanced"` | Durability level: `durable`, `balanced`, or `fast` |
| `cache_size_mb` | integer | `200` | SQLite cache size in megabytes |
| `busy_timeout_ms` | integer | `5000` | SQLite busy timeout in milliseconds |
| `max_connections` | integer | auto | Max concurrent SQLite connections per table |
| `checkpoint_interval_sec` | integer | `300` | WAL checkpoint interval in seconds (0 = auto) |

**Persistence Mode Details:**

| Mode | synchronous | journal_mode | fsync | Use Case |
|------|-------------|--------------|-------|----------|
| `durable` | `FULL` | `wal` | Every commit | Production, no data loss tolerance |
| `balanced` | `NORMAL` | `wal` | Periodic | Development, good performance |
| `fast` | `OFF` | `memory` | Never | Testing, maximum speed, data loss acceptable |

**Storage Path Structure:**
```
{data_directory}/{namespace}/{table_name}.db
```

### 2.3 Auth Section

Authentication and authorization settings.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `mode` | string | `"local"` | Auth mode: `local` (no auth), `production` (SigV4) |
| `aws_region` | string | `"eu-west-1"` | Default AWS region for requests |
| `iam_policy_file` | string | `null` | Path to IAM policy JSON file |
| `access_key_id` | string | `"local"` | Static access key ID (local mode only) |
| `secret_access_key` | string | `"local"` | Static secret key (local mode only) |
| `signature_ttl_sec` | integer | `300` | Max age of signed requests in seconds |

**Auth Modes:**

- **`local`**: Accepts any credentials (like DynamoDB Local). Useful for development and testing.
- **`production`**: Verifies AWS Signature Version 4. Validates credentials and IAM policies.

### 2.4 Logging Section

Structured logging configuration.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `level` | string | `"info"` | Log level: `debug`, `info`, `warn`, `error` |
| `format` | string | `"json"` | Output format: `json` or `text` |
| `output` | string | `"stdout"` | Output destination: `stdout`, `stderr`, or file path |
| `include_timestamp` | boolean | `true` | Include ISO8601 timestamp |
| `include_source` | boolean | `false` | Include source file and line number |
| `redact_sensitive` | boolean | `true` | Redact sensitive data (credentials, tokens) |
| `request_logging` | boolean | `true` | Log all HTTP requests |
| `slow_query_threshold_ms` | integer | `1000` | Log warnings for queries exceeding this duration |

**Log Level Definitions:**

| Level | Description |
|-------|-------------|
| `debug` | Detailed debugging information, request/response bodies |
| `info` | Normal operational messages, startup info |
| `warn` | Warning conditions, deprecated feature usage |
| `error` | Error conditions, failed operations |

### 2.5 Metrics Section

Prometheus metrics and observability.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `prometheus_enabled` | boolean | `true` | Enable Prometheus metrics endpoint |
| `prometheus_port` | integer | `9090` | Port for Prometheus metrics (separate from API) |
| `prometheus_path` | string | `"/metrics"` | HTTP path for metrics endpoint |
| `prometheus_host` | string | `"0.0.0.0"` | Bind address for metrics server |
| `operation_latency_buckets` | array | `[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]` | Latency histogram buckets in seconds |
| `collect_table_metrics` | boolean | `true` | Collect per-table metrics |
| `collect_query_metrics` | boolean | `true` | Collect per-query-type metrics |

**Default Metrics Exposed:**

| Metric | Type | Description |
|--------|------|-------------|
| `dyscount_requests_total` | Counter | Total HTTP requests |
| `dyscount_request_duration_seconds` | Histogram | Request latency |
| `dyscount_operations_total` | Counter | DynamoDB operations by type |
| `dyscount_operation_duration_seconds` | Histogram | Operation latency |
| `dyscount_errors_total` | Counter | Errors by type |
| `dyscount_storage_size_bytes` | Gauge | Storage size by table |
| `dyscount_table_item_count` | Gauge | Items per table |
| `dyscount_active_connections` | Gauge | Active SQLite connections |

### 2.6 CORS Section

Cross-Origin Resource Sharing settings.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable CORS headers |
| `allowed_origins` | array | `["*"]` | List of allowed origins or `["*"]` for all |
| `allowed_methods` | array | `["POST", "OPTIONS"]` | Allowed HTTP methods |
| `allowed_headers` | array | `["*"]` | Allowed request headers |
| `allow_credentials` | boolean | `false` | Allow credentials in CORS requests |
| `max_age` | integer | `86400` | Preflight cache duration in seconds |

### 2.7 Limits Section

Resource and operation limits.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `max_item_size` | integer | `409600` | Max item size in bytes (400 KB DynamoDB limit) |
| `max_batch_size` | integer | `25` | Max items per BatchWriteItem/BatchGetItem |
| `max_batch_bytes` | integer | `16777216` | Max batch request size in bytes (16 MB) |
| `max_query_limit` | integer | `1000` | Max items returned per Query operation |
| `max_scan_limit` | integer | `1000` | Max items returned per Scan operation |
| `max_page_size` | integer | `1000` | Max items per page in paginated responses |
| `max_expression_length` | integer | `4096` | Max characters in filter/condition expressions |
| `max_gsi_per_table` | integer | `20` | Max Global Secondary Indexes per table |
| `max_lsi_per_table` | integer | `5` | Max Local Secondary Indexes per table |
| `max_table_name_length` | integer | `1024` | Max characters in table names |
| `max_concurrent_requests` | integer | `1000` | Max concurrent HTTP requests |
| `rate_limit_rps` | integer | `0` | Rate limit in requests per second (0 = unlimited) |

**Note on DynamoDB Compatibility:**
- `max_item_size`: DynamoDB limit is 400 KB (409,600 bytes) including attribute names
- `max_batch_size`: DynamoDB limit is 25 items for BatchWriteItem, 100 for BatchGetItem
- We default to 25 for consistency with the more restrictive limit

---

## 3. Default Values

### Summary of Key Defaults

| Setting | Default | Override via Env Var |
|---------|---------|---------------------|
| Server Port | `8000` | `DYSCOUNT_SERVER__PORT` |
| AWS Region | `eu-west-1` | `DYSCOUNT_AUTH__AWS_REGION` |
| Namespace | `default` | `DYSCOUNT_STORAGE__NAMESPACE` |
| Data Directory | `./data` | `DYSCOUNT_STORAGE__DATA_DIRECTORY` |
| Log Level | `info` | `DYSCOUNT_LOGGING__LEVEL` |
| Prometheus Port | `9090` | `DYSCOUNT_METRICS__PROMETHEUS_PORT` |

### Why These Defaults?

- **Port 8000**: Matches DynamoDB Local default for SDK compatibility
- **eu-west-1**: Ireland region commonly used for European development
- **WAL Mode**: Enables concurrent reads during writes, essential for API performance
- **Balanced Persistence**: Good performance with reasonable durability for most use cases
- **JSON Logging**: Structured logs are easier to parse in production environments

---

## 4. JSON Schema

The complete JSON Schema for `dyscount.json` configuration files:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://dyscount.dev/config-schema.json",
  "title": "Dyscount Configuration",
  "description": "Configuration schema for Dyscount DynamoDB-compatible API service",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "server": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "port": {
          "type": "integer",
          "minimum": 1,
          "maximum": 65535,
          "default": 8000
        },
        "host": {
          "type": "string",
          "default": "0.0.0.0"
        },
        "workers": {
          "type": ["integer", "string"],
          "minimum": 1,
          "pattern": "^auto$",
          "default": "auto"
        },
        "timeout": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "read": {
              "type": "integer",
              "minimum": 1,
              "default": 30
            },
            "write": {
              "type": "integer",
              "minimum": 1,
              "default": 30
            },
            "idle": {
              "type": "integer",
              "minimum": 1,
              "default": 120
            }
          }
        },
        "max_request_size": {
          "type": "integer",
          "minimum": 1024,
          "default": 16777216
        },
        "keep_alive": {
          "type": "boolean",
          "default": true
        }
      }
    },
    "storage": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "data_directory": {
          "type": "string",
          "default": "./data"
        },
        "namespace": {
          "type": "string",
          "pattern": "^[a-zA-Z0-9_-]+$",
          "maxLength": 64,
          "default": "default"
        },
        "sqlite_mode": {
          "type": "string",
          "enum": ["wal", "normal"],
          "default": "wal"
        },
        "persistence_mode": {
          "type": "string",
          "enum": ["durable", "balanced", "fast"],
          "default": "balanced"
        },
        "cache_size_mb": {
          "type": "integer",
          "minimum": 1,
          "maximum": 4096,
          "default": 200
        },
        "busy_timeout_ms": {
          "type": "integer",
          "minimum": 0,
          "default": 5000
        },
        "max_connections": {
          "type": ["integer", "string"],
          "minimum": 1,
          "pattern": "^auto$",
          "default": "auto"
        },
        "checkpoint_interval_sec": {
          "type": "integer",
          "minimum": 0,
          "default": 300
        }
      }
    },
    "auth": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "mode": {
          "type": "string",
          "enum": ["local", "production"],
          "default": "local"
        },
        "aws_region": {
          "type": "string",
          "pattern": "^[a-z]{2}-[a-z]+-[0-9]+$",
          "default": "eu-west-1"
        },
        "iam_policy_file": {
          "type": ["string", "null"],
          "default": null
        },
        "access_key_id": {
          "type": "string",
          "default": "local"
        },
        "secret_access_key": {
          "type": "string",
          "default": "local"
        },
        "signature_ttl_sec": {
          "type": "integer",
          "minimum": 0,
          "maximum": 3600,
          "default": 300
        }
      }
    },
    "logging": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "level": {
          "type": "string",
          "enum": ["debug", "info", "warn", "error"],
          "default": "info"
        },
        "format": {
          "type": "string",
          "enum": ["json", "text"],
          "default": "json"
        },
        "output": {
          "type": "string",
          "default": "stdout"
        },
        "include_timestamp": {
          "type": "boolean",
          "default": true
        },
        "include_source": {
          "type": "boolean",
          "default": false
        },
        "redact_sensitive": {
          "type": "boolean",
          "default": true
        },
        "request_logging": {
          "type": "boolean",
          "default": true
        },
        "slow_query_threshold_ms": {
          "type": "integer",
          "minimum": 0,
          "default": 1000
        }
      }
    },
    "metrics": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "prometheus_enabled": {
          "type": "boolean",
          "default": true
        },
        "prometheus_port": {
          "type": "integer",
          "minimum": 1,
          "maximum": 65535,
          "default": 9090
        },
        "prometheus_path": {
          "type": "string",
          "pattern": "^/",
          "default": "/metrics"
        },
        "prometheus_host": {
          "type": "string",
          "default": "0.0.0.0"
        },
        "operation_latency_buckets": {
          "type": "array",
          "items": {
            "type": "number",
            "minimum": 0
          },
          "default": [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        },
        "collect_table_metrics": {
          "type": "boolean",
          "default": true
        },
        "collect_query_metrics": {
          "type": "boolean",
          "default": true
        }
      }
    },
    "cors": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "enabled": {
          "type": "boolean",
          "default": false
        },
        "allowed_origins": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "default": ["*"]
        },
        "allowed_methods": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"]
          },
          "default": ["POST", "OPTIONS"]
        },
        "allowed_headers": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "default": ["*"]
        },
        "allow_credentials": {
          "type": "boolean",
          "default": false
        },
        "max_age": {
          "type": "integer",
          "minimum": 0,
          "default": 86400
        }
      }
    },
    "limits": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "max_item_size": {
          "type": "integer",
          "minimum": 1024,
          "maximum": 4194304,
          "default": 409600
        },
        "max_batch_size": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100,
          "default": 25
        },
        "max_batch_bytes": {
          "type": "integer",
          "minimum": 1024,
          "default": 16777216
        },
        "max_query_limit": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10000,
          "default": 1000
        },
        "max_scan_limit": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10000,
          "default": 1000
        },
        "max_page_size": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10000,
          "default": 1000
        },
        "max_expression_length": {
          "type": "integer",
          "minimum": 1,
          "maximum": 65536,
          "default": 4096
        },
        "max_gsi_per_table": {
          "type": "integer",
          "minimum": 0,
          "maximum": 20,
          "default": 20
        },
        "max_lsi_per_table": {
          "type": "integer",
          "minimum": 0,
          "maximum": 5,
          "default": 5
        },
        "max_table_name_length": {
          "type": "integer",
          "minimum": 1,
          "maximum": 1024,
          "default": 1024
        },
        "max_concurrent_requests": {
          "type": "integer",
          "minimum": 1,
          "default": 1000
        },
        "rate_limit_rps": {
          "type": "integer",
          "minimum": 0,
          "default": 0
        }
      }
    }
  }
}
```

---

## 5. Environment Variables

### 5.1 Naming Convention

All environment variables use the `DYSCOUNT_` prefix followed by the section and setting names:

```
DYSCOUNT_<SECTION>__<SETTING>
```

- **Double underscore (`__`)** separates section from setting name
- **Single underscore (`_`)** separates words within section or setting names
- All letters are **uppercase**

### 5.2 Variable Reference

| Variable | Maps To | Type | Example |
|----------|---------|------|---------|
| `DYSCOUNT_SERVER__PORT` | `server.port` | integer | `8000` |
| `DYSCOUNT_SERVER__HOST` | `server.host` | string | `127.0.0.1` |
| `DYSCOUNT_SERVER__WORKERS` | `server.workers` | integer/string | `4` or `auto` |
| `DYSCOUNT_SERVER__TIMEOUT__READ` | `server.timeout.read` | integer | `30` |
| `DYSCOUNT_SERVER__TIMEOUT__WRITE` | `server.timeout.write` | integer | `30` |
| `DYSCOUNT_SERVER__TIMEOUT__IDLE` | `server.timeout.idle` | integer | `120` |
| `DYSCOUNT_SERVER__MAX_REQUEST_SIZE` | `server.max_request_size` | integer | `16777216` |
| `DYSCOUNT_SERVER__KEEP_ALIVE` | `server.keep_alive` | boolean | `true` |
| `DYSCOUNT_STORAGE__DATA_DIRECTORY` | `storage.data_directory` | string | `/var/lib/dyscount` |
| `DYSCOUNT_STORAGE__NAMESPACE` | `storage.namespace` | string | `production` |
| `DYSCOUNT_STORAGE__SQLITE_MODE` | `storage.sqlite_mode` | string | `wal` |
| `DYSCOUNT_STORAGE__PERSISTENCE_MODE` | `storage.persistence_mode` | string | `durable` |
| `DYSCOUNT_STORAGE__CACHE_SIZE_MB` | `storage.cache_size_mb` | integer | `200` |
| `DYSCOUNT_STORAGE__BUSY_TIMEOUT_MS` | `storage.busy_timeout_ms` | integer | `5000` |
| `DYSCOUNT_STORAGE__MAX_CONNECTIONS` | `storage.max_connections` | integer | `10` |
| `DYSCOUNT_STORAGE__CHECKPOINT_INTERVAL_SEC` | `storage.checkpoint_interval_sec` | integer | `300` |
| `DYSCOUNT_AUTH__MODE` | `auth.mode` | string | `production` |
| `DYSCOUNT_AUTH__AWS_REGION` | `auth.aws_region` | string | `us-east-1` |
| `DYSCOUNT_AUTH__IAM_POLICY_FILE` | `auth.iam_policy_file` | string | `/etc/dyscount/policy.json` |
| `DYSCOUNT_AUTH__ACCESS_KEY_ID` | `auth.access_key_id` | string | `AKIA...` |
| `DYSCOUNT_AUTH__SECRET_ACCESS_KEY` | `auth.secret_access_key` | string | `secret...` |
| `DYSCOUNT_AUTH__SIGNATURE_TTL_SEC` | `auth.signature_ttl_sec` | integer | `300` |
| `DYSCOUNT_LOGGING__LEVEL` | `logging.level` | string | `debug` |
| `DYSCOUNT_LOGGING__FORMAT` | `logging.format` | string | `json` |
| `DYSCOUNT_LOGGING__OUTPUT` | `logging.output` | string | `/var/log/dyscount.log` |
| `DYSCOUNT_LOGGING__INCLUDE_TIMESTAMP` | `logging.include_timestamp` | boolean | `true` |
| `DYSCOUNT_LOGGING__INCLUDE_SOURCE` | `logging.include_source` | boolean | `false` |
| `DYSCOUNT_LOGGING__REDACT_SENSITIVE` | `logging.redact_sensitive` | boolean | `true` |
| `DYSCOUNT_LOGGING__REQUEST_LOGGING` | `logging.request_logging` | boolean | `true` |
| `DYSCOUNT_LOGGING__SLOW_QUERY_THRESHOLD_MS` | `logging.slow_query_threshold_ms` | integer | `1000` |
| `DYSCOUNT_METRICS__PROMETHEUS_ENABLED` | `metrics.prometheus_enabled` | boolean | `true` |
| `DYSCOUNT_METRICS__PROMETHEUS_PORT` | `metrics.prometheus_port` | integer | `9090` |
| `DYSCOUNT_METRICS__PROMETHEUS_PATH` | `metrics.prometheus_path` | string | `/metrics` |
| `DYSCOUNT_METRICS__PROMETHEUS_HOST` | `metrics.prometheus_host` | string | `0.0.0.0` |
| `DYSCOUNT_METRICS__COLLECT_TABLE_METRICS` | `metrics.collect_table_metrics` | boolean | `true` |
| `DYSCOUNT_METRICS__COLLECT_QUERY_METRICS` | `metrics.collect_query_metrics` | boolean | `true` |
| `DYSCOUNT_CORS__ENABLED` | `cors.enabled` | boolean | `true` |
| `DYSCOUNT_CORS__ALLOWED_ORIGINS` | `cors.allowed_origins` | JSON array | `["https://app.example.com"]` |
| `DYSCOUNT_CORS__ALLOWED_METHODS` | `cors.allowed_methods` | JSON array | `["POST","OPTIONS"]` |
| `DYSCOUNT_CORS__ALLOWED_HEADERS` | `cors.allowed_headers` | JSON array | `["Content-Type","Authorization"]` |
| `DYSCOUNT_CORS__ALLOW_CREDENTIALS` | `cors.allow_credentials` | boolean | `false` |
| `DYSCOUNT_CORS__MAX_AGE` | `cors.max_age` | integer | `86400` |
| `DYSCOUNT_LIMITS__MAX_ITEM_SIZE` | `limits.max_item_size` | integer | `409600` |
| `DYSCOUNT_LIMITS__MAX_BATCH_SIZE` | `limits.max_batch_size` | integer | `25` |
| `DYSCOUNT_LIMITS__MAX_BATCH_BYTES` | `limits.max_batch_bytes` | integer | `16777216` |
| `DYSCOUNT_LIMITS__MAX_QUERY_LIMIT` | `limits.max_query_limit` | integer | `1000` |
| `DYSCOUNT_LIMITS__MAX_SCAN_LIMIT` | `limits.max_scan_limit` | integer | `1000` |
| `DYSCOUNT_LIMITS__MAX_CONCURRENT_REQUESTS` | `limits.max_concurrent_requests` | integer | `1000` |
| `DYSCOUNT_LIMITS__RATE_LIMIT_RPS` | `limits.rate_limit_rps` | integer | `0` |
| `DYSCOUNT_CONFIG_FILE` | Config file path | string | `/etc/dyscount/config.json` |

### 5.3 Boolean Environment Values

Boolean values in environment variables are parsed case-insensitively:

| True Values | False Values |
|-------------|--------------|
| `true`, `1`, `yes`, `on`, `enable` | `false`, `0`, `no`, `off`, `disable` |

### 5.4 Array Environment Values

Array values are specified as JSON arrays:

```bash
export DYSCOUNT_CORS__ALLOWED_ORIGINS='["https://app1.com", "https://app2.com"]'
```

---

## 6. Example Configurations

### 6.1 Minimal Configuration

```json
{
  "server": {
    "port": 8000
  },
  "storage": {
    "data_directory": "./data"
  }
}
```

### 6.2 Development Configuration

```json
{
  "server": {
    "port": 8000,
    "host": "127.0.0.1",
    "workers": 2
  },
  "storage": {
    "data_directory": "./data",
    "namespace": "dev",
    "persistence_mode": "fast"
  },
  "auth": {
    "mode": "local"
  },
  "logging": {
    "level": "debug",
    "format": "text",
    "include_source": true
  },
  "metrics": {
    "prometheus_enabled": true,
    "prometheus_port": 9090
  }
}
```

### 6.3 Production Configuration

```json
{
  "server": {
    "port": 8000,
    "host": "0.0.0.0",
    "workers": 8,
    "timeout": {
      "read": 30,
      "write": 30,
      "idle": 120
    },
    "max_request_size": 16777216
  },
  "storage": {
    "data_directory": "/var/lib/dyscount",
    "namespace": "production",
    "sqlite_mode": "wal",
    "persistence_mode": "durable",
    "cache_size_mb": 512,
    "busy_timeout_ms": 10000,
    "max_connections": 20,
    "checkpoint_interval_sec": 300
  },
  "auth": {
    "mode": "production",
    "aws_region": "eu-west-1",
    "iam_policy_file": "/etc/dyscount/iam-policy.json",
    "signature_ttl_sec": 300
  },
  "logging": {
    "level": "info",
    "format": "json",
    "output": "stdout",
    "include_timestamp": true,
    "include_source": false,
    "redact_sensitive": true,
    "request_logging": true,
    "slow_query_threshold_ms": 500
  },
  "metrics": {
    "prometheus_enabled": true,
    "prometheus_port": 9090,
    "prometheus_host": "0.0.0.0",
    "collect_table_metrics": true,
    "collect_query_metrics": true
  },
  "cors": {
    "enabled": false
  },
  "limits": {
    "max_item_size": 409600,
    "max_batch_size": 25,
    "max_batch_bytes": 16777216,
    "max_query_limit": 1000,
    "max_concurrent_requests": 10000,
    "rate_limit_rps": 0
  }
}
```

### 6.4 Docker Configuration

```json
{
  "server": {
    "port": 8000,
    "host": "0.0.0.0"
  },
  "storage": {
    "data_directory": "/data",
    "persistence_mode": "balanced"
  },
  "logging": {
    "level": "info",
    "format": "json"
  }
}
```

With corresponding `docker run`:

```bash
docker run -d \
  -p 8000:8000 \
  -p 9090:9090 \
  -v dyscount-data:/data \
  -e DYSCOUNT_STORAGE__NAMESPACE=production \
  -e DYSCOUNT_AUTH__MODE=local \
  dyscount:latest
```

### 6.5 Environment Variable Examples

#### Basic Local Development

```bash
# Minimal local setup
export DYSCOUNT_SERVER__PORT=8000
export DYSCOUNT_STORAGE__DATA_DIRECTORY=./data
export DYSCOUNT_AUTH__MODE=local
export DYSCOUNT_LOGGING__LEVEL=debug

# Run the server
dyscount
```

#### Production with Custom Region

```bash
# Production settings via environment
export DYSCOUNT_SERVER__PORT=8000
export DYSCOUNT_SERVER__WORKERS=8
export DYSCOUNT_STORAGE__DATA_DIRECTORY=/var/lib/dyscount
export DYSCOUNT_STORAGE__NAMESPACE=prod
export DYSCOUNT_STORAGE__PERSISTENCE_MODE=durable
export DYSCOUNT_AUTH__MODE=production
export DYSCOUNT_AUTH__AWS_REGION=us-east-1
export DYSCOUNT_AUTH__IAM_POLICY_FILE=/etc/dyscount/policy.json
export DYSCOUNT_LOGGING__LEVEL=warn
export DYSCOUNT_LOGGING__FORMAT=json
export DYSCOUNT_METRICS__PROMETHEUS_ENABLED=true
export DYSCOUNT_LIMITS__RATE_LIMIT_RPS=1000

# Run the server
dyscount
```

#### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dyscount
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: dyscount
        image: dyscount:latest
        ports:
        - containerPort: 8000
          name: api
        - containerPort: 9090
          name: metrics
        env:
        - name: DYSCOUNT_SERVER__PORT
          value: "8000"
        - name: DYSCOUNT_SERVER__WORKERS
          value: "4"
        - name: DYSCOUNT_STORAGE__DATA_DIRECTORY
          value: "/data"
        - name: DYSCOUNT_STORAGE__NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        - name: DYSCOUNT_STORAGE__PERSISTENCE_MODE
          value: "balanced"
        - name: DYSCOUNT_AUTH__MODE
          value: "local"
        - name: DYSCOUNT_LOGGING__LEVEL
          value: "info"
        - name: DYSCOUNT_METRICS__PROMETHEUS_ENABLED
          value: "true"
        volumeMounts:
        - name: data
          mountPath: /data
        livenessProbe:
          httpGet:
            path: /metrics
            port: 9090
          initialDelaySeconds: 10
          periodSeconds: 10
```

---

## 7. Implementation Notes

### 7.1 Configuration Loading (Per Language)

#### Python

```python
# Using pydantic-settings
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DYSCOUNT_SERVER__")
    port: int = 8000
    host: str = "0.0.0.0"
    # ...

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DYSCOUNT_",
        env_nested_delimiter="__",
        json_file="dyscount.json",
        json_file_encoding="utf-8"
    )
    server: ServerSettings = Field(default_factory=ServerSettings)
    # ...
```

#### Go

```go
// Using viper
type Config struct {
    Server  ServerConfig  `mapstructure:"server"`
    Storage StorageConfig `mapstructure:"storage"`
    // ...
}

func Load() (*Config, error) {
    v := viper.New()
    v.SetEnvPrefix("DYSCOUNT")
    v.SetEnvKeyReplacer(strings.NewReplacer(".", "__"))
    v.AutomaticEnv()
    
    v.SetConfigName("dyscount")
    v.SetConfigType("json")
    v.AddConfigPath(".")
    // ...
}
```

#### Rust

```rust
// Using config + serde
use serde::Deserialize;
use config::{Config, ConfigError, Environment};

#[derive(Debug, Deserialize)]
struct Server {
    port: u16,
    host: String,
    // ...
}

#[derive(Debug, Deserialize)]
struct Settings {
    server: Server,
    // ...
}

impl Settings {
    pub fn new() -> Result<Self, ConfigError> {
        let s = Config::builder()
            .add_source(config::File::with_name("dyscount"))
            .add_source(Environment::with_prefix("DYSCOUNT")
                .separator("__"))
            .build()?;
        s.try_deserialize()
    }
}
```

#### Zig

```zig
// Manual implementation with std.json and std.process
const std = @import("std");

pub const Config = struct {
    server: ServerConfig,
    // ...
    
    pub fn load(allocator: std.mem.Allocator) !Config {
        // Load defaults
        var config = Config{
            .server = .{ .port = 8000, ... },
            // ...
        };
        
        // Override from file
        if (try loadFromFile(allocator, "dyscount.json")) |file_config| {
            config.merge(file_config);
        }
        
        // Override from environment
        config.mergeFromEnv(allocator);
        
        return config;
    }
};
```

### 7.2 Validation Rules

All implementations should validate:

1. **Port numbers** are in valid range (1-65535)
2. **Paths** are absolute or resolve correctly
3. **Directory permissions** allow read/write
4. **Enum values** match allowed options
5. **Timeout values** are positive integers
6. **Array values** contain valid elements

### 7.3 Hot Reloading (Future)

Some settings may support hot reloading without restart:

| Setting | Hot Reloadable |
|---------|----------------|
| `logging.level` | ✅ Yes |
| `limits.*` | ✅ Yes |
| `cors.*` | ✅ Yes |
| `metrics.*` | ✅ Yes |
| `server.port` | ❌ No (requires restart) |
| `storage.*` | ❌ No (requires restart) |
| `auth.*` | ⚠️ Partial (IAM file reload) |

### 7.4 Security Considerations

1. **Never log** `auth.secret_access_key` or IAM credentials
2. **Validate** IAM policy file permissions (should be readable only by owner)
3. **Sanitize** `data_directory` path to prevent directory traversal
4. **Redact** sensitive headers in request logging (`Authorization`, `X-Amz-Security-Token`)

### 7.5 Configuration Merging Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Merge                       │
├─────────────────────────────────────────────────────────────┤
│ 1. Start with built-in defaults                              │
│                                                              │
│ 2. Load JSON config file (if exists):                        │
│    - Deep merge with defaults                                │
│    - Missing keys use defaults                               │
│    - Null values use defaults                                │
│                                                              │
│ 3. Apply environment variables (if set):                     │
│    - Override specific settings                              │
│    - Empty string treated as unset (use default)             │
│                                                              │
│ 4. Validate final configuration                              │
│    - Type checking                                           │
│    - Range validation                                        │
│    - Cross-field consistency                                 │
└─────────────────────────────────────────────────────────────┘
```

### 7.6 Configuration Validation Errors

Implementations should provide clear error messages:

```
Error: Invalid configuration
  at server.port: must be between 1 and 65535, got 99999
  at storage.data_directory: directory does not exist: /invalid/path
  at auth.iam_policy_file: file not readable: /etc/dyscount/policy.json
```

---

## References

- [AWS DynamoDB Limits](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ServiceQuotas.html)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [SQLite PRAGMA synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous)
- [12-Factor App Config](https://12factor.net/config)
