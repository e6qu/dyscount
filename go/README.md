# Dyscount Go Implementation

A DynamoDB-compatible API service written in Go using Gin framework and SQLite.

## Quick Start

```bash
# Install dependencies
go mod download

# Run the server
cd src
go run main.go

# Or build and run
cd src
go build -o dyscount main.go
./dyscount
```

## Configuration

Configuration is done via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DYSCOUNT_SERVER_HOST` | `0.0.0.0` | HTTP server host |
| `DYSCOUNT_SERVER_PORT` | `8000` | HTTP server port |
| `DYSCOUNT_SERVER_MODE` | `debug` | Gin mode (`debug` or `release`) |
| `DYSCOUNT_STORAGE_DATA_DIRECTORY` | `./data` | SQLite data directory |
| `DYSCOUNT_STORAGE_NAMESPACE` | `default` | Namespace for table isolation |
| `DYSCOUNT_AUTH_MODE` | `local` | Auth mode (`local` or `production`) |
| `DYSCOUNT_LOGGING_LEVEL` | `info` | Log level |
| `DYSCOUNT_METRICS_ENABLED` | `true` | Enable Prometheus metrics |

## API Endpoints

- `POST /` - DynamoDB API endpoint (requires `X-Amz-Target` header)
- `GET /metrics` - Prometheus metrics
- `GET /health` - Health check
- `GET /swagger/*any` - API documentation

## Implemented Operations

### Control Plane
- ✅ CreateTable
- ✅ DeleteTable
- ✅ ListTables
- ✅ DescribeTable
- ✅ DescribeEndpoints
- ✅ TagResource (stub)
- ✅ UntagResource (stub)
- ✅ ListTagsOfResource (stub)

## Project Structure

```
src/
├── main.go                      # Entry point
├── internal/
│   ├── config/
│   │   └── config.go            # Configuration management
│   ├── handlers/
│   │   └── dynamodb.go          # HTTP handlers
│   ├── models/
│   │   ├── table.go             # Data models
│   │   └── operations.go        # Request/response models
│   └── storage/
│       └── table_manager.go     # SQLite storage layer
```

## Testing

```bash
cd src
go test ./...
```

## Architecture

The Go implementation mirrors the Python reference implementation:

1. **HTTP Layer**: Gin framework handles routing and middleware
2. **Handler Layer**: Routes DynamoDB operations to appropriate handlers
3. **Storage Layer**: SQLite with one database file per table
4. **Models**: Go structs matching DynamoDB API types

## Differences from Python Implementation

- Uses Gin instead of FastAPI
- Uses mattn/go-sqlite3 (CGO) instead of aiosqlite
- Synchronous request handling (no async/await)
- Swagger docs generated from code comments
- Prometheus metrics built-in
