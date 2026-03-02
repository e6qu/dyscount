"""Tests for DeleteItem operation."""

import pytest

from dyscount_core.config import Config, ServerSettings, StorageSettings, LoggingSettings
from dyscount_core.services.item_service import ItemService
from dyscount_core.services.table_service import TableService
from dyscount_core.models.operations import (
    CreateTableRequest,
    DeleteItemRequest,
    PutItemRequest,
    GetItemRequest,
)
from dyscount_core.models.table import (
    AttributeDefinition,
    KeySchemaElement,
    ScalarAttributeType,
    KeyType,
)
from dyscount_core.models.errors import ResourceNotFoundException, ValidationException


@pytest.fixture
def temp_data_dir():
    """Provide a temporary data directory."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def config(temp_data_dir):
    """Provide a test configuration."""
    return Config(
        server=ServerSettings(host="127.0.0.1", port=8000),
        storage=StorageSettings(data_directory=temp_data_dir),
        logging=LoggingSettings(level="INFO"),
    )


@pytest.fixture
async def test_table(config):
    """Create a test table and yield its name."""
    table_service = TableService(config)
    request = CreateTableRequest(
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
    await table_service.create_table(request)
    yield "TestTable"
    await table_service.close()


@pytest.fixture
async def test_table_composite(config):
    """Create a test table with composite key and yield its name."""
    table_service = TableService(config)
    request = CreateTableRequest(
        TableName="TestTableComposite",
        KeySchema=[
            KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            KeySchemaElement(AttributeName="sk", KeyType=KeyType.RANGE),
        ],
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
    )
    await table_service.create_table(request)
    yield "TestTableComposite"
    await table_service.close()


class TestDeleteItemValidation:
    """Tests for DeleteItem request validation."""

    @pytest.mark.asyncio
    async def test_delete_item_empty_table_name(self, config):
        """Test that empty table name raises ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            DeleteItemRequest(
                TableName="",
                Key={"pk": {"S": "test"}},
            )

        assert "String should have at least 1 character" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_item_invalid_table_name(self, config):
        """Test that invalid table name raises ValidationException."""
        service = ItemService(config)

        request = DeleteItemRequest(
            TableName="invalid@name",
            Key={"pk": {"S": "test"}},
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.delete_item(request)

        assert "can only contain alphanumeric characters" in str(exc_info.value)
        await service.close()

    @pytest.mark.asyncio
    async def test_delete_item_empty_key(self, config):
        """Test that empty key raises ValidationException."""
        service = ItemService(config)

        request = DeleteItemRequest(
            TableName="TestTable",
            Key={},
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.delete_item(request)

        assert "Key cannot be empty" in str(exc_info.value)
        await service.close()

    @pytest.mark.asyncio
    async def test_delete_item_invalid_key_format(self, config):
        """Test that invalid key format raises ValidationException."""
        service = ItemService(config)

        request = DeleteItemRequest(
            TableName="TestTable",
            Key={"pk": "not-an-attribute-value"},
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.delete_item(request)

        assert "must be an AttributeValue map" in str(exc_info.value)
        await service.close()


class TestDeleteItemNotFound:
    """Tests for DeleteItem when table or item doesn't exist."""

    @pytest.mark.asyncio
    async def test_delete_item_table_not_found(self, config):
        """Test that deleting from non-existent table raises ResourceNotFoundException."""
        service = ItemService(config)

        request = DeleteItemRequest(
            TableName="NonExistentTable",
            Key={"pk": {"S": "test"}},
        )

        with pytest.raises(ResourceNotFoundException) as exc_info:
            await service.delete_item(request)

        assert "Table not found" in str(exc_info.value)
        await service.close()

    @pytest.mark.asyncio
    async def test_delete_item_item_not_found(self, config, test_table):
        """Test that deleting non-existent item succeeds silently."""
        service = ItemService(config)

        request = DeleteItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "non-existent-key"}},
        )

        response = await service.delete_item(request)

        # Should succeed without error, but no attributes returned
        assert response.attributes is None
        assert response.consumed_capacity is not None
        assert response.consumed_capacity.table_name == test_table
        assert response.consumed_capacity.write_capacity_units == 1.0

        await service.close()


class TestDeleteItemSuccess:
    """Tests for successful DeleteItem operations."""

    @pytest.mark.asyncio
    async def test_delete_existing_item(self, config, test_table):
        """Test deleting an existing item."""
        service = ItemService(config)

        # First put an item
        await service.put_item(PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "delete-test"},
                "name": {"S": "Test Item"},
                "value": {"N": "42"},
            },
        ))

        # Verify item exists
        get_response = await service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "delete-test"}},
        ))
        assert get_response.item is not None

        # Delete the item
        request = DeleteItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "delete-test"}},
        )

        response = await service.delete_item(request)

        # Verify response
        assert response.attributes is None  # ReturnValues not set
        assert response.consumed_capacity is not None
        assert response.consumed_capacity.table_name == test_table
        assert response.consumed_capacity.write_capacity_units == 1.0

        # Verify item is deleted
        get_response2 = await service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "delete-test"}},
        ))
        assert get_response2.item is None

        await service.close()

    @pytest.mark.asyncio
    async def test_delete_item_return_values_none(self, config, test_table):
        """Test DeleteItem with ReturnValues=NONE (default)."""
        service = ItemService(config)

        # Put an item
        await service.put_item(PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "delete-none"},
                "name": {"S": "Test"},
            },
        ))

        # Delete with NONE
        request = DeleteItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "delete-none"}},
            ReturnValues="NONE",
        )

        response = await service.delete_item(request)

        assert response.attributes is None

        await service.close()

    @pytest.mark.asyncio
    async def test_delete_item_return_values_all_old(self, config, test_table):
        """Test DeleteItem with ReturnValues=ALL_OLD."""
        service = ItemService(config)

        # Put an item
        await service.put_item(PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "delete-old"},
                "name": {"S": "Old Name"},
                "count": {"N": "100"},
            },
        ))

        # Delete with ALL_OLD
        request = DeleteItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "delete-old"}},
            ReturnValues="ALL_OLD",
        )

        response = await service.delete_item(request)

        # Should return deleted attributes
        assert response.attributes is not None
        assert response.attributes["pk"] == {"S": "delete-old"}
        assert response.attributes["name"] == {"S": "Old Name"}
        assert response.attributes["count"] == {"N": "100"}

        await service.close()

    @pytest.mark.asyncio
    async def test_delete_item_return_values_all_old_nonexistent(self, config, test_table):
        """Test DeleteItem with ReturnValues=ALL_OLD for non-existent item."""
        service = ItemService(config)

        request = DeleteItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "never-existed"}},
            ReturnValues="ALL_OLD",
        )

        response = await service.delete_item(request)

        # No old attributes for non-existent item
        assert response.attributes is None

        await service.close()

    @pytest.mark.asyncio
    async def test_delete_item_composite_key(self, config, test_table_composite):
        """Test DeleteItem with composite key (partition + sort)."""
        service = ItemService(config)

        # Put an item with composite key
        await service.put_item(PutItemRequest(
            TableName=test_table_composite,
            Item={
                "pk": {"S": "partition-value"},
                "sk": {"S": "sort-value"},
                "data": {"S": "some data"},
            },
        ))

        # Delete the item
        request = DeleteItemRequest(
            TableName=test_table_composite,
            Key={
                "pk": {"S": "partition-value"},
                "sk": {"S": "sort-value"},
            },
        )

        response = await service.delete_item(request)

        assert response.consumed_capacity is not None

        # Verify item is deleted
        get_response = await service.get_item(GetItemRequest(
            TableName=test_table_composite,
            Key={
                "pk": {"S": "partition-value"},
                "sk": {"S": "sort-value"},
            },
        ))
        assert get_response.item is None

        await service.close()

    @pytest.mark.asyncio
    async def test_delete_item_missing_partition_key(self, config, test_table):
        """Test that DeleteItem without partition key raises ValidationException."""
        service = ItemService(config)

        request = DeleteItemRequest(
            TableName=test_table,
            Key={"name": {"S": "no pk"}},
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.delete_item(request)

        assert "Missing partition key attribute: pk" in str(exc_info.value)

        await service.close()


class TestDeleteItemResponseFormat:
    """Tests for DeleteItem response format."""

    @pytest.mark.asyncio
    async def test_delete_item_response_structure(self, config, test_table):
        """Test that DeleteItem response has correct structure."""
        service = ItemService(config)

        # Put then delete an item
        await service.put_item(PutItemRequest(
            TableName=test_table,
            Item={"pk": {"S": "response-test"}},
        ))

        request = DeleteItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "response-test"}},
        )

        response = await service.delete_item(request)

        # Check response structure
        assert hasattr(response, 'attributes')
        assert hasattr(response, 'consumed_capacity')

        # Check ConsumedCapacity structure
        cc = response.consumed_capacity
        assert cc.table_name == test_table
        assert cc.capacity_units is not None
        assert cc.write_capacity_units is not None

        await service.close()
