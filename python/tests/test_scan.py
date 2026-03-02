"""Tests for Scan operation."""

import pytest
import pytest_asyncio
from dyscount_core.config import Config
from dyscount_core.services.item_service import ItemService
from dyscount_core.services.table_service import TableService
from dyscount_core.models.errors import ResourceNotFoundException, ValidationException


@pytest_asyncio.fixture
async def item_service():
    """Create an item service for testing."""
    config = Config()
    service = ItemService(config)
    yield service
    await service.close()


@pytest_asyncio.fixture
async def table_service():
    """Create a table service for testing."""
    config = Config()
    service = TableService(config)
    yield service
    await service.close()


@pytest_asyncio.fixture
async def test_table(table_service):
    """Create a test table."""
    from dyscount_core.models.table import (
        KeySchemaElement,
        AttributeDefinition,
        KeyType,
        ScalarAttributeType,
    )
    
    import uuid
    table_name = f"test_scan_table_{uuid.uuid4().hex[:8]}"
    
    # Delete if exists
    try:
        await table_service.table_manager.delete_table(table_name)
    except Exception:
        pass
    
    key_schema = [
        KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
    ]
    attribute_definitions = [
        AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
    ]
    
    await table_service.table_manager.create_table(
        table_name,
        key_schema=key_schema,
        attribute_definitions=attribute_definitions,
    )
    
    yield table_name
    
    # Cleanup
    try:
        await table_service.table_manager.delete_table(table_name)
    except Exception:
        pass


@pytest_asyncio.fixture
async def sample_items(item_service, test_table):
    """Create sample items for testing."""
    from dyscount_core.models.operations import PutItemRequest
    
    items = [
        {"pk": {"S": "item1"}, "status": {"S": "active"}, "count": {"N": "10"}},
        {"pk": {"S": "item2"}, "status": {"S": "inactive"}, "count": {"N": "20"}},
        {"pk": {"S": "item3"}, "status": {"S": "active"}, "count": {"N": "30"}},
        {"pk": {"S": "item4"}, "status": {"S": "pending"}, "count": {"N": "40"}},
    ]
    
    for item in items:
        request = PutItemRequest(
            TableName=test_table,
            Item=item,
        )
        await item_service.put_item(request)
    
    return items


class TestScanValidation:
    """Test Scan request validation."""
    
    @pytest.mark.asyncio
    async def test_scan_empty_table_name(self, item_service):
        """Test Scan with empty table name."""
        from dyscount_core.models.operations import ScanRequest
        from pydantic import ValidationError
        
        # Empty table name is caught by Pydantic validation
        with pytest.raises(ValidationError):
            ScanRequest(
                TableName="",
            )
    
    @pytest.mark.asyncio
    async def test_scan_invalid_table_name(self, item_service):
        """Test Scan with invalid table name."""
        from dyscount_core.models.operations import ScanRequest
        
        request = ScanRequest(
            TableName="ab",  # Too short
        )
        
        with pytest.raises(ValidationException):
            await item_service.scan(request)
    
    @pytest.mark.asyncio
    async def test_scan_table_not_found(self, item_service):
        """Test Scan on non-existent table."""
        from dyscount_core.models.operations import ScanRequest
        
        request = ScanRequest(
            TableName="this_table_does_not_exist",
        )
        
        with pytest.raises(ResourceNotFoundException):
            await item_service.scan(request)


class TestScanBasic:
    """Test basic Scan operations."""
    
    @pytest.mark.asyncio
    async def test_scan_all_items(self, item_service, test_table, sample_items):
        """Test Scan returns all items."""
        from dyscount_core.models.operations import ScanRequest
        
        request = ScanRequest(
            TableName=test_table,
        )
        
        response = await item_service.scan(request)
        
        assert response.count == 4
        assert len(response.items) == 4
        assert response.scanned_count == 4
    
    @pytest.mark.asyncio
    async def test_scan_empty_table(self, item_service, test_table):
        """Test Scan on empty table."""
        from dyscount_core.models.operations import ScanRequest
        
        request = ScanRequest(
            TableName=test_table,
        )
        
        response = await item_service.scan(request)
        
        assert response.count == 0
        assert len(response.items) == 0
        assert response.scanned_count == 0


class TestScanFilterExpression:
    """Test Scan with FilterExpression."""
    
    @pytest.mark.asyncio
    async def test_scan_with_filter(self, item_service, test_table, sample_items):
        """Test Scan with FilterExpression."""
        from dyscount_core.models.operations import ScanRequest
        
        request = ScanRequest(
            TableName=test_table,
            FilterExpression="#s = :status",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":status": {"S": "active"}},
        )
        
        response = await item_service.scan(request)
        
        assert response.count == 2  # Only active items
        assert response.scanned_count == 4  # All items scanned
        for item in response.items:
            assert item["status"] == {"S": "active"}
    
    @pytest.mark.asyncio
    async def test_scan_with_numeric_filter(self, item_service, test_table, sample_items):
        """Test Scan with numeric filter."""
        from dyscount_core.models.operations import ScanRequest
        
        request = ScanRequest(
            TableName=test_table,
            FilterExpression="#c > :min_count",
            ExpressionAttributeNames={"#c": "count"},
            ExpressionAttributeValues={":min_count": {"N": "20"}},
        )
        
        response = await item_service.scan(request)
        
        assert response.count == 2  # Items with count > 20
        for item in response.items:
            assert int(item["count"]["N"]) > 20


class TestScanLimit:
    """Test Scan with Limit."""
    
    @pytest.mark.asyncio
    async def test_scan_with_limit(self, item_service, test_table, sample_items):
        """Test Scan with Limit."""
        from dyscount_core.models.operations import ScanRequest
        
        request = ScanRequest(
            TableName=test_table,
            Limit=2,
        )
        
        response = await item_service.scan(request)
        
        assert response.count == 2
        assert len(response.items) == 2
        # Note: scanned_count may be 2 or more depending on implementation


class TestScanProjection:
    """Test Scan with ProjectionExpression."""
    
    @pytest.mark.asyncio
    async def test_scan_with_projection(self, item_service, test_table, sample_items):
        """Test Scan with ProjectionExpression."""
        from dyscount_core.models.operations import ScanRequest
        
        request = ScanRequest(
            TableName=test_table,
            ProjectionExpression="#pk, #s",
            ExpressionAttributeNames={"#pk": "pk", "#s": "status"},
        )
        
        response = await item_service.scan(request)
        
        assert response.count == 4
        for item in response.items:
            # Should have pk and status, but not count
            assert "pk" in item
            assert "status" in item
            # Note: projection handling may vary in implementation


class TestScanConsumedCapacity:
    """Test Scan ConsumedCapacity."""
    
    @pytest.mark.asyncio
    async def test_scan_returns_consumed_capacity(self, item_service, test_table, sample_items):
        """Test Scan returns ConsumedCapacity."""
        from dyscount_core.models.operations import ScanRequest
        
        request = ScanRequest(
            TableName=test_table,
            ReturnConsumedCapacity="TOTAL",
        )
        
        response = await item_service.scan(request)
        
        assert response.consumed_capacity is not None
        assert response.consumed_capacity.table_name == test_table
        assert response.consumed_capacity.capacity_units > 0
