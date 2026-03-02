"""Tests for PutItem operation."""

import pytest

from dyscount_core.config import Config, ServerSettings, StorageSettings, LoggingSettings
from dyscount_core.services.item_service import ItemService
from dyscount_core.services.table_service import TableService
from dyscount_core.models.operations import (
    CreateTableRequest,
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


class TestPutItemValidation:
    """Tests for PutItem request validation."""

    @pytest.mark.asyncio
    async def test_put_item_empty_table_name(self, config):
        """Test that empty table name raises ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            PutItemRequest(
                TableName="",
                Item={"pk": {"S": "test"}},
            )

        assert "String should have at least 1 character" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_put_item_invalid_table_name(self, config):
        """Test that invalid table name raises ValidationException."""
        service = ItemService(config)

        request = PutItemRequest(
            TableName="invalid@name",
            Item={"pk": {"S": "test"}},
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.put_item(request)

        assert "can only contain alphanumeric characters" in str(exc_info.value)
        await service.close()

    @pytest.mark.asyncio
    async def test_put_item_empty_item(self, config):
        """Test that empty item raises ValidationException."""
        service = ItemService(config)

        request = PutItemRequest(
            TableName="TestTable",
            Item={},
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.put_item(request)

        assert "Item cannot be empty" in str(exc_info.value)
        await service.close()

    @pytest.mark.asyncio
    async def test_put_item_invalid_item_format(self, config):
        """Test that invalid item format raises ValidationException."""
        service = ItemService(config)

        request = PutItemRequest(
            TableName="TestTable",
            Item={"pk": "not-an-attribute-value"},
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.put_item(request)

        assert "must be an AttributeValue map" in str(exc_info.value)
        await service.close()


class TestPutItemNotFound:
    """Tests for PutItem when table doesn't exist."""

    @pytest.mark.asyncio
    async def test_put_item_table_not_found(self, config):
        """Test that putting item to non-existent table raises ResourceNotFoundException."""
        service = ItemService(config)

        request = PutItemRequest(
            TableName="NonExistentTable",
            Item={"pk": {"S": "test"}},
        )

        with pytest.raises(ResourceNotFoundException) as exc_info:
            await service.put_item(request)

        assert "Table not found" in str(exc_info.value)
        await service.close()


class TestPutItemSuccess:
    """Tests for successful PutItem operations."""

    @pytest.mark.asyncio
    async def test_put_new_item(self, config, test_table):
        """Test putting a new item."""
        service = ItemService(config)

        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "user#123"},
                "name": {"S": "John Doe"},
                "age": {"N": "30"},
            },
        )

        response = await service.put_item(request)

        # Verify response structure
        assert response.attributes is None  # No old item (ReturnValues not set)
        assert response.consumed_capacity is not None
        assert response.consumed_capacity.table_name == test_table
        assert response.consumed_capacity.capacity_units == 1.0
        assert response.consumed_capacity.write_capacity_units == 1.0

        await service.close()

    @pytest.mark.asyncio
    async def test_put_item_return_values_none(self, config, test_table):
        """Test PutItem with ReturnValues=NONE (default)."""
        service = ItemService(config)

        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "user#123"},
                "name": {"S": "John"},
            },
            ReturnValues="NONE",
        )

        response = await service.put_item(request)

        assert response.attributes is None

        await service.close()

    @pytest.mark.asyncio
    async def test_put_item_return_values_all_old_new_item(self, config, test_table):
        """Test PutItem with ReturnValues=ALL_OLD for new item (no old data)."""
        service = ItemService(config)

        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "new-user"},
                "name": {"S": "New User"},
            },
            ReturnValues="ALL_OLD",
        )

        response = await service.put_item(request)

        # New item, so no old attributes
        assert response.attributes is None

        await service.close()

    @pytest.mark.asyncio
    async def test_put_item_return_values_all_old_existing_item(self, config, test_table):
        """Test PutItem with ReturnValues=ALL_OLD for existing item."""
        service = ItemService(config)

        # First put the item
        await service.put_item(PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "existing-user"},
                "name": {"S": "Old Name"},
                "age": {"N": "25"},
            },
        ))

        # Now put with ALL_OLD
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "existing-user"},
                "name": {"S": "New Name"},
                "email": {"S": "test@example.com"},
            },
            ReturnValues="ALL_OLD",
        )

        response = await service.put_item(request)

        # Should return old attributes
        assert response.attributes is not None
        assert response.attributes["pk"] == {"S": "existing-user"}
        assert response.attributes["name"] == {"S": "Old Name"}
        assert response.attributes["age"] == {"N": "25"}

        await service.close()

    @pytest.mark.asyncio
    async def test_put_item_composite_key(self, config, test_table_composite):
        """Test PutItem with composite key (partition + sort)."""
        service = ItemService(config)

        request = PutItemRequest(
            TableName=test_table_composite,
            Item={
                "pk": {"S": "partition-value"},
                "sk": {"S": "sort-value"},
                "data": {"S": "some data"},
            },
        )

        response = await service.put_item(request)

        assert response.consumed_capacity is not None
        assert response.attributes is None

        await service.close()

    @pytest.mark.asyncio
    async def test_put_item_all_attribute_types(self, config, test_table):
        """Test PutItem with all DynamoDB attribute types."""
        service = ItemService(config)

        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "test"},
                "string_attr": {"S": "hello"},
                "number_attr": {"N": "42"},
                "binary_attr": {"B": b"binary data"},
                "bool_attr": {"BOOL": True},
                "null_attr": {"NULL": True},
                "list_attr": {"L": [{"S": "item1"}, {"N": "2"}]},
                "map_attr": {"M": {"key": {"S": "value"}}},
                "string_set_attr": {"SS": ["a", "b", "c"]},
                "number_set_attr": {"NS": ["1", "2", "3"]},
                "binary_set_attr": {"BS": [b"bin1", b"bin2"]},
            },
        )

        response = await service.put_item(request)

        assert response.consumed_capacity is not None

        await service.close()

    @pytest.mark.asyncio
    async def test_put_item_replace_existing(self, config, test_table):
        """Test that PutItem replaces an existing item."""
        service = ItemService(config)

        # Put first item
        await service.put_item(PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "replace-test"},
                "field1": {"S": "original"},
                "field2": {"N": "100"},
            },
        ))

        # Put replacement item
        await service.put_item(PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "replace-test"},
                "field1": {"S": "replaced"},
                "field3": {"S": "new field"},
            },
        ))

        # Verify replacement via GetItem
        get_response = await service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "replace-test"}},
        ))

        assert get_response.item is not None
        assert get_response.item["field1"] == {"S": "replaced"}
        assert get_response.item["field3"] == {"S": "new field"}
        # field2 should not exist anymore
        assert "field2" not in get_response.item

        await service.close()

    @pytest.mark.asyncio
    async def test_put_item_missing_partition_key(self, config, test_table):
        """Test that PutItem without partition key raises ValidationException."""
        service = ItemService(config)

        request = PutItemRequest(
            TableName=test_table,
            Item={
                "name": {"S": "no pk"},
            },
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.put_item(request)

        assert "Missing partition key attribute: pk" in str(exc_info.value)

        await service.close()


class TestPutItemResponseFormat:
    """Tests for PutItem response format."""

    @pytest.mark.asyncio
    async def test_put_item_response_structure(self, config, test_table):
        """Test that PutItem response has correct structure."""
        service = ItemService(config)

        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "test"},
                "name": {"S": "Test"},
            },
        )

        response = await service.put_item(request)

        # Check response structure
        assert hasattr(response, 'attributes')
        assert hasattr(response, 'consumed_capacity')

        # Check ConsumedCapacity structure
        cc = response.consumed_capacity
        assert cc.table_name == test_table
        assert cc.capacity_units is not None
        assert cc.write_capacity_units is not None

        await service.close()
