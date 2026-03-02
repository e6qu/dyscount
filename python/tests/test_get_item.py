"""Tests for GetItem operation."""

import tempfile

import pytest
from dyscount_core.config import Config, LoggingSettings, ServerSettings, StorageSettings
from dyscount_core.models.errors import ResourceNotFoundException, ValidationException
from dyscount_core.models.operations import (
    CreateTableRequest,
    GetItemRequest,
)
from dyscount_core.models.table import (
    AttributeDefinition,
    KeySchemaElement,
    KeyType,
    ScalarAttributeType,
)
from dyscount_core.services.item_service import ItemService
from dyscount_core.services.table_service import TableService


@pytest.fixture
def temp_data_dir():
    """Provide a temporary data directory."""
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
async def test_table_composite_key(config):
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


class TestGetItemValidation:
    """Tests for GetItem request validation."""

    @pytest.mark.asyncio
    async def test_get_item_empty_table_name(self, config):
        """Test that empty table name raises ValidationException."""
        # Pydantic validates this before service layer, so we expect ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            GetItemRequest(
                TableName="",
                Key={"pk": {"S": "test"}},
            )

        assert "String should have at least 1 character" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_item_invalid_table_name(self, config):
        """Test that invalid table name raises ValidationException."""
        service = ItemService(config)

        request = GetItemRequest(
            TableName="invalid@name",
            Key={"pk": {"S": "test"}},
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.get_item(request)

        assert "can only contain alphanumeric characters" in str(exc_info.value)
        await service.close()

    @pytest.mark.asyncio
    async def test_get_item_empty_key(self, config):
        """Test that empty key raises ValidationException."""
        service = ItemService(config)

        request = GetItemRequest(
            TableName="TestTable",
            Key={},
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.get_item(request)

        assert "Key cannot be empty" in str(exc_info.value)
        await service.close()

    @pytest.mark.asyncio
    async def test_get_item_invalid_key_format(self, config):
        """Test that invalid key format raises ValidationException."""
        service = ItemService(config)

        request = GetItemRequest(
            TableName="TestTable",
            Key={"pk": "not-an-attribute-value"},  # Should be {"S": "value"}
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.get_item(request)

        assert "must be an AttributeValue map" in str(exc_info.value)
        await service.close()


class TestGetItemNotFound:
    """Tests for GetItem when table or item doesn't exist."""

    @pytest.mark.asyncio
    async def test_get_item_table_not_found(self, config):
        """Test that getting item from non-existent table raises ResourceNotFoundException."""
        service = ItemService(config)

        request = GetItemRequest(
            TableName="NonExistentTable",
            Key={"pk": {"S": "test"}},
        )

        with pytest.raises(ResourceNotFoundException) as exc_info:
            await service.get_item(request)

        assert "Table not found" in str(exc_info.value)
        await service.close()

    @pytest.mark.asyncio
    async def test_get_item_item_not_found(self, config, test_table):
        """Test that getting non-existent item returns empty response."""
        service = ItemService(config)

        request = GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "non-existent-key"}},
        )

        response = await service.get_item(request)

        assert response.item is None
        assert response.consumed_capacity is not None
        assert response.consumed_capacity.table_name == test_table
        assert response.consumed_capacity.read_capacity_units == 0.5  # Eventually consistent

        await service.close()


class TestGetItemSuccess:
    """Tests for successful GetItem operations."""

    @pytest.mark.asyncio
    async def test_get_item_strongly_consistent(self, config, test_table):
        """Test GetItem with strongly consistent read."""
        service = ItemService(config)

        request = GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "test-key"}},
            ConsistentRead=True,
        )

        response = await service.get_item(request)

        # Item doesn't exist yet, but we can check the consumed capacity
        assert response.consumed_capacity.read_capacity_units == 1.0  # Strongly consistent

        await service.close()

    @pytest.mark.asyncio
    async def test_get_item_with_number_key(self, config):
        """Test GetItem with numeric partition key."""
        # Create table with numeric key
        table_service = TableService(config)

        await table_service.create_table(
            CreateTableRequest(
                TableName="NumberKeyTable",
                KeySchema=[
                    KeySchemaElement(AttributeName="id", KeyType=KeyType.HASH),
                ],
                AttributeDefinitions=[
                    AttributeDefinition(
                        AttributeName="id",
                        AttributeType=ScalarAttributeType.NUMBER,
                    ),
                ],
            )
        )

        service = ItemService(config)

        request = GetItemRequest(
            TableName="NumberKeyTable",
            Key={"id": {"N": "123"}},
        )

        response = await service.get_item(request)

        assert response.item is None  # Item doesn't exist

        await service.close()
        await table_service.close()

    @pytest.mark.asyncio
    async def test_get_item_composite_key(self, config, test_table_composite_key):
        """Test GetItem with composite key (partition + sort)."""
        service = ItemService(config)

        request = GetItemRequest(
            TableName=test_table_composite_key,
            Key={
                "pk": {"S": "partition-value"},
                "sk": {"S": "sort-value"},
            },
        )

        response = await service.get_item(request)

        assert response.item is None  # Item doesn't exist
        assert response.consumed_capacity is not None

        await service.close()


class TestGetItemResponseFormat:
    """Tests for GetItem response format."""

    @pytest.mark.asyncio
    async def test_get_item_response_structure(self, config, test_table):
        """Test that GetItem response has correct structure."""
        service = ItemService(config)

        request = GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "test"}},
        )

        response = await service.get_item(request)

        # Check response structure
        assert hasattr(response, 'item')
        assert hasattr(response, 'consumed_capacity')

        # Check ConsumedCapacity structure
        cc = response.consumed_capacity
        assert cc.table_name == test_table
        assert cc.capacity_units is not None
        assert cc.read_capacity_units is not None

        await service.close()
