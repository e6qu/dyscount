"""Performance benchmarks for Dyscount operations.

Measures latency for various DynamoDB operations at different table sizes.
"""

import asyncio
import random
import statistics
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
import tempfile
import os

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dyscount_core.config import Config, StorageSettings, ServerSettings, AuthSettings, LoggingSettings
from dyscount_core.services.table_service import TableService
from dyscount_core.services.item_service import ItemService
from dyscount_core.models.operations import (
    CreateTableRequest,
    PutItemRequest,
    GetItemRequest,
    QueryRequest,
    ScanRequest,
    DeleteItemRequest,
    UpdateItemRequest,
)
from dyscount_core.models.table import (
    AttributeDefinition,
    KeySchemaElement,
    ScalarAttributeType,
    KeyType,
)


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    operation: str
    table_size: int
    iterations: int
    mean_ms: float
    median_ms: float
    p50_ms: float
    p90_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float
    ops_per_second: float

    def __str__(self) -> str:
        return (
            f"{self.operation} (table_size={self.table_size}, n={self.iterations}): "
            f"mean={self.mean_ms:.2f}ms, p50={self.p50_ms:.2f}ms, "
            f"p99={self.p99_ms:.2f}ms, ops/s={self.ops_per_second:.0f}"
        )


class LatencyBenchmark:
    """Benchmark operation latency."""
    
    def __init__(self, config: Config):
        self.config = config
        self.table_service = TableService(config)
        self.item_service = ItemService(config)
        self.results: List[BenchmarkResult] = []
    
    async def setup(self):
        """Initialize services."""
        pass  # Services are initialized in __init__
    
    async def cleanup(self):
        """Clean up services."""
        await self.table_service.close()
        await self.item_service.close()
    
    async def create_benchmark_table(self, table_name: str, num_items: int = 0) -> str:
        """Create a table and optionally populate it with items."""
        # Create table
        create_request = CreateTableRequest(
            TableName=table_name,
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="pk",
                    AttributeType=ScalarAttributeType.STRING,
                ),
                AttributeDefinition(
                    AttributeName="sk",
                    AttributeType=ScalarAttributeType.STRING,
                ),
            ],
            KeySchema=[
                KeySchemaElement(
                    AttributeName="pk",
                    KeyType=KeyType.HASH,
                ),
                KeySchemaElement(
                    AttributeName="sk",
                    KeyType=KeyType.RANGE,
                ),
            ],
        )
        
        try:
            await self.table_service.create_table(create_request)
        except Exception:
            pass  # Table may already exist
        
        # Populate with items
        if num_items > 0:
            for i in range(num_items):
                put_request = PutItemRequest(
                    TableName=table_name,
                    Item={
                        "pk": {"S": f"user{i % 100}"},  # 100 partition keys
                        "sk": {"S": f"item{i}"},
                        "data": {"S": f"data_{i}" * 10},  # ~100 bytes per item
                        "timestamp": {"N": str(int(time.time()))},
                    },
                )
                await self.item_service.put_item(put_request)
        
        return table_name
    
    async def benchmark_getitem(
        self,
        table_name: str,
        table_size: int,
        iterations: int = 1000,
    ) -> BenchmarkResult:
        """Benchmark GetItem operation."""
        times: List[float] = []
        
        for _ in range(iterations):
            key = random.randint(0, table_size - 1)
            get_request = GetItemRequest(
                TableName=table_name,
                Key={
                    "pk": {"S": f"user{key % 100}"},
                    "sk": {"S": f"item{key}"},
                },
            )
            
            start = time.perf_counter()
            await self.item_service.get_item(get_request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)
        
        return self._compute_stats("GetItem", table_size, iterations, times)
    
    async def benchmark_putitem(
        self,
        table_name: str,
        table_size: int,
        iterations: int = 1000,
    ) -> BenchmarkResult:
        """Benchmark PutItem operation."""
        times: List[float] = []
        
        for i in range(iterations):
            put_request = PutItemRequest(
                TableName=table_name,
                Item={
                    "pk": {"S": f"bench{i}"},
                    "sk": {"S": f"item{i}"},
                    "data": {"S": f"benchmark_data_{i}" * 10},
                    "timestamp": {"N": str(int(time.time()))},
                },
            )
            
            start = time.perf_counter()
            await self.item_service.put_item(put_request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)
        
        return self._compute_stats("PutItem", table_size, iterations, times)
    
    async def benchmark_query(
        self,
        table_name: str,
        table_size: int,
        iterations: int = 1000,
    ) -> BenchmarkResult:
        """Benchmark Query operation."""
        times: List[float] = []
        
        for _ in range(iterations):
            partition = random.randint(0, 99)  # 100 partitions
            query_request = QueryRequest(
                TableName=table_name,
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": {"S": f"user{partition}"}},
            )
            
            start = time.perf_counter()
            await self.item_service.query(query_request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)
        
        return self._compute_stats("Query", table_size, iterations, times)
    
    async def benchmark_scan(
        self,
        table_name: str,
        table_size: int,
        iterations: int = 100,
    ) -> BenchmarkResult:
        """Benchmark Scan operation."""
        times: List[float] = []
        
        for _ in range(iterations):
            scan_request = ScanRequest(
                TableName=table_name,
                Limit=100,  # Scan 100 items at a time
            )
            
            start = time.perf_counter()
            await self.item_service.scan(scan_request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)
        
        return self._compute_stats("Scan", table_size, iterations, times)
    
    async def benchmark_updateitem(
        self,
        table_name: str,
        table_size: int,
        iterations: int = 1000,
    ) -> BenchmarkResult:
        """Benchmark UpdateItem operation."""
        times: List[float] = []
        
        for _ in range(iterations):
            key = random.randint(0, min(table_size - 1, 10000))
            update_request = UpdateItemRequest(
                TableName=table_name,
                Key={
                    "pk": {"S": f"user{key % 100}"},
                    "sk": {"S": f"item{key}"},
                },
                UpdateExpression="SET #d = :d",
                ExpressionAttributeNames={"#d": "data"},
                ExpressionAttributeValues={":d": {"S": f"updated_{time.time()}"}},
            )
            
            start = time.perf_counter()
            try:
                await self.item_service.update_item(update_request)
            except Exception:
                pass  # Item may not exist
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)
        
        return self._compute_stats("UpdateItem", table_size, iterations, times)
    
    async def benchmark_deleteitem(
        self,
        table_name: str,
        table_size: int,
        iterations: int = 1000,
    ) -> BenchmarkResult:
        """Benchmark DeleteItem operation."""
        times: List[float] = []
        
        for i in range(iterations):
            delete_request = DeleteItemRequest(
                TableName=table_name,
                Key={
                    "pk": {"S": f"delbench{i}"},
                    "sk": {"S": f"item{i}"},
                },
            )
            
            start = time.perf_counter()
            await self.item_service.delete_item(delete_request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)
        
        return self._compute_stats("DeleteItem", table_size, iterations, times)
    
    def _compute_stats(
        self,
        operation: str,
        table_size: int,
        iterations: int,
        times: List[float],
    ) -> BenchmarkResult:
        """Compute statistics from timing data."""
        sorted_times = sorted(times)
        n = len(sorted_times)
        
        mean = statistics.mean(times)
        median = statistics.median(times)
        p50 = sorted_times[int(n * 0.50)]
        p90 = sorted_times[int(n * 0.90)]
        p99 = sorted_times[int(n * 0.99)]
        min_val = min(times)
        max_val = max(times)
        std_dev = statistics.stdev(times) if n > 1 else 0
        ops_per_sec = 1000 / mean if mean > 0 else 0
        
        return BenchmarkResult(
            operation=operation,
            table_size=table_size,
            iterations=iterations,
            mean_ms=mean,
            median_ms=median,
            p50_ms=p50,
            p90_ms=p90,
            p99_ms=p99,
            min_ms=min_val,
            max_ms=max_val,
            std_dev_ms=std_dev,
            ops_per_second=ops_per_sec,
        )
    
    async def run_full_benchmark(self) -> List[BenchmarkResult]:
        """Run complete benchmark suite."""
        table_sizes = [100, 1000, 10000, 100000]
        results = []
        
        for size in table_sizes:
            print(f"\n{'='*60}")
            print(f"Benchmarking with table size: {size:,} items")
            print(f"{'='*60}")
            
            table_name = f"BenchmarkTable_{size}"
            await self.create_benchmark_table(table_name, size)
            
            # Benchmark GetItem
            print(f"  Running GetItem benchmark...")
            result = await self.benchmark_getitem(table_name, size, 1000)
            results.append(result)
            print(f"    {result}")
            
            # Benchmark PutItem
            print(f"  Running PutItem benchmark...")
            result = await self.benchmark_putitem(f"{table_name}_put", 0, 1000)
            results.append(result)
            print(f"    {result}")
            
            # Benchmark Query
            print(f"  Running Query benchmark...")
            result = await self.benchmark_query(table_name, size, 1000)
            results.append(result)
            print(f"    {result}")
            
            # Benchmark Scan (fewer iterations)
            print(f"  Running Scan benchmark...")
            result = await self.benchmark_scan(table_name, size, 100)
            results.append(result)
            print(f"    {result}")
            
            # Benchmark UpdateItem
            print(f"  Running UpdateItem benchmark...")
            result = await self.benchmark_updateitem(table_name, size, 1000)
            results.append(result)
            print(f"    {result}")
            
            # Benchmark DeleteItem
            print(f"  Running DeleteItem benchmark...")
            result = await self.benchmark_deleteitem(table_name, size, 1000)
            results.append(result)
            print(f"    {result}")
        
        return results


async def main():
    """Run benchmarks."""
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Using temporary directory: {tmpdir}")
        
        config = Config(
            server=ServerSettings(host="localhost", port=8000),
            storage=StorageSettings(data_directory=tmpdir, namespace="bench"),
            auth=AuthSettings(mode="local"),
            logging=LoggingSettings(level="warn", format="json"),
        )
        
        benchmark = LatencyBenchmark(config)
        
        try:
            start_time = time.time()
            results = await benchmark.run_full_benchmark()
            elapsed = time.time() - start_time
            
            print(f"\n{'='*60}")
            print(f"Benchmark Complete (total time: {elapsed:.1f}s)")
            print(f"{'='*60}\n")
            
            # Print summary table
            print(f"{'Operation':<15} {'Size':<10} {'Mean (ms)':<12} {'P99 (ms)':<12} {'Ops/s':<10}")
            print("-" * 65)
            for r in results:
                print(f"{r.operation:<15} {r.table_size:<10,} {r.mean_ms:<12.2f} {r.p99_ms:<12.2f} {r.ops_per_second:<10.0f}")
            
            # Check if performance meets targets
            print(f"\n{'='*60}")
            print("Performance Targets Check")
            print(f"{'='*60}")
            
            all_pass = True
            for r in results:
                if r.operation == "Query" and r.p99_ms > 10:
                    print(f"  ⚠️  {r.operation} p99 {r.p99_ms:.2f}ms exceeds 10ms target")
                    all_pass = False
                elif r.operation == "GetItem" and r.p99_ms > 10:
                    print(f"  ⚠️  {r.operation} p99 {r.p99_ms:.2f}ms exceeds 10ms target")
                    all_pass = False
                elif r.operation == "PutItem" and r.p99_ms > 10:
                    print(f"  ⚠️  {r.operation} p99 {r.p99_ms:.2f}ms exceeds 10ms target")
                    all_pass = False
            
            if all_pass:
                print("  ✅ All performance targets met!")
            
        finally:
            await benchmark.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
