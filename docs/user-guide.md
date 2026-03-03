# Dyscount User Guide

Dyscount is a DynamoDB-compatible API service that runs locally, backed by SQLite. It provides a drop-in replacement for DynamoDB Local that's faster, easier to use, and more feature-complete.

## Quick Start

### Using Docker

```bash
# Run Dyscount
docker run -p 8000:8000 dyscount:latest

# With persistent storage
docker run -p 8000:8000 -v dyscount-data:/data dyscount:latest
```

### Using Python

```bash
# Install
pip install dyscount

# Start server
dyscount serve --port 8000
```

### Using Docker Compose

```yaml
version: '3.8'
services:
  dynamodb:
    image: dyscount:latest
    ports:
      - "8000:8000"
    volumes:
      - dyscount-data:/data
    environment:
      - DYSCOUNT_STORAGE__DATA_DIRECTORY=/data

volumes:
  dyscount-data:
```

## First Steps

### Create a Table

```python
import boto3

# Connect to Dyscount
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='eu-west-1',
    aws_access_key_id='local',
    aws_secret_access_key='local'
)

# Create a table
table = dynamodb.create_table(
    TableName='Users',
    KeySchema=[
        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
    ],
    AttributeDefinitions=[
        {'AttributeName': 'user_id', 'AttributeType': 'S'},
    ],
    BillingMode='PAY_PER_REQUEST'
)

# Wait for table to be created
table.wait_until_exists()
print(f"Table created: {table.table_name}")
```

### Put and Get Items

```python
# Put an item
table.put_item(Item={
    'user_id': 'user123',
    'name': 'Alice',
    'email': 'alice@example.com',
    'age': 30
})

# Get an item
response = table.get_item(Key={'user_id': 'user123'})
item = response.get('Item')
print(f"Retrieved: {item}")
```

### Query Items

```python
# Create a table with sort key
table = dynamodb.create_table(
    TableName='Orders',
    KeySchema=[
        {'AttributeName': 'customer_id', 'KeyType': 'HASH'},
        {'AttributeName': 'order_date', 'KeyType': 'RANGE'},
    ],
    AttributeDefinitions=[
        {'AttributeName': 'customer_id', 'AttributeType': 'S'},
        {'AttributeName': 'order_date', 'AttributeType': 'S'},
    ],
    BillingMode='PAY_PER_REQUEST'
)

# Query items
response = table.query(
    KeyConditionExpression=Key('customer_id').eq('cust456')
)
items = response['Items']
print(f"Found {len(items)} orders")
```

## Configuration

Dyscount can be configured via:

1. **Environment variables** (highest priority)
2. **Configuration file** (`dyscount.json`)
3. **Defaults** (lowest priority)

### Environment Variables

```bash
# Server settings
export DYSCOUNT_SERVER__PORT=8000
export DYSCOUNT_SERVER__HOST=0.0.0.0

# Storage settings
export DYSCOUNT_STORAGE__DATA_DIRECTORY=/var/lib/dyscount
export DYSCOUNT_STORAGE__NAMESPACE=production

# Auth settings
export DYSCOUNT_AUTH__MODE=local

# Logging
export DYSCOUNT_LOGGING__LEVEL=info
export DYSCOUNT_LOGGING__FORMAT=json
```

### Configuration File

Create `dyscount.json`:

```json
{
  "server": {
    "port": 8000,
    "host": "0.0.0.0"
  },
  "storage": {
    "data_directory": "/var/lib/dyscount",
    "namespace": "default"
  },
  "auth": {
    "mode": "local"
  },
  "logging": {
    "level": "info",
    "format": "json"
  },
  "metrics": {
    "prometheus_enabled": true,
    "prometheus_port": 9090
  }
}
```

## Features

### Core Operations

- ✅ **Control Plane**: CreateTable, DeleteTable, ListTables, DescribeTable, UpdateTable
- ✅ **Data Plane**: GetItem, PutItem, UpdateItem, DeleteItem, Query, Scan
- ✅ **Batch Operations**: BatchGetItem, BatchWriteItem
- ✅ **Transactions**: TransactGetItems, TransactWriteItems
- ✅ **Expressions**: ConditionExpression, FilterExpression, KeyConditionExpression, UpdateExpression

### Advanced Features

- ✅ **TTL**: Automatic item expiration
- ✅ **GSI/LSI**: Global and Local Secondary Indexes
- ✅ **Backup/Restore**: Point-in-time recovery
- ✅ **PartiQL**: SQL-compatible query language
- ✅ **Import/Export**: Data migration tools

### Operations & Monitoring

- ✅ **Prometheus Metrics**: `/metrics` endpoint
- ✅ **Structured Logging**: JSON format
- ✅ **Health Checks**: Built-in health endpoint
- ✅ **Docker Support**: Ready-to-use container

## AWS SDK Compatibility

Dyscount works with all AWS SDKs:

### Python (boto3)

```python
import boto3

dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='eu-west-1',
    aws_access_key_id='local',
    aws_secret_access_key='local'
)
```

### AWS CLI

```bash
aws dynamodb list-tables \
  --endpoint-url http://localhost:8000 \
  --region eu-west-1
```

### Node.js

```javascript
const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');

const client = new DynamoDBClient({
  endpoint: 'http://localhost:8000',
  region: 'eu-west-1',
  credentials: {
    accessKeyId: 'local',
    secretAccessKey: 'local'
  }
});
```

## Performance

Dyscount is designed for high performance:

| Operation | Latency (p99) | Throughput |
|-----------|--------------|------------|
| GetItem | < 1ms | 5,000+ ops/s |
| PutItem | < 1ms | 2,000+ ops/s |
| Query | < 5ms | 3,000+ ops/s |
| Scan | < 1ms | 3,500+ ops/s |

See [benchmarks](../python/benchmarks/) for detailed performance metrics.

## Migration from DynamoDB Local

Dyscount is a drop-in replacement for DynamoDB Local:

1. **Same endpoint**: `http://localhost:8000`
2. **Same API**: All DynamoDB operations work identically
3. **Better performance**: SQLite backend is faster than DynamoDB Local's implementation
4. **More features**: TTL, backup/restore, PartiQL support

Simply change your endpoint URL:

```python
# Before (DynamoDB Local)
endpoint_url='http://localhost:8000'

# After (Dyscount) - same URL!
endpoint_url='http://localhost:8000'
```

## Troubleshooting

### Connection Refused

```
Connection refused: localhost:8000
```

**Solution**: Ensure Dyscount is running:
```bash
docker ps  # Check if container is running
dyscount serve  # Or start the server
```

### Table Already Exists

```
ResourceInUseException: Table already exists
```

**Solution**: Delete the table first or use `CreateTable` with `if not exists` logic.

### Item Too Large

```
ValidationException: Item size has exceeded the maximum allowed size
```

**Solution**: DynamoDB has a 400KB limit per item. Reduce item size or split into multiple items.

## Next Steps

- Read the [API Reference](api-reference.md) for all supported operations
- Check the [Configuration Guide](configuration.md) for advanced settings
- See [Docker Usage](docker.md) for container deployment
- Review [Examples](examples/) for code samples in multiple languages
