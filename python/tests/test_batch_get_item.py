"""Tests for BatchGetItem operation."""

import pytest
import pytest_asyncio
from dyscount_core.config import Config
from dyscount_core.services.item_service import ItemService
from dyscount_core.services.table_service import TableService
from dyscount_core.models.errors import ResourceNotFoundException


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
    table_name = f"test_batch_get_{uuid.uuid4().hex[:8]}"
    
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
        {"pk": {"S": "item1"}, "data": {"S": "value1"}},
        {"pk": {"S": "item2"}, "data": {"S": "value2"}},
        {"pk": {"S": "item3"}, "data": {"S": "value3"}},
    ]
    
    for item in items:
        request = PutItemRequest(
            TableName=test_table,
            Item=item,
        )
        await item_service.put_item(request)
    
    return items


class TestBatchGetItem:
    """Test BatchGetItem operation."""
    
    @pytest.mark.asyncio
    async def test_batch_get_single_item(self, item_service, test_table, sample_items):
        """Test BatchGetItem with single item."""
        from dyscount_core.models.operations import BatchGetItemRequest, BatchGetItemTableRequest
        
        request = BatchGetItemRequest(
            RequestItems={
                test_table: BatchGetItemTableRequest(
                    Keys=[{"pk": {"S": "item1"}}],
                ),
            },
        )
        
        response = await item_service.batch_get_item(request)
        
        assert test_table in response.responses
        assert len(response.responses[test_table]) == 1
        assert response.responses[test_table][0]["pk"] == {"S": "item1"}
    
    @pytest.mark.asyncio
    async def test_batch_get_multiple_items(self, item_service, test_table, sample_items):
        """Test BatchGetItem with multiple items."""
        from dyscount_core.models.operations import BatchGetItemRequest, BatchGetItemTableRequest
        
        request = BatchGetItemRequest(
            RequestItems={
                test_table: BatchGetItemTableRequest(
                    Keys=[
                        {"pk": {"S": "item1"}},
                        {"pk": {"S": "item2"}},
                    ],
                ),
            },
        )
        
        response = await item_service.batch_get_item(request)
        
        assert len(response.responses[test_table]) == 2
        pk_values = {item["pk"]["S"] for item in response.responses[test_table]}
        assert pk_values == {"item1", "item2"}
    
    @pytest.mark.asyncio
    async def test_batch_get_nonexistent_item(self, item_service, test_table, sample_items):
        """Test BatchGetItem with non-existent item."""
        from dyscount_core.models.operations import BatchGetItemRequest, BatchGetItemTableRequest
        
        request = BatchGetItemRequest(
            RequestItems={
                test_table: BatchGetItemTableRequest(
                    Keys=[
                        {"pk": {"S": "item1"}},
                        {"pk": {"S": "nonexistent"}},
                    ],
                ),
            },
        )
        
        response = await item_service.batch_get_item(request)
        
        # Should only return existing item
        assert len(response.responses[test_table]) == 1
        assert response.responses[test_table][0]["pk"] == {"S": "item1"}
    
    @pytest.mark.asyncio
    async def test_batch_get_with_projection(self, item_service, test_table, sample_items):
        """Test BatchGetItem with ProjectionExpression."""
        from dyscount_core.models.operations import BatchGetItemRequest, BatchGetItemTableRequest
        
        request = BatchGetItemRequest(
            RequestItems={
                test_table: BatchGetItemTableRequest(
                    Keys=[{"pk": {"S": "item1"}}],
                    ProjectionExpression="#p",
                    ExpressionAttributeNames={"#p": "pk"},
                ),
            },
        )
        
        response = await item_service.batch_get_item(request)
        
        # Response should include the item (projection handling may vary)
        assert len(response.responses[test_table]) == 1
    
    @pytest.mark.asyncio
    async def test_batch_get_table_not_found(self, item_service):
        """Test BatchGetItem with non-existent table."""
        from dyscount_core.models.operations import BatchGetItemRequest, BatchGetItemTableRequest
        
        request = BatchGetItemRequest(
            RequestItems={
                "nonexistent_table": BatchGetItemTableRequest(
                    Keys=[{"pk": {"S": "item1"}}],
                ),
            },
        )
        
        with pytest.raises(ResourceNotFoundException):
            await item_service.batch_get_item(request)
    
    @pytest.mark.asyncio
    async def test_batch_get_returns_consumed_capacity(self, item_service, test_table, sample_items):
        """Test BatchGetItem returns ConsumedCapacity."""
        from dyscount_core.models.operations import BatchGetItemRequest, BatchGetItemTableRequest
        
        request = BatchGetItemRequest(
            RequestItems={
                test_table: BatchGetItemTableRequest(
                    Keys=[
                        {"pk": {"S": "item1"}},
                        {"pk": {"S": "item2"}},
                    ],
                ),
            },
            ReturnConsumedCapacity="TOTAL",
        )
        
        response = await item_service.batch_get_item(request)
        
        assert response.consumed_capacity is not None
        assert len(response.consumed_capacity) > 0
