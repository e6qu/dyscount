"""Tests for UpdateItem operation."""

import pytest

from dyscount_core.config import Config, ServerSettings, StorageSettings, LoggingSettings
from dyscount_core.services.item_service import ItemService
from dyscount_core.services.table_service import TableService
from dyscount_core.models.operations import (
    CreateTableRequest,
    UpdateItemRequest,
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
async def item_service(config, test_table):
    """Provide an ItemService with test table set up."""
    service = ItemService(config)
    yield service
    await service.close()


class TestUpdateItemValidation:
    """Tests for UpdateItem request validation."""

    @pytest.mark.asyncio
    async def test_update_item_empty_table_name(self, config):
        """Test that empty table name raises ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            UpdateItemRequest(
                TableName="",
                Key={"pk": {"S": "test"}},
                UpdateExpression="SET #n = :val",
            )

        assert "String should have at least 1 character" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_item_invalid_table_name(self, item_service, test_table):
        """Test that invalid table name raises ValidationException."""
        request = UpdateItemRequest(
            TableName="invalid@name",
            Key={"pk": {"S": "test"}},
            UpdateExpression="SET #n = :val",
        )

        with pytest.raises(ValidationException) as exc_info:
            await item_service.update_item(request)

        assert "can only contain alphanumeric characters" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_item_empty_key(self, item_service, test_table):
        """Test that empty key raises ValidationException."""
        request = UpdateItemRequest(
            TableName=test_table,
            Key={},
            UpdateExpression="SET #n = :val",
        )

        with pytest.raises(ValidationException) as exc_info:
            await item_service.update_item(request)

        assert "Key cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_item_invalid_key_format(self, item_service, test_table):
        """Test that invalid key format raises ValidationException."""
        request = UpdateItemRequest(
            TableName=test_table,
            Key={"pk": "not-an-attribute-value"},
            UpdateExpression="SET #n = :val",
        )

        with pytest.raises(ValidationException) as exc_info:
            await item_service.update_item(request)

        assert "must be an AttributeValue map" in str(exc_info.value)


class TestUpdateItemNotFound:
    """Tests for UpdateItem when table doesn't exist."""

    @pytest.mark.asyncio
    async def test_update_item_table_not_found(self, config):
        """Test that updating in non-existent table raises ResourceNotFoundException."""
        service = ItemService(config)

        request = UpdateItemRequest(
            TableName="NonExistentTable",
            Key={"pk": {"S": "test"}},
            UpdateExpression="SET #n = :val",
        )

        with pytest.raises(ResourceNotFoundException) as exc_info:
            await service.update_item(request)

        assert "Table not found" in str(exc_info.value)
        await service.close()


class TestUpdateItemSet:
    """Tests for SET actions."""

    @pytest.mark.asyncio
    async def test_set_scalar_attribute(self, item_service, test_table):
        """Test SET with a scalar attribute value."""
        # First put an item
        await item_service.put_item(PutItemRequest(
            TableName=test_table,
            Item={"pk": {"S": "set-test"}, "name": {"S": "Original"}},
        ))

        # Update with SET
        request = UpdateItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "set-test"}},
            UpdateExpression="SET #n = :val",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":val": {"S": "Updated"}},
        )

        response = await item_service.update_item(request)

        # Verify the update
        get_response = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "set-test"}},
        ))
        assert get_response.item["name"] == {"S": "Updated"}

    @pytest.mark.asyncio
    async def test_set_new_attribute(self, item_service, test_table):
        """Test SET to add a new attribute."""
        # First put an item
        await item_service.put_item(PutItemRequest(
            TableName=test_table,
            Item={"pk": {"S": "new-attr-test"}},
        ))

        # Update with SET to add new attribute
        request = UpdateItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "new-attr-test"}},
            UpdateExpression="SET #n = :val",
            ExpressionAttributeNames={"#n": "newField"},
            ExpressionAttributeValues={":val": {"N": "42"}},
        )

        await item_service.update_item(request)

        # Verify the update
        get_response = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "new-attr-test"}},
        ))
        assert get_response.item["newField"] == {"N": "42"}

    @pytest.mark.asyncio
    async def test_set_multiple_attributes(self, item_service, test_table):
        """Test SET with multiple attributes."""
        # First put an item
        await item_service.put_item(PutItemRequest(
            TableName=test_table,
            Item={"pk": {"S": "multi-set-test"}},
        ))

        # Update with multiple SETs
        request = UpdateItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "multi-set-test"}},
            UpdateExpression="SET #a = :val1, #b = :val2",
            ExpressionAttributeNames={"#a": "field1", "#b": "field2"},
            ExpressionAttributeValues={
                ":val1": {"S": "Value1"},
                ":val2": {"N": "100"},
            },
        )

        await item_service.update_item(request)

        # Verify the update
        get_response = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "multi-set-test"}},
        ))
        assert get_response.item["field1"] == {"S": "Value1"}
        assert get_response.item["field2"] == {"N": "100"}

    @pytest.mark.asyncio
    async def test_set_arithmetic_add(self, item_service, test_table):
        """Test SET with arithmetic addition."""
        # First put an item with a counter
        await item_service.put_item(PutItemRequest(
            TableName=test_table,
            Item={"pk": {"S": "counter-test"}, "counter": {"N": "10"}},
        ))

        # Increment counter
        request = UpdateItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "counter-test"}},
            UpdateExpression="SET #c = #c + :inc",
            ExpressionAttributeNames={"#c": "counter"},
            ExpressionAttributeValues={":inc": {"N": "5"}},
        )

        await item_service.update_item(request)

        # Verify the update
        get_response = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "counter-test"}},
        ))
        assert get_response.item["counter"] == {"N": "15"}

    @pytest.mark.asyncio
    async def test_set_arithmetic_subtract(self, item_service, test_table):
        """Test SET with arithmetic subtraction."""
        # First put an item with a counter
        await item_service.put_item(PutItemRequest(
            TableName=test_table,
            Item={"pk": {"S": "dec-test"}, "balance": {"N": "100"}},
        ))

        # Decrement
        request = UpdateItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "dec-test"}},
            UpdateExpression="SET #b = #b - :dec",
            ExpressionAttributeNames={"#b": "balance"},
            ExpressionAttributeValues={":dec": {"N": "25"}},
        )

        await item_service.update_item(request)

        # Verify
        get_response = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "dec-test"}},
        ))
        assert get_response.item["balance"] == {"N": "75"}


class TestUpdateItemRemove:
    """Tests for REMOVE actions."""

    @pytest.mark.asyncio
    async def test_remove_attribute(self, item_service, test_table):
        """Test REMOVE to delete an attribute."""
        # First put an item
        await item_service.put_item(PutItemRequest(
            TableName=test_table,
            Item={"pk": {"S": "remove-test"}, "temp": {"S": "value"}},
        ))

        # Remove the attribute
        request = UpdateItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "remove-test"}},
            UpdateExpression="REMOVE #t",
            ExpressionAttributeNames={"#t": "temp"},
        )

        await item_service.update_item(request)

        # Verify the attribute is removed
        get_response = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "remove-test"}},
        ))
        assert "temp" not in get_response.item


class TestUpdateItemReturnValues:
    """Tests for ReturnValues options."""

    @pytest.mark.asyncio
    async def test_return_values_all_old(self, item_service, test_table):
        """Test ReturnValues=ALL_OLD."""
        # First put an item
        await item_service.put_item(PutItemRequest(
            TableName=test_table,
            Item={"pk": {"S": "rv-old-test"}, "name": {"S": "OldName"}},
        ))

        # Update with ALL_OLD
        request = UpdateItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "rv-old-test"}},
            UpdateExpression="SET #n = :val",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":val": {"S": "NewName"}},
            ReturnValues="ALL_OLD",
        )

        response = await item_service.update_item(request)

        # Should return old attributes
        assert response.attributes is not None
        assert response.attributes["name"] == {"S": "OldName"}

    @pytest.mark.asyncio
    async def test_return_values_all_new(self, item_service, test_table):
        """Test ReturnValues=ALL_NEW."""
        # First put an item
        await item_service.put_item(PutItemRequest(
            TableName=test_table,
            Item={"pk": {"S": "rv-new-test"}, "name": {"S": "OldName"}},
        ))

        # Update with ALL_NEW
        request = UpdateItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "rv-new-test"}},
            UpdateExpression="SET #n = :val",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":val": {"S": "NewName"}},
            ReturnValues="ALL_NEW",
        )

        response = await item_service.update_item(request)

        # Should return new attributes
        assert response.attributes is not None
        assert response.attributes["name"] == {"S": "NewName"}

    @pytest.mark.asyncio
    async def test_return_values_updated_new(self, item_service, test_table):
        """Test ReturnValues=UPDATED_NEW."""
        # First put an item
        await item_service.put_item(PutItemRequest(
            TableName=test_table,
            Item={"pk": {"S": "rv-upd-test"}, "name": {"S": "OldName"}, "keep": {"S": "KeepValue"}},
        ))

        # Update with UPDATED_NEW
        request = UpdateItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "rv-upd-test"}},
            UpdateExpression="SET #n = :val",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":val": {"S": "NewName"}},
            ReturnValues="UPDATED_NEW",
        )

        response = await item_service.update_item(request)

        # Should return only updated attributes
        assert response.attributes is not None
        assert response.attributes["name"] == {"S": "NewName"}
        assert "keep" not in response.attributes  # Not updated


class TestUpdateItemFunctions:
    """Tests for UpdateExpression functions."""

    @pytest.mark.asyncio
    async def test_list_append_existing(self, item_service, test_table):
        """Test list_append function with existing list."""
        # First put an item with a list
        await item_service.put_item(PutItemRequest(
            TableName=test_table,
            Item={"pk": {"S": "list-test"}, "items": {"L": [{"S": "item1"}]}},
        ))

        # Append to the list
        request = UpdateItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "list-test"}},
            UpdateExpression="SET #i = list_append(#i, :new_items)",
            ExpressionAttributeNames={"#i": "items"},
            ExpressionAttributeValues={":new_items": {"L": [{"S": "item2"}]}},
        )

        await item_service.update_item(request)

        # Verify
        get_response = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "list-test"}},
        ))
        assert len(get_response.item["items"]["L"]) == 2
        assert get_response.item["items"]["L"][0] == {"S": "item1"}
        assert get_response.item["items"]["L"][1] == {"S": "item2"}

    @pytest.mark.asyncio
    async def test_if_not_exists_new(self, item_service, test_table):
        """Test if_not_exists function when attribute doesn't exist."""
        # First put an item without the attribute
        await item_service.put_item(PutItemRequest(
            TableName=test_table,
            Item={"pk": {"S": "ifne-test"}},
        ))

        # Use if_not_exists
        request = UpdateItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "ifne-test"}},
            UpdateExpression="SET #c = if_not_exists(#c, :default)",
            ExpressionAttributeNames={"#c": "counter"},
            ExpressionAttributeValues={":default": {"N": "0"}},
        )

        await item_service.update_item(request)

        # Verify counter was set to default
        get_response = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "ifne-test"}},
        ))
        assert get_response.item["counter"] == {"N": "0"}

    @pytest.mark.asyncio
    async def test_if_not_exists_existing(self, item_service, test_table):
        """Test if_not_exists function when attribute exists."""
        # First put an item with the attribute
        await item_service.put_item(PutItemRequest(
            TableName=test_table,
            Item={"pk": {"S": "ifne-exist-test"}, "counter": {"N": "42"}},
        ))

        # Use if_not_exists - should keep existing value
        request = UpdateItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "ifne-exist-test"}},
            UpdateExpression="SET #c = if_not_exists(#c, :default)",
            ExpressionAttributeNames={"#c": "counter"},
            ExpressionAttributeValues={":default": {"N": "0"}},
        )

        await item_service.update_item(request)

        # Verify counter kept original value
        get_response = await item_service.get_item(GetItemRequest(
            TableName=test_table,
            Key={"pk": {"S": "ifne-exist-test"}},
        ))
        assert get_response.item["counter"] == {"N": "42"}
