"""Tests for TransactGetItems operation."""

import tempfile

import pytest
from dyscount_core.models.operations import (
    TransactGetItemsRequest,
    TransactGetItem,
    TransactGet,
    CreateTableRequest,
    PutItemRequest,
)
from dyscount_core.models.table import (
    AttributeDefinition,
    KeySchemaElement,
    KeyType,
    ScalarAttributeType,
)
from dyscount_core.models.errors import ValidationException, ResourceNotFoundException
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


class TestTransactGetItemsValidation:
    """Test TransactGetItems validation rules."""
    
    @pytest.mark.asyncio
    async def test_transact_get_empty_items_list(self, config):
        """Should reject empty TransactItems list."""
        service = ItemService(config)
        request = TransactGetItemsRequest(
            TransactItems=[],
        )
        
        with pytest.raises(ValidationException):
            await service.transact_get_items(request)
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_get_too_many_items(self, config):
        """Should reject more than 100 items."""
        service = ItemService(config)
        items = [
            TransactGetItem(
                Get=TransactGet(
                    TableName="TestTable",
                    Key={"pk": {"S": f"pk{i}"}},
                )
            )
            for i in range(101)
        ]
        request = TransactGetItemsRequest(TransactItems=items)
        
        with pytest.raises(ValidationException):
            await service.transact_get_items(request)
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_get_table_not_found(self, config):
        """Should reject if table does not exist."""
        service = ItemService(config)
        request = TransactGetItemsRequest(
            TransactItems=[
                TransactGetItem(
                    Get=TransactGet(
                        TableName="NonExistentTable",
                        Key={"pk": {"S": "test"}},
                    )
                )
            ],
        )
        
        with pytest.raises(ResourceNotFoundException):
            await service.transact_get_items(request)
        
        await service.close()


class TestTransactGetItemsSuccess:
    """Test successful TransactGetItems operations."""
    
    @pytest.mark.asyncio
    async def test_transact_get_single_item(self, config, test_table):
        """Should get a single item atomically."""
        service = ItemService(config)
        
        # Setup: Put an item using table_manager directly
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "user1"}, "name": {"S": "Alice"}},
        )
        
        # Execute
        request = TransactGetItemsRequest(
            TransactItems=[
                TransactGetItem(
                    Get=TransactGet(
                        TableName=test_table,
                        Key={"pk": {"S": "user1"}},
                    )
                )
            ],
        )
        
        response = await service.transact_get_items(request)
        
        # Verify
        assert len(response.responses) == 1
        assert response.responses[0] == {"pk": {"S": "user1"}, "name": {"S": "Alice"}}
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_get_multiple_items(self, config, test_table):
        """Should get multiple items atomically."""
        service = ItemService(config)
        
        # Setup: Put multiple items
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "user1"}, "name": {"S": "Alice"}},
        )
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "user2"}, "name": {"S": "Bob"}},
        )
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "user3"}, "name": {"S": "Charlie"}},
        )
        
        # Execute
        request = TransactGetItemsRequest(
            TransactItems=[
                TransactGetItem(
                    Get=TransactGet(
                        TableName=test_table,
                        Key={"pk": {"S": "user1"}},
                    )
                ),
                TransactGetItem(
                    Get=TransactGet(
                        TableName=test_table,
                        Key={"pk": {"S": "user2"}},
                    )
                ),
                TransactGetItem(
                    Get=TransactGet(
                        TableName=test_table,
                        Key={"pk": {"S": "user3"}},
                    )
                ),
            ],
        )
        
        response = await service.transact_get_items(request)
        
        # Verify
        assert len(response.responses) == 3
        assert response.responses[0] == {"pk": {"S": "user1"}, "name": {"S": "Alice"}}
        assert response.responses[1] == {"pk": {"S": "user2"}, "name": {"S": "Bob"}}
        assert response.responses[2] == {"pk": {"S": "user3"}, "name": {"S": "Charlie"}}
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_get_nonexistent_item(self, config, test_table):
        """Should return empty dict for non-existent items."""
        service = ItemService(config)
        
        request = TransactGetItemsRequest(
            TransactItems=[
                TransactGetItem(
                    Get=TransactGet(
                        TableName=test_table,
                        Key={"pk": {"S": "nonexistent"}},
                    )
                )
            ],
        )
        
        response = await service.transact_get_items(request)
        
        # Verify - non-existent items return empty dict
        assert len(response.responses) == 1
        assert response.responses[0] == {}
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_get_mixed_existence(self, config, test_table):
        """Should handle mix of existing and non-existing items."""
        service = ItemService(config)
        
        # Setup: Put only some items
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "user1"}, "name": {"S": "Alice"}},
        )
        
        request = TransactGetItemsRequest(
            TransactItems=[
                TransactGetItem(
                    Get=TransactGet(
                        TableName=test_table,
                        Key={"pk": {"S": "user1"}},
                    )
                ),
                TransactGetItem(
                    Get=TransactGet(
                        TableName=test_table,
                        Key={"pk": {"S": "nonexistent"}},
                    )
                ),
            ],
        )
        
        response = await service.transact_get_items(request)
        
        # Verify
        assert len(response.responses) == 2
        assert response.responses[0] == {"pk": {"S": "user1"}, "name": {"S": "Alice"}}
        assert response.responses[1] == {}
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_get_with_projection(self, config, test_table):
        """Should support ProjectionExpression."""
        service = ItemService(config)
        
        # Setup: Put item with multiple attributes
        await service.table_manager.put_item(
            test_table,
            {
                "pk": {"S": "user1"},
                "name": {"S": "Alice"},
                "email": {"S": "alice@example.com"},
                "age": {"N": "30"},
            },
        )
        
        # Execute
        request = TransactGetItemsRequest(
            TransactItems=[
                TransactGetItem(
                    Get=TransactGet(
                        TableName=test_table,
                        Key={"pk": {"S": "user1"}},
                        ProjectionExpression="pk, #n",
                        ExpressionAttributeNames={"#n": "name"},
                    )
                )
            ],
        )
        
        response = await service.transact_get_items(request)
        
        # Verify - only projected fields returned
        assert len(response.responses) == 1
        assert response.responses[0] == {"pk": {"S": "user1"}, "name": {"S": "Alice"}}
        
        await service.close()


class TestTransactGetItemsCapacity:
    """Test consumed capacity tracking."""
    
    @pytest.mark.asyncio
    async def test_transact_get_returns_consumed_capacity(self, config, test_table):
        """Should return consumed capacity when requested."""
        service = ItemService(config)
        
        # Setup
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "user1"}, "name": {"S": "Alice"}},
        )
        
        # Execute
        request = TransactGetItemsRequest(
            TransactItems=[
                TransactGetItem(
                    Get=TransactGet(
                        TableName=test_table,
                        Key={"pk": {"S": "user1"}},
                    )
                )
            ],
            ReturnConsumedCapacity="TOTAL",
        )
        
        response = await service.transact_get_items(request)
        
        # Verify
        assert response.consumed_capacity is not None
        assert len(response.consumed_capacity) == 1
        assert response.consumed_capacity[0].table_name == test_table
        assert response.consumed_capacity[0].read_capacity_units is not None
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_transact_get_no_capacity_when_not_requested(self, config, test_table):
        """Should not return consumed capacity when not requested."""
        service = ItemService(config)
        
        # Setup
        await service.table_manager.put_item(
            test_table,
            {"pk": {"S": "user1"}, "name": {"S": "Alice"}},
        )
        
        # Execute
        request = TransactGetItemsRequest(
            TransactItems=[
                TransactGetItem(
                    Get=TransactGet(
                        TableName=test_table,
                        Key={"pk": {"S": "user1"}},
                    )
                )
            ],
        )
        
        response = await service.transact_get_items(request)
        
        # Verify - no capacity info when not requested
        assert response.consumed_capacity is None
        
        await service.close()
