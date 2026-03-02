"""Tests for BatchWriteItem operation."""

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
    table_name = f"test_batch_write_{uuid.uuid4().hex[:8]}"
    
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


class TestBatchWriteItem:
    """Test BatchWriteItem operation."""
    
    @pytest.mark.asyncio
    async def test_batch_write_put_single_item(self, item_service, test_table):
        """Test BatchWriteItem with single put."""
        from dyscount_core.models.operations import (
            BatchWriteItemRequest, BatchWriteItemTableRequest,
            PutRequest
        )
        
        request = BatchWriteItemRequest(
            RequestItems={
                test_table: [
                    BatchWriteItemTableRequest(
                        PutRequest=PutRequest(
                            Item={"pk": {"S": "new_item"}, "data": {"S": "value"}},
                        ),
                    ),
                ],
            },
        )
        
        response = await item_service.batch_write_item(request)
        
        # Verify item was written
        from dyscount_core.models.operations import GetItemRequest
        get_response = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "new_item"}},
        ))
        assert get_response.item is not None
        assert get_response.item["data"] == {"S": "value"}
    
    @pytest.mark.asyncio
    async def test_batch_write_put_multiple_items(self, item_service, test_table):
        """Test BatchWriteItem with multiple puts."""
        from dyscount_core.models.operations import (
            BatchWriteItemRequest, BatchWriteItemTableRequest,
            PutRequest
        )
        
        request = BatchWriteItemRequest(
            RequestItems={
                test_table: [
                    BatchWriteItemTableRequest(
                        PutRequest=PutRequest(
                            Item={"pk": {"S": "item1"}, "data": {"S": "value1"}},
                        ),
                    ),
                    BatchWriteItemTableRequest(
                        PutRequest=PutRequest(
                            Item={"pk": {"S": "item2"}, "data": {"S": "value2"}},
                        ),
                    ),
                ],
            },
        )
        
        response = await item_service.batch_write_item(request)
        
        # Verify both items were written
        from dyscount_core.models.operations import GetItemRequest
        get1 = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "item1"}},
        ))
        get2 = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "item2"}},
        ))
        assert get1.item is not None
        assert get2.item is not None
    
    @pytest.mark.asyncio
    async def test_batch_write_delete_item(self, item_service, test_table):
        """Test BatchWriteItem with delete."""
        from dyscount_core.models.operations import (
            BatchWriteItemRequest, BatchWriteItemTableRequest,
            PutRequest, DeleteRequest, GetItemRequest
        )
        
        # First put an item
        await item_service.batch_write_item(BatchWriteItemRequest(
            RequestItems={
                test_table: [
                    BatchWriteItemTableRequest(
                        PutRequest=PutRequest(
                            Item={"pk": {"S": "to_delete"}, "data": {"S": "temp"}},
                        ),
                    ),
                ],
            },
        ))
        
        # Now delete it
        request = BatchWriteItemRequest(
            RequestItems={
                test_table: [
                    BatchWriteItemTableRequest(
                        DeleteRequest=DeleteRequest(
                            Key={"pk": {"S": "to_delete"}},
                        ),
                    ),
                ],
            },
        )
        
        response = await item_service.batch_write_item(request)
        
        # Verify item was deleted
        get_response = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "to_delete"}},
        ))
        assert get_response.item is None
    
    @pytest.mark.asyncio
    async def test_batch_write_put_and_delete(self, item_service, test_table):
        """Test BatchWriteItem with both put and delete."""
        from dyscount_core.models.operations import (
            BatchWriteItemRequest, BatchWriteItemTableRequest,
            PutRequest, DeleteRequest, GetItemRequest
        )
        
        # First put an item to delete
        await item_service.batch_write_item(BatchWriteItemRequest(
            RequestItems={
                test_table: [
                    BatchWriteItemTableRequest(
                        PutRequest=PutRequest(
                            Item={"pk": {"S": "old_item"}, "data": {"S": "old"}},
                        ),
                    ),
                ],
            },
        ))
        
        # Put new item and delete old one
        request = BatchWriteItemRequest(
            RequestItems={
                test_table: [
                    BatchWriteItemTableRequest(
                        PutRequest=PutRequest(
                            Item={"pk": {"S": "new_item"}, "data": {"S": "new"}},
                        ),
                    ),
                    BatchWriteItemTableRequest(
                        DeleteRequest=DeleteRequest(
                            Key={"pk": {"S": "old_item"}},
                        ),
                    ),
                ],
            },
        )
        
        response = await item_service.batch_write_item(request)
        
        # Verify
        new_item = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "new_item"}},
        ))
        old_item = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "old_item"}},
        ))
        assert new_item.item is not None
        assert old_item.item is None
    
    @pytest.mark.asyncio
    async def test_batch_write_table_not_found(self, item_service):
        """Test BatchWriteItem with non-existent table."""
        from dyscount_core.models.operations import (
            BatchWriteItemRequest, BatchWriteItemTableRequest,
            PutRequest
        )
        
        request = BatchWriteItemRequest(
            RequestItems={
                "nonexistent_table": [
                    BatchWriteItemTableRequest(
                        PutRequest=PutRequest(
                            Item={"pk": {"S": "item"}, "data": {"S": "value"}},
                        ),
                    ),
                ],
            },
        )
        
        with pytest.raises(ResourceNotFoundException):
            await item_service.batch_write_item(request)
    
    @pytest.mark.asyncio
    async def test_batch_write_returns_consumed_capacity(self, item_service, test_table):
        """Test BatchWriteItem returns ConsumedCapacity."""
        from dyscount_core.models.operations import (
            BatchWriteItemRequest, BatchWriteItemTableRequest,
            PutRequest
        )
        
        request = BatchWriteItemRequest(
            RequestItems={
                test_table: [
                    BatchWriteItemTableRequest(
                        PutRequest=PutRequest(
                            Item={"pk": {"S": "item1"}, "data": {"S": "value1"}},
                        ),
                    ),
                    BatchWriteItemTableRequest(
                        PutRequest=PutRequest(
                            Item={"pk": {"S": "item2"}, "data": {"S": "value2"}},
                        ),
                    ),
                ],
            },
            ReturnConsumedCapacity="TOTAL",
        )
        
        response = await item_service.batch_write_item(request)
        
        assert response.consumed_capacity is not None
        assert len(response.consumed_capacity) > 0
