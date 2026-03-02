"""Tests for TransactWriteItems operation."""

import tempfile

import pytest
from dyscount_core.models.operations import (
    TransactWriteItemsRequest,
    TransactWriteItem,
    TransactPut,
    TransactDelete,
    TransactConditionCheck,
    TransactUpdate,
    CreateTableRequest,
)
from dyscount_core.models.table import (
    AttributeDefinition,
    KeySchemaElement,
    KeyType,
    ScalarAttributeType,
)
from dyscount_core.models.errors import (
    ValidationException,
    ResourceNotFoundException,
    ConditionalCheckFailedException,
)
from dyscount_core.config import Config, LoggingSettings, ServerSettings, StorageSettings
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


class TestTransactWriteItemsValidation:
    """Test TransactWriteItems validation rules."""
    
    @pytest.mark.asyncio
    async def test_transact_write_empty_items_list(self, config):
        """Should reject empty TransactItems list."""
        service = ItemService(config)
        request = TransactWriteItemsRequest(
            TransactItems=[],
        )
        
        with pytest.raises(ValidationException):
            await service.transact_write_items(request)
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_write_too_many_items(self, config):
        """Should reject more than 100 items."""
        service = ItemService(config)
        items = [
            TransactWriteItem(
                Put=TransactPut(
                    TableName="TestTable",
                    Item={"pk": {"S": f"pk{i}"}},
                )
            )
            for i in range(101)
        ]
        request = TransactWriteItemsRequest(TransactItems=items)
        
        with pytest.raises(ValidationException):
            await service.transact_write_items(request)
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_write_no_operation(self, config):
        """Should reject item with no operation."""
        service = ItemService(config)
        request = TransactWriteItemsRequest(
            TransactItems=[TransactWriteItem()],  # Empty item
        )
        
        with pytest.raises(ValidationException):
            await service.transact_write_items(request)
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_write_table_not_found(self, config):
        """Should reject if table does not exist."""
        service = ItemService(config)
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    Put=TransactPut(
                        TableName="NonExistentTable",
                        Item={"pk": {"S": "test"}},
                    )
                )
            ],
        )
        
        with pytest.raises(ResourceNotFoundException):
            await service.transact_write_items(request)
        
        await service.close()


class TestTransactWriteItemsPut:
    """Test Put operations in transactions."""
    
    @pytest.mark.asyncio
    async def test_transact_write_put_single_item(self, config, test_table):
        """Should put a single item atomically."""
        service = ItemService(config)
        
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    Put=TransactPut(
                        TableName=test_table,
                        Item={"pk": {"S": "user1"}, "name": {"S": "Alice"}},
                    )
                )
            ],
        )
        
        response = await service.transact_write_items(request)
        
        # Verify
        assert response.consumed_capacity is None
        
        # Verify item was written
        item = await service.table_manager.get_item(test_table, {"pk": {"S": "user1"}})
        assert item == {"pk": {"S": "user1"}, "name": {"S": "Alice"}}
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_write_put_multiple_items(self, config, test_table):
        """Should put multiple items atomically."""
        service = ItemService(config)
        
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    Put=TransactPut(
                        TableName=test_table,
                        Item={"pk": {"S": "user1"}, "name": {"S": "Alice"}},
                    )
                ),
                TransactWriteItem(
                    Put=TransactPut(
                        TableName=test_table,
                        Item={"pk": {"S": "user2"}, "name": {"S": "Bob"}},
                    )
                ),
                TransactWriteItem(
                    Put=TransactPut(
                        TableName=test_table,
                        Item={"pk": {"S": "user3"}, "name": {"S": "Charlie"}},
                    )
                ),
            ],
        )
        
        response = await service.transact_write_items(request)
        
        # Verify all items were written
        item1 = await service.table_manager.get_item(test_table, {"pk": {"S": "user1"}})
        item2 = await service.table_manager.get_item(test_table, {"pk": {"S": "user2"}})
        item3 = await service.table_manager.get_item(test_table, {"pk": {"S": "user3"}})
        
        assert item1 == {"pk": {"S": "user1"}, "name": {"S": "Alice"}}
        assert item2 == {"pk": {"S": "user2"}, "name": {"S": "Bob"}}
        assert item3 == {"pk": {"S": "user3"}, "name": {"S": "Charlie"}}
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_write_put_overwrite_existing(self, config, test_table):
        """Should overwrite existing items in transaction."""
        service = ItemService(config)
        
        # Setup: Put initial item
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "user1"}, "name": {"S": "OldName"}},
        )
        
        # Execute: Overwrite with transaction
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    Put=TransactPut(
                        TableName=test_table,
                        Item={"pk": {"S": "user1"}, "name": {"S": "NewName"}},
                    )
                )
            ],
        )
        
        await service.transact_write_items(request)
        
        # Verify
        item = await service.table_manager.get_item(test_table, {"pk": {"S": "user1"}})
        assert item == {"pk": {"S": "user1"}, "name": {"S": "NewName"}}
        
        await service.close()


class TestTransactWriteItemsDelete:
    """Test Delete operations in transactions."""
    
    @pytest.mark.asyncio
    async def test_transact_write_delete_single_item(self, config, test_table):
        """Should delete a single item atomically."""
        service = ItemService(config)
        
        # Setup: Put item
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "user1"}, "name": {"S": "Alice"}},
        )
        
        # Execute
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    Delete=TransactDelete(
                        TableName=test_table,
                        Key={"pk": {"S": "user1"}},
                    )
                )
            ],
        )
        
        response = await service.transact_write_items(request)
        
        # Verify item was deleted
        item = await service.table_manager.get_item(test_table, {"pk": {"S": "user1"}})
        assert item is None
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_write_delete_multiple_items(self, config, test_table):
        """Should delete multiple items atomically."""
        service = ItemService(config)
        
        # Setup: Put items
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "user1"}, "name": {"S": "Alice"}},
        )
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "user2"}, "name": {"S": "Bob"}},
        )
        
        # Execute
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    Delete=TransactDelete(
                        TableName=test_table,
                        Key={"pk": {"S": "user1"}},
                    )
                ),
                TransactWriteItem(
                    Delete=TransactDelete(
                        TableName=test_table,
                        Key={"pk": {"S": "user2"}},
                    )
                ),
            ],
        )
        
        await service.transact_write_items(request)
        
        # Verify all items deleted
        item1 = await service.table_manager.get_item(test_table, {"pk": {"S": "user1"}})
        item2 = await service.table_manager.get_item(test_table, {"pk": {"S": "user2"}})
        assert item1 is None
        assert item2 is None
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_write_delete_nonexistent(self, config, test_table):
        """Should succeed when deleting non-existent items."""
        service = ItemService(config)
        
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    Delete=TransactDelete(
                        TableName=test_table,
                        Key={"pk": {"S": "nonexistent"}},
                    )
                )
            ],
        )
        
        # Should not raise
        response = await service.transact_write_items(request)
        assert response.consumed_capacity is None
        
        await service.close()


class TestTransactWriteItemsConditionCheck:
    """Test ConditionCheck operations in transactions."""
    
    @pytest.mark.asyncio
    async def test_transact_write_condition_check_passes(self, config, test_table):
        """Should succeed when condition check passes."""
        service = ItemService(config)
        
        # Setup: Put item to check
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "user1"}, "status": {"S": "active"}},
        )
        
        # Execute: Condition check passes
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    ConditionCheck=TransactConditionCheck(
                        TableName=test_table,
                        Key={"pk": {"S": "user1"}},
                        ConditionExpression="attribute_exists(pk)",
                    )
                ),
                TransactWriteItem(
                    Put=TransactPut(
                        TableName=test_table,
                        Item={"pk": {"S": "user2"}, "name": {"S": "NewUser"}},
                    )
                ),
            ],
        )
        
        response = await service.transact_write_items(request)
        
        # Verify second item was written
        item = await service.table_manager.get_item(test_table, {"pk": {"S": "user2"}})
        assert item == {"pk": {"S": "user2"}, "name": {"S": "NewUser"}}
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_write_condition_check_fails(self, config, test_table):
        """Should fail entire transaction when condition check fails."""
        service = ItemService(config)
        
        # Setup: Put item
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "user1"}, "status": {"S": "active"}},
        )
        
        # Execute: Condition check fails
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    ConditionCheck=TransactConditionCheck(
                        TableName=test_table,
                        Key={"pk": {"S": "nonexistent"}},
                        ConditionExpression="attribute_exists(pk)",
                    )
                ),
                TransactWriteItem(
                    Put=TransactPut(
                        TableName=test_table,
                        Item={"pk": {"S": "user2"}, "name": {"S": "NewUser"}},
                    )
                ),
            ],
        )
        
        with pytest.raises(ConditionalCheckFailedException):
            await service.transact_write_items(request)
        
        # Verify second item was NOT written (transaction aborted)
        item = await service.table_manager.get_item(test_table, {"pk": {"S": "user2"}})
        assert item is None
        
        await service.close()


class TestTransactWriteItemsMixed:
    """Test mixed operations in transactions."""
    
    @pytest.mark.asyncio
    async def test_transact_write_put_and_delete(self, config, test_table):
        """Should handle Put and Delete in same transaction."""
        service = ItemService(config)
        
        # Setup: Put item to delete
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "old_user"}, "name": {"S": "OldUser"}},
        )
        
        # Execute: Delete old and add new
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    Delete=TransactDelete(
                        TableName=test_table,
                        Key={"pk": {"S": "old_user"}},
                    )
                ),
                TransactWriteItem(
                    Put=TransactPut(
                        TableName=test_table,
                        Item={"pk": {"S": "new_user"}, "name": {"S": "NewUser"}},
                    )
                ),
            ],
        )
        
        await service.transact_write_items(request)
        
        # Verify
        old_item = await service.table_manager.get_item(test_table, {"pk": {"S": "old_user"}})
        new_item = await service.table_manager.get_item(test_table, {"pk": {"S": "new_user"}})
        assert old_item is None
        assert new_item == {"pk": {"S": "new_user"}, "name": {"S": "NewUser"}}
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_write_all_operation_types(self, config, test_table):
        """Should handle all operation types in one transaction."""
        service = ItemService(config)
        
        # Setup: Put items for condition check and delete
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "check_user"}, "status": {"S": "active"}},
        )
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "delete_user"}, "name": {"S": "ToDelete"}},
        )
        
        # Execute: All operations
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    ConditionCheck=TransactConditionCheck(
                        TableName=test_table,
                        Key={"pk": {"S": "check_user"}},
                        ConditionExpression="#s = :s",
                        ExpressionAttributeNames={"#s": "status"},
                        ExpressionAttributeValues={":s": {"S": "active"}},
                    )
                ),
                TransactWriteItem(
                    Delete=TransactDelete(
                        TableName=test_table,
                        Key={"pk": {"S": "delete_user"}},
                    )
                ),
                TransactWriteItem(
                    Put=TransactPut(
                        TableName=test_table,
                        Item={"pk": {"S": "new_user"}, "name": {"S": "NewUser"}},
                    )
                ),
            ],
        )
        
        await service.transact_write_items(request)
        
        # Verify
        check_user = await service.table_manager.get_item(test_table, {"pk": {"S": "check_user"}})
        delete_user = await service.table_manager.get_item(test_table, {"pk": {"S": "delete_user"}})
        new_user = await service.table_manager.get_item(test_table, {"pk": {"S": "new_user"}})
        
        assert check_user == {"pk": {"S": "check_user"}, "status": {"S": "active"}}
        assert delete_user is None
        assert new_user == {"pk": {"S": "new_user"}, "name": {"S": "NewUser"}}
        
        await service.close()


class TestTransactWriteItemsCapacity:
    """Test consumed capacity tracking."""
    
    @pytest.mark.asyncio
    async def test_transact_write_returns_consumed_capacity(self, config, test_table):
        """Should return consumed capacity when requested."""
        service = ItemService(config)
        
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    Put=TransactPut(
                        TableName=test_table,
                        Item={"pk": {"S": "user1"}, "name": {"S": "Alice"}},
                    )
                )
            ],
            ReturnConsumedCapacity="TOTAL",
        )
        
        response = await service.transact_write_items(request)
        
        # Verify
        assert response.consumed_capacity is not None
        assert len(response.consumed_capacity) == 1
        assert response.consumed_capacity[0].table_name == test_table
        assert response.consumed_capacity[0].write_capacity_units is not None
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_write_no_capacity_when_not_requested(self, config, test_table):
        """Should not return consumed capacity when not requested."""
        service = ItemService(config)
        
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    Put=TransactPut(
                        TableName=test_table,
                        Item={"pk": {"S": "user1"}, "name": {"S": "Alice"}},
                    )
                )
            ],
        )
        
        response = await service.transact_write_items(request)
        
        # Verify - no capacity info when not requested
        assert response.consumed_capacity is None
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_write_capacity_multiple_tables(self, config, test_table):
        """Should return capacity for each table."""
        service = ItemService(config)
        
        # Create second table (test_table is already created by fixture)
        table_svc = TableService(config)
        await table_svc.create_table(
            CreateTableRequest(
                TableName="SecondTable",
                KeySchema=[KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH)],
                AttributeDefinitions=[AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING)],
            )
        )
        await table_svc.close()
        
        # Execute: Write to both tables
        request = TransactWriteItemsRequest(
            TransactItems=[
                TransactWriteItem(
                    Put=TransactPut(
                        TableName="TestTable",
                        Item={"pk": {"S": "user1"}},
                    )
                ),
                TransactWriteItem(
                    Put=TransactPut(
                        TableName="SecondTable",
                        Item={"pk": {"S": "user2"}},
                    )
                ),
            ],
            ReturnConsumedCapacity="TOTAL",
        )
        
        response = await service.transact_write_items(request)
        
        # Verify - capacity for both tables
        assert response.consumed_capacity is not None
        table_names = [c.table_name for c in response.consumed_capacity]
        assert "TestTable" in table_names
        assert "SecondTable" in table_names
        
        await service.close()
