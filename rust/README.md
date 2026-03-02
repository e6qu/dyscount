# Dyscount Rust Implementation

DynamoDB-compatible API service written in Rust using Axum framework.

## Features

### Control Plane Operations
- ✅ CreateTable - Create new tables with configurable key schema
- ✅ DeleteTable - Delete existing tables
- ✅ ListTables - List all tables in the namespace
- ✅ DescribeTable - Get table metadata

### Data Types
- ✅ String (S)
- ✅ Number (N)
- ✅ Binary (B)
- ✅ Boolean (BOOL)
- ✅ Null (NULL)
- ✅ List (L)
- ✅ Map (M)
- ✅ String Set (SS)
- ✅ Number Set (NS)
- ✅ Binary Set (BS)

## Quick Start

### Prerequisites

- Rust 1.75+ with Cargo

### Build

```bash
cd rust
cargo build --release
```

### Run

```bash
# Run with default settings
cargo run

# Run with custom configuration
DYSCOUNT_HOST=0.0.0.0 DYSCOUNT_PORT=8080 cargo run
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DYSCOUNT_HOST` | Server host | `127.0.0.1` |
| `DYSCOUNT_PORT` | Server port | `8000` |
| `DYSCOUNT_DATA_DIR` | Data directory | `./data` |
| `DYSCOUNT_NAMESPACE` | Namespace for tables | `default` |

## API Usage

### Create a Table

```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -H "X-Amz-Target: DynamoDB_20120810.CreateTable" \
  -d '{
    "TableName": "Users",
    "KeySchema": [
      {"AttributeName": "userId", "KeyType": "HASH"}
    ],
    "AttributeDefinitions": [
      {"AttributeName": "userId", "AttributeType": "S"}
    ],
    "BillingMode": "PAY_PER_REQUEST"
  }'
```

### List Tables

```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -H "X-Amz-Target: DynamoDB_20120810.ListTables" \
  -d '{}'
```

### Describe Table

```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -H "X-Amz-Target: DynamoDB_20120810.DescribeTable" \
  -d '{
    "TableName": "Users"
  }'
```

### Delete Table

```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -H "X-Amz-Target: DynamoDB_20120810.DeleteTable" \
  -d '{
    "TableName": "Users"
  }'
```

## Architecture

```
┌─────────────────┐
│   Axum Router   │
│  (HTTP Server)  │
└────────┬────────┘
         │
┌────────▼────────┐
│    Handlers     │
│  (DynamoDB API) │
└────────┬────────┘
         │
┌────────▼────────┐
│ Table Manager   │
│ (SQLite Backend)│
└─────────────────┘
```

## Testing

```bash
# Run all tests
cargo test

# Run with output
cargo test -- --nocapture

# Run specific test
cargo test test_create_table
```

## Project Structure

```
rust/
├── Cargo.toml
├── README.md
└── src/
    ├── main.rs      # Application entry point
    ├── models.rs    # DynamoDB-compatible data models
    ├── storage.rs   # SQLite-backed table storage
    └── handlers.rs  # HTTP API handlers
```

## License

AGPL-3.0 - See repository root for full license text.
