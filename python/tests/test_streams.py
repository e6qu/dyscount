"""Tests for DynamoDB Streams functionality."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from dyscount_core.config import Config, StorageSettings
from dyscount_core.models.operations import (
    CreateTableRequest,
    PutItemRequest,
    DeleteItemRequest,
    UpdateItemRequest,
    UpdateTableRequest,
)
from dyscount_core.models.table import (
    AttributeDefinition,
    KeySchemaElement,
    StreamSpecification,
)
from dyscount_core.services.table_service import TableService
from dyscount_core.services.item_service import ItemService
from dyscount_core.storage.stream_manager import StreamManager, StreamViewType, EventName


@pytest.fixture
async def temp_config():
    """Create a temporary configuration for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config(
            storage=StorageSettings(
                data_directory=Path(tmpdir),
                namespace="test",
            )
        )
        yield config


@pytest.mark.asyncio
async def test_create_table_with_stream(temp_config):
    """Test creating a table with streams enabled."""
    service = TableService(temp_config)
    try:
        request = CreateTableRequest(
            TableName="test-table",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType="HASH"),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType="S"),
            ],
            StreamSpecification=StreamSpecification(
                StreamEnabled=True,
                StreamViewType="NEW_AND_OLD_IMAGES",
            ),
        )
        
        response = await service.create_table(request)
        
        assert response.TableDescription is not None
        assert response.TableDescription.TableName == "test-table"
        
        # Verify stream was created
        stream_manager = StreamManager(temp_config.storage.data_directory)
        try:
            stream_meta = await stream_manager.describe_stream("test-table")
            assert stream_meta is not None
            assert stream_meta.stream_status.value == "ENABLED"
            assert stream_meta.stream_view_type == StreamViewType.NEW_AND_OLD_IMAGES
        finally:
            await stream_manager.close()
            
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_enable_stream_via_update_table(temp_config):
    """Test enabling streams via UpdateTable."""
    # First create a table without streams
    table_service = TableService(temp_config)
    try:
        create_request = CreateTableRequest(
            TableName="test-table",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType="HASH"),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType="S"),
            ],
        )
        await table_service.create_table(create_request)
        
        # Enable streams via UpdateTable
        update_request = UpdateTableRequest(
            TableName="test-table",
            StreamSpecification=StreamSpecification(
                StreamEnabled=True,
                StreamViewType="NEW_IMAGE",
            ),
        )
        
        response = await table_service.update_table(update_request)
        
        # Verify stream was enabled
        stream_manager = StreamManager(temp_config.storage.data_directory)
        try:
            stream_meta = await stream_manager.describe_stream("test-table")
            assert stream_meta is not None
            assert stream_meta.stream_status.value == "ENABLED"
            assert stream_meta.stream_view_type == StreamViewType.NEW_IMAGE
        finally:
            await stream_manager.close()
            
    finally:
        await table_service.close()


@pytest.mark.asyncio
async def test_put_item_creates_stream_record(temp_config):
    """Test that put_item creates a stream record."""
    # Create table with streams
    table_service = TableService(temp_config)
    item_service = ItemService(temp_config)
    
    try:
        create_request = CreateTableRequest(
            TableName="test-table",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType="HASH"),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType="S"),
            ],
            StreamSpecification=StreamSpecification(
                StreamEnabled=True,
                StreamViewType="NEW_AND_OLD_IMAGES",
            ),
        )
        await table_service.create_table(create_request)
        
        # Put an item
        put_request = PutItemRequest(
            TableName="test-table",
            Item={
                "pk": {"S": "test-key"},
                "data": {"S": "test-value"},
            },
        )
        await item_service.put_item(put_request)
        
        # Verify stream record was created
        stream_manager = StreamManager(temp_config.storage.data_directory)
        try:
            records, _ = await stream_manager.get_records(
                table_name="test-table",
                shard_iterator="0",
                limit=10,
            )
            
            assert len(records) == 1
            assert records[0].event_name == EventName.INSERT
            assert records[0].keys == {"pk": {"S": "test-key"}}
            assert records[0].new_image is not None
        finally:
            await stream_manager.close()
            
    finally:
        await item_service.close()
        await table_service.close()


@pytest.mark.asyncio
async def test_delete_item_creates_stream_record(temp_config):
    """Test that delete_item creates a stream record."""
    # Create table with streams
    table_service = TableService(temp_config)
    item_service = ItemService(temp_config)
    
    try:
        create_request = CreateTableRequest(
            TableName="test-table",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType="HASH"),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType="S"),
            ],
            StreamSpecification=StreamSpecification(
                StreamEnabled=True,
                StreamViewType="NEW_AND_OLD_IMAGES",
            ),
        )
        await table_service.create_table(create_request)
        
        # First put an item
        put_request = PutItemRequest(
            TableName="test-table",
            Item={
                "pk": {"S": "test-key"},
                "data": {"S": "test-value"},
            },
        )
        await item_service.put_item(put_request)
        
        # Delete the item
        delete_request = DeleteItemRequest(
            TableName="test-table",
            Key={
                "pk": {"S": "test-key"},
            },
        )
        await item_service.delete_item(delete_request)
        
        # Verify stream records
        stream_manager = StreamManager(temp_config.storage.data_directory)
        try:
            records, _ = await stream_manager.get_records(
                table_name="test-table",
                shard_iterator="0",
                limit=10,
            )
            
            assert len(records) == 2
            assert records[0].event_name == EventName.INSERT
            assert records[1].event_name == EventName.REMOVE
            assert records[1].old_image is not None
        finally:
            await stream_manager.close()
            
    finally:
        await item_service.close()
        await table_service.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
