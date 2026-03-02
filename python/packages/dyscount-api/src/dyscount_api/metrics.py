"""Prometheus metrics endpoint for dyscount-api."""

from prometheus_client import Counter, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response

# Create router for metrics endpoint
router = APIRouter()

# Define metrics
# Table info
TABLE_INFO = Info("dyscount_table", "Table metadata")

# Operation counters
OPERATION_COUNTER = Counter(
    "dyscount_operations_total",
    "Total number of DynamoDB operations",
    ["operation", "table", "status"]
)

# Operation latency
OPERATION_LATENCY = Histogram(
    "dyscount_operation_duration_seconds",
    "Operation latency in seconds",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Error counter
ERROR_COUNTER = Counter(
    "dyscount_errors_total",
    "Total number of errors",
    ["operation", "error_type"]
)

# Table item count gauge (updated via observations)
ITEM_COUNT_COUNTER = Counter(
    "dyscount_table_items_total",
    "Total number of items processed per table",
    ["table", "operation"]
)

# Consumed capacity
CONSUMED_CAPACITY = Counter(
    "dyscount_consumed_capacity_total",
    "Total consumed capacity units",
    ["table", "operation", "capacity_type"]  # capacity_type: read or write
)


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint.
    
    Returns:
        Prometheus-formatted metrics.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def record_operation(operation: str, table: str, status: str = "success") -> None:
    """Record an operation metric.
    
    Args:
        operation: The DynamoDB operation name (e.g., "GetItem", "PutItem")
        table: The table name
        status: "success" or "error"
    """
    OPERATION_COUNTER.labels(
        operation=operation,
        table=table,
        status=status
    ).inc()


def record_error(operation: str, error_type: str) -> None:
    """Record an error metric.
    
    Args:
        operation: The operation that failed
        error_type: The type of error (e.g., "ValidationException", "ResourceNotFoundException")
    """
    ERROR_COUNTER.labels(
        operation=operation,
        error_type=error_type
    ).inc()


def record_latency(operation: str, table: str, duration_seconds: float) -> None:
    """Record operation latency.
    
    Args:
        operation: The operation name
        table: The table name
        duration_seconds: The operation duration in seconds
    """
    OPERATION_LATENCY.labels(
        operation=operation,
        table=table
    ).observe(duration_seconds)


def record_consumed_capacity(table: str, operation: str, read_units: float = 0, write_units: float = 0) -> None:
    """Record consumed capacity.
    
    Args:
        table: The table name
        operation: The operation name
        read_units: Read capacity units consumed
        write_units: Write capacity units consumed
    """
    if read_units > 0:
        CONSUMED_CAPACITY.labels(
            table=table,
            operation=operation,
            capacity_type="read"
        ).inc(read_units)
    
    if write_units > 0:
        CONSUMED_CAPACITY.labels(
            table=table,
            operation=operation,
            capacity_type="write"
        ).inc(write_units)


def record_item_count(table: str, operation: str, count: int = 1) -> None:
    """Record item count for operations.
    
    Args:
        table: The table name
        operation: The operation name (e.g., "PutItem", "DeleteItem")
        count: Number of items processed
    """
    ITEM_COUNT_COUNTER.labels(
        table=table,
        operation=operation
    ).inc(count)
