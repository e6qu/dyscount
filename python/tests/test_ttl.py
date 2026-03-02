"""Tests for Time-to-Live (TTL) operations."""

import pytest
import pytest_asyncio
import time
from datetime import datetime, timedelta

from dyscount_core.models.attribute_value import AttributeValue
from dyscount_core.models.operations import (
    UpdateTimeToLiveRequest,
    UpdateTimeToLiveResponse,
    DescribeTimeToLiveRequest,
    DescribeTimeToLiveResponse,
    TimeToLiveSpecification,
    PutItemRequest,
    GetItemRequest,
)
from dyscount_core.models.errors import ResourceNotFoundException, ValidationException
from dyscount_core.services.table_service import TableService
from dyscount_core.ttl_cleanup import TTLCleanupTask
from dyscount_core.config import Config, StorageSettings


@pytest_asyncio.fixture
async def config(tmp_path):
    """Create a test configuration."""
    return Config(
        storage=StorageSettings(
            data_directory=str(tmp_path / "data"),
            namespace="test",
        )
    )


@pytest_asyncio.fixture
async def table_with_ttl(config):
    """Create a table with TTL enabled."""
    service = TableService(config)
    
    # Create table
    from dyscount_core.models.operations import CreateTableRequest
    from dyscount_core.models.table import (
        KeySchemaElement,
        AttributeDefinition,
        KeyType,
        ScalarAttributeType,
    )
    
    create_request = CreateTableRequest(
        TableName="TTLTestTable",
        KeySchema=[
            KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
        ],
        AttributeDefinitions=[
            AttributeDefinition(
                AttributeName="pk",
                AttributeType=ScalarAttributeType.STRING,
            ),
        ],
    )
    
    await service.create_table(create_request)
    
    # Enable TTL
    ttl_request = UpdateTimeToLiveRequest(
        TableName="TTLTestTable",
        TimeToLiveSpecification=TimeToLiveSpecification(
            AttributeName="exp",
            Enabled=True,
        ),
    )
    
    await service.update_time_to_live(ttl_request)
    
    yield service
    
    # Cleanup
    await service.close()


class TestUpdateTimeToLive:
    """Tests for UpdateTimeToLive operation."""
    
    @pytest.mark.asyncio
    async def test_enable_ttl(self, config):
        """Test enabling TTL on a table."""
        service = TableService(config)
        
        # Create table first
        from dyscount_core.models.operations import CreateTableRequest
        from dyscount_core.models.table import (
            KeySchemaElement,
            AttributeDefinition,
            KeyType,
            ScalarAttributeType,
        )
        
        create_request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="pk",
                    AttributeType=ScalarAttributeType.STRING,
                ),
            ],
        )
        
        await service.create_table(create_request)
        
        # Enable TTL
        request = UpdateTimeToLiveRequest(
            TableName="TestTable",
            TimeToLiveSpecification=TimeToLiveSpecification(
                AttributeName="exp",
                Enabled=True,
            ),
        )
        
        response = await service.update_time_to_live(request)
        
        assert response.time_to_live_specification.attribute_name == "exp"
        assert response.time_to_live_specification.enabled is True
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_disable_ttl(self, table_with_ttl):
        """Test disabling TTL on a table."""
        service = table_with_ttl
        
        # Disable TTL
        request = UpdateTimeToLiveRequest(
            TableName="TTLTestTable",
            TimeToLiveSpecification=TimeToLiveSpecification(
                AttributeName="exp",
                Enabled=False,
            ),
        )
        
        response = await service.update_time_to_live(request)
        
        assert response.time_to_live_specification.enabled is False
    
    @pytest.mark.asyncio
    async def test_update_ttl_table_not_found(self, config):
        """Test UpdateTimeToLive on non-existent table."""
        service = TableService(config)
        
        request = UpdateTimeToLiveRequest(
            TableName="NonExistentTable",
            TimeToLiveSpecification=TimeToLiveSpecification(
                AttributeName="exp",
                Enabled=True,
            ),
        )
        
        with pytest.raises(ResourceNotFoundException):
            await service.update_time_to_live(request)
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_update_ttl_empty_attribute(self, config):
        """Test UpdateTimeToLive with empty attribute name."""
        service = TableService(config)
        
        # Create table
        from dyscount_core.models.operations import CreateTableRequest
        from dyscount_core.models.table import (
            KeySchemaElement,
            AttributeDefinition,
            KeyType,
            ScalarAttributeType,
        )
        
        create_request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="pk",
                    AttributeType=ScalarAttributeType.STRING,
                ),
            ],
        )
        
        await service.create_table(create_request)
        
        # Try to enable TTL with empty attribute
        request = UpdateTimeToLiveRequest(
            TableName="TestTable",
            TimeToLiveSpecification=TimeToLiveSpecification(
                AttributeName="",
                Enabled=True,
            ),
        )
        
        with pytest.raises(ValidationException):
            await service.update_time_to_live(request)
        
        await service.close()


class TestDescribeTimeToLive:
    """Tests for DescribeTimeToLive operation."""
    
    @pytest.mark.asyncio
    async def test_describe_ttl_enabled(self, table_with_ttl):
        """Test describing TTL on a table with TTL enabled."""
        service = table_with_ttl
        
        request = DescribeTimeToLiveRequest(TableName="TTLTestTable")
        response = await service.describe_time_to_live(request)
        
        assert response.time_to_live_description.attribute_name == "exp"
        assert response.time_to_live_description.time_to_live_status == "ENABLED"
    
    @pytest.mark.asyncio
    async def test_describe_ttl_disabled(self, config):
        """Test describing TTL on a table without TTL."""
        service = TableService(config)
        
        # Create table without TTL
        from dyscount_core.models.operations import CreateTableRequest
        from dyscount_core.models.table import (
            KeySchemaElement,
            AttributeDefinition,
            KeyType,
            ScalarAttributeType,
        )
        
        create_request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="pk",
                    AttributeType=ScalarAttributeType.STRING,
                ),
            ],
        )
        
        await service.create_table(create_request)
        
        # Describe TTL (should be DISABLED by default)
        request = DescribeTimeToLiveRequest(TableName="TestTable")
        response = await service.describe_time_to_live(request)
        
        assert response.time_to_live_description.attribute_name is None
        assert response.time_to_live_description.time_to_live_status == "DISABLED"
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_describe_ttl_table_not_found(self, config):
        """Test DescribeTimeToLive on non-existent table."""
        service = TableService(config)
        
        request = DescribeTimeToLiveRequest(TableName="NonExistentTable")
        
        with pytest.raises(ResourceNotFoundException):
            await service.describe_time_to_live(request)
        
        await service.close()


class TestTTLCleanup:
    """Tests for TTL background cleanup."""
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_items(self, table_with_ttl, config):
        """Test cleaning up expired items."""
        service = table_with_ttl
        
        # Create an item with TTL in the past
        past_time = int((datetime.utcnow() - timedelta(hours=1)).timestamp())
        
        from dyscount_core.services.item_service import ItemService
        item_service = ItemService(config)
        
        put_request = PutItemRequest(
            TableName="TTLTestTable",
            Item={
                "pk": {"S": "test_item"},
                "data": {"S": "some data"},
                "exp": {"N": str(past_time)},
            },
        )
        
        await item_service.put_item(put_request)
        
        # Verify item exists
        get_request = GetItemRequest(
            TableName="TTLTestTable",
            Key={
                "pk": {"S": "test_item"},
            },
        )
        
        response = await item_service.get_item(get_request)
        assert response.item is not None
        
        # Run cleanup
        cleanup_task = TTLCleanupTask(
            config.storage.data_directory,
            namespace="default",
            check_interval=1,
            batch_size=100,
        )
        
        deleted_count = await cleanup_task.run_once()
        
        # Verify item was deleted
        response = await item_service.get_item(get_request)
        assert response.item is None  # Item should be deleted
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_cleanup_not_expired_items(self, table_with_ttl, config):
        """Test that non-expired items are not cleaned up."""
        service = table_with_ttl
        
        # Create an item with TTL in the future
        future_time = int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        
        from dyscount_core.services.item_service import ItemService
        item_service = ItemService(config)
        
        put_request = PutItemRequest(
            TableName="TTLTestTable",
            Item={
                "pk": {"S": "test_item"},
                "data": {"S": "some data"},
                "exp": {"N": str(future_time)},
            },
        )
        
        await item_service.put_item(put_request)
        
        # Run cleanup
        cleanup_task = TTLCleanupTask(
            config.storage.data_directory,
            namespace="default",
            check_interval=1,
            batch_size=100,
        )
        
        deleted_count = await cleanup_task.run_once()
        
        # Verify item still exists
        get_request = GetItemRequest(
            TableName="TTLTestTable",
            Key={
                "pk": {"S": "test_item"},
            },
        )
        
        response = await item_service.get_item(get_request)
        assert response.item is not None  # Item should NOT be deleted
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_cleanup_disabled_ttl(self, config):
        """Test that cleanup skips tables with disabled TTL."""
        service = TableService(config)
        
        # Create table without TTL
        from dyscount_core.models.operations import CreateTableRequest
        from dyscount_core.models.table import (
            KeySchemaElement,
            AttributeDefinition,
            KeyType,
            ScalarAttributeType,
        )
        
        create_request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="pk",
                    AttributeType=ScalarAttributeType.STRING,
                ),
            ],
        )
        
        await service.create_table(create_request)
        
        # Create item with past TTL (but TTL is disabled)
        past_time = int((datetime.utcnow() - timedelta(hours=1)).timestamp())
        
        from dyscount_core.services.item_service import ItemService
        item_service = ItemService(config)
        
        put_request = PutItemRequest(
            TableName="TestTable",
            Item={
                "pk": {"S": "test_item"},
                "data": {"S": "some data"},
                "exp": {"N": str(past_time)},
            },
        )
        
        await item_service.put_item(put_request)
        
        # Run cleanup
        cleanup_task = TTLCleanupTask(
            config.storage.data_directory,
            namespace="default",
            check_interval=1,
            batch_size=100,
        )
        
        deleted_count = await cleanup_task.run_once()
        
        # Verify item still exists (TTL is disabled)
        get_request = GetItemRequest(
            TableName="TestTable",
            Key={
                "pk": {"S": "test_item"},
            },
        )
        
        response = await item_service.get_item(get_request)
        assert response.item is not None  # Item should NOT be deleted
        
        await service.close()


class TestTTLCleanupTask:
    """Tests for TTLCleanupTask background task."""
    
    @pytest.mark.asyncio
    async def test_start_stop(self, config):
        """Test starting and stopping the cleanup task."""
        task = TTLCleanupTask(
            config.storage.data_directory,
            namespace="test",
            check_interval=1,
        )
        
        # Start task
        await task.start()
        assert task.running is True
        
        # Stop task
        await task.stop()
        assert task.running is False
    
    @pytest.mark.asyncio
    async def test_double_start(self, config):
        """Test starting task twice (should not create duplicate)."""
        task = TTLCleanupTask(
            config.storage.data_directory,
            namespace="test",
            check_interval=1,
        )
        
        await task.start()
        first_task = task._task
        
        # Try to start again
        await task.start()
        second_task = task._task
        
        # Should be the same task
        assert first_task is second_task
        
        await task.stop()
