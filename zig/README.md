# Dyscount Zig Implementation

DynamoDB-compatible API service written in Zig.

## Features

### Control Plane Operations
- ✅ CreateTable - Create new tables
- ✅ DeleteTable - Delete existing tables
- ✅ ListTables - List all tables in namespace
- ✅ DescribeTable - Get table metadata
- ✅ DescribeEndpoints - Get endpoint information

### Architecture

Zig's performance and memory safety make it ideal for high-throughput database operations:

```
┌─────────────────┐
│  HTTP Server    │  Raw TCP socket handling
│  (Port 8000)    │
└────────┬────────┘
         │
┌────────▼────────┐
│    Server       │  Request routing & JSON parsing
│   (Router)      │
└────────┬────────┘
         │
┌────────▼────────┐
│ TableManager    │  SQLite C bindings
│ (data/{ns}/*.db)│
└─────────────────┘
```

## Prerequisites

- Zig 0.12+ (master/nightly recommended)
- SQLite3 development libraries

### macOS
```bash
brew install zig sqlite3
```

### Ubuntu/Debian
```bash
sudo apt-get install zig libsqlite3-dev
```

## Build

```bash
cd zig
zig build
```

## Run

```bash
# Run with default settings
zig build run

# Or run the binary directly
./zig-out/bin/dyscount
```

## Test

```bash
zig build test
```

## API Usage

### Create a Table

```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -H "X-Amz-Target: DynamoDB_20120810.CreateTable" \
  -d '{
    "TableName": "Users"
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

## Project Structure

```
zig/
├── build.zig
├── README.md
└── src/
    ├── main.zig      # HTTP server and request routing
    ├── models.zig    # DynamoDB data structures
    └── storage.zig   # SQLite-backed storage
```

## Key Design Decisions

1. **Manual Memory Management**: Explicit allocator usage throughout
2. **C Interop**: Direct SQLite C library bindings
3. **Zero-cost Abstractions**: Minimal runtime overhead
4. **Compile-time Safety**: Leverage Zig's comptime features

## License

AGPL-3.0 - See repository root for full license text.
