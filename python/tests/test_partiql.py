"""Tests for PartiQL operations (M2 Phase 4)."""

import pytest
import pytest_asyncio
import tempfile
import shutil

from dyscount_core.config import Config, StorageSettings, ServerSettings
from dyscount_core.services.table_service import TableService
from dyscount_core.services.item_service import ItemService
from dyscount_core.services.partiql_service import PartiQLService
from dyscount_core.models.operations import (
    CreateTableRequest,
    AttributeDefinition,
    KeySchemaElement,
    PutItemRequest,
    ExecuteStatementRequest,
    BatchExecuteStatementRequest,
    BatchStatementRequest,
)
from dyscount_core.models.errors import ResourceNotFoundException, ValidationException


@pytest_asyncio.fixture
async def config():
    """Create a temporary config for testing."""
    tmpdir = tempfile.mkdtemp()
    config = Config(
        server=ServerSettings(),
        storage=StorageSettings(data_directory=tmpdir),
    )
    yield config
    shutil.rmtree(tmpdir)


@pytest_asyncio.fixture
async def table_with_items(config):
    """Create a table with items for PartiQL testing."""
    service = TableService(config)
    
    # Create table
    create_request = CreateTableRequest(
        TableName="PartiQLTestTable",
        AttributeDefinitions=[
            AttributeDefinition(AttributeName="pk", AttributeType="S"),
        ],
        KeySchema=[
            KeySchemaElement(AttributeName="pk", KeyType="HASH"),
        ],
    )
    await service.create_table(create_request)
    
    # Add some items
    item_service = ItemService(config)
    items = [
        {"pk": {"S": "user1"}, "name": {"S": "Alice"}, "age": {"N": "30"}},
        {"pk": {"S": "user2"}, "name": {"S": "Bob"}, "age": {"N": "25"}},
        {"pk": {"S": "user3"}, "name": {"S": "Charlie"}, "age": {"N": "35"}},
    ]
    for item in items:
        put_request = PutItemRequest(
            TableName="PartiQLTestTable",
            Item=item,
        )
        await item_service.put_item(put_request)
    
    await item_service.close()
    
    yield service
    
    await service.close()


class TestExecuteStatementSelect:
    """Tests for ExecuteStatement SELECT operations."""
    
    @pytest.mark.asyncio
    async def test_select_star(self, table_with_items, config):
        """Test SELECT * FROM table."""
        service = PartiQLService(config)
        
        request = ExecuteStatementRequest(
            Statement="SELECT * FROM PartiQLTestTable",
        )
        
        response = await service.execute_statement(request)
        
        assert response.items is not None
        assert len(response.items) == 3
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_select_with_limit(self, table_with_items, config):
        """Test SELECT with LIMIT."""
        service = PartiQLService(config)
        
        request = ExecuteStatementRequest(
            Statement="SELECT * FROM PartiQLTestTable LIMIT 2",
        )
        
        response = await service.execute_statement(request)
        
        assert response.items is not None
        assert len(response.items) == 2
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_select_table_not_found(self, config):
        """Test SELECT from non-existent table."""
        service = PartiQLService(config)
        
        request = ExecuteStatementRequest(
            Statement="SELECT * FROM NonExistentTable",
        )
        
        with pytest.raises(ResourceNotFoundException) as exc_info:
            await service.execute_statement(request)
        
        assert "Table not found" in str(exc_info.value)
        await service.close()


class TestExecuteStatementInsert:
    """Tests for ExecuteStatement INSERT operations."""
    
    @pytest.mark.asyncio
    async def test_insert_value(self, table_with_items, config):
        """Test INSERT INTO table VALUE {...}."""
        service = PartiQLService(config)
        item_service = ItemService(config)
        
        request = ExecuteStatementRequest(
            Statement="INSERT INTO PartiQLTestTable VALUE {'pk': 'user4', 'name': 'David', 'age': 40}",
        )
        
        response = await service.execute_statement(request)
        
        # Verify item was inserted
        from dyscount_core.models.operations import GetItemRequest
        get_request = GetItemRequest(
            TableName="PartiQLTestTable",
            Key={"pk": {"S": "user4"}},
        )
        get_response = await item_service.get_item(get_request)
        assert get_response.item is not None
        assert get_response.item["name"]["S"] == "David"
        
        await item_service.close()
        await service.close()
    
    @pytest.mark.asyncio
    async def test_insert_columns_values(self, table_with_items, config):
        """Test INSERT INTO table (cols) VALUES (vals)."""
        service = PartiQLService(config)
        item_service = ItemService(config)
        
        request = ExecuteStatementRequest(
            Statement="INSERT INTO PartiQLTestTable (pk, name, age) VALUES ('user5', 'Eve', 28)",
        )
        
        response = await service.execute_statement(request)
        
        # Verify item was inserted
        from dyscount_core.models.operations import GetItemRequest
        get_request = GetItemRequest(
            TableName="PartiQLTestTable",
            Key={"pk": {"S": "user5"}},
        )
        get_response = await item_service.get_item(get_request)
        assert get_response.item is not None
        assert get_response.item["name"]["S"] == "Eve"
        
        await item_service.close()
        await service.close()


class TestExecuteStatementUpdate:
    """Tests for ExecuteStatement UPDATE operations."""
    
    @pytest.mark.asyncio
    async def test_update_set(self, table_with_items, config):
        """Test UPDATE table SET col = val WHERE key = val."""
        service = PartiQLService(config)
        item_service = ItemService(config)
        
        request = ExecuteStatementRequest(
            Statement="UPDATE PartiQLTestTable SET name = 'Alice Updated' WHERE pk = 'user1'",
        )
        
        response = await service.execute_statement(request)
        
        # Verify item was updated
        from dyscount_core.models.operations import GetItemRequest
        get_request = GetItemRequest(
            TableName="PartiQLTestTable",
            Key={"pk": {"S": "user1"}},
        )
        get_response = await item_service.get_item(get_request)
        assert get_response.item is not None
        assert get_response.item["name"]["S"] == "Alice Updated"
        
        await item_service.close()
        await service.close()
    
    @pytest.mark.asyncio
    async def test_update_without_where(self, table_with_items, config):
        """Test UPDATE without WHERE clause fails."""
        service = PartiQLService(config)
        
        request = ExecuteStatementRequest(
            Statement="UPDATE PartiQLTestTable SET name = 'All Updated'",
        )
        
        with pytest.raises(ValidationException) as exc_info:
            await service.execute_statement(request)
        
        assert "WHERE clause" in str(exc_info.value)
        await service.close()


class TestExecuteStatementDelete:
    """Tests for ExecuteStatement DELETE operations."""
    
    @pytest.mark.asyncio
    async def test_delete_where(self, table_with_items, config):
        """Test DELETE FROM table WHERE key = val."""
        service = PartiQLService(config)
        item_service = ItemService(config)
        
        request = ExecuteStatementRequest(
            Statement="DELETE FROM PartiQLTestTable WHERE pk = 'user2'",
        )
        
        response = await service.execute_statement(request)
        
        # Verify item was deleted
        from dyscount_core.models.operations import GetItemRequest
        get_request = GetItemRequest(
            TableName="PartiQLTestTable",
            Key={"pk": {"S": "user2"}},
        )
        get_response = await item_service.get_item(get_request)
        assert get_response.item is None
        
        await item_service.close()
        await service.close()
    
    @pytest.mark.asyncio
    async def test_delete_without_where(self, table_with_items, config):
        """Test DELETE without WHERE clause fails."""
        service = PartiQLService(config)
        
        request = ExecuteStatementRequest(
            Statement="DELETE FROM PartiQLTestTable",
        )
        
        with pytest.raises(ValidationException) as exc_info:
            await service.execute_statement(request)
        
        assert "WHERE clause" in str(exc_info.value)
        await service.close()


class TestBatchExecuteStatement:
    """Tests for BatchExecuteStatement operations."""
    
    @pytest.mark.asyncio
    async def test_batch_execute_multiple(self, table_with_items, config):
        """Test executing multiple statements in a batch."""
        service = PartiQLService(config)
        
        request = BatchExecuteStatementRequest(
            Statements=[
                BatchStatementRequest(
                    Statement="SELECT * FROM PartiQLTestTable WHERE pk = 'user1'",
                ),
                BatchStatementRequest(
                    Statement="SELECT * FROM PartiQLTestTable WHERE pk = 'user2'",
                ),
            ],
        )
        
        response = await service.batch_execute_statement(request)
        
        assert len(response.responses) == 2
        # First response should have user1 item
        assert response.responses[0].item is not None
        assert response.responses[0].item.get("pk", {}).get("S") == "user1"
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_batch_execute_with_error(self, table_with_items, config):
        """Test batch execution with one failing statement."""
        service = PartiQLService(config)
        
        request = BatchExecuteStatementRequest(
            Statements=[
                BatchStatementRequest(
                    Statement="SELECT * FROM PartiQLTestTable WHERE pk = 'user1'",
                ),
                BatchStatementRequest(
                    Statement="SELECT * FROM NonExistentTable WHERE pk = 'user1'",
                ),
            ],
        )
        
        response = await service.batch_execute_statement(request)
        
        assert len(response.responses) == 2
        # First should succeed
        assert response.responses[0].error is None
        # Second should have error
        assert response.responses[1].error is not None
        
        await service.close()


class TestPartiQLParser:
    """Tests for the PartiQL parser."""
    
    def test_parse_select_basic(self):
        """Test parsing basic SELECT."""
        from dyscount_core.partiql import parse_partiql, PartiQLOperation
        
        result = parse_partiql("SELECT * FROM MyTable")
        
        assert result.operation == PartiQLOperation.SELECT
        assert result.table_name == "MyTable"
        assert result.columns is None  # * means all columns
    
    def test_parse_select_with_limit(self):
        """Test parsing SELECT with LIMIT."""
        from dyscount_core.partiql import parse_partiql, PartiQLOperation
        
        result = parse_partiql("SELECT * FROM MyTable LIMIT 10")
        
        assert result.operation == PartiQLOperation.SELECT
        assert result.table_name == "MyTable"
        assert result.limit == 10
    
    def test_parse_insert_value(self):
        """Test parsing INSERT with VALUE."""
        from dyscount_core.partiql import parse_partiql, PartiQLOperation
        
        result = parse_partiql("INSERT INTO MyTable VALUE {'pk': '1', 'name': 'Test'}")
        
        assert result.operation == PartiQLOperation.INSERT
        assert result.table_name == "MyTable"
        assert result.values is not None
        assert result.values[0].get("pk") == "1"
        assert result.values[0].get("name") == "Test"
    
    def test_parse_update(self):
        """Test parsing UPDATE."""
        from dyscount_core.partiql import parse_partiql, PartiQLOperation
        
        result = parse_partiql("UPDATE MyTable SET name = 'NewName' WHERE pk = '1'")
        
        assert result.operation == PartiQLOperation.UPDATE
        assert result.table_name == "MyTable"
        assert result.set_clause is not None
        assert result.set_clause.get("name") == "NewName"
        assert result.where_conditions is not None
    
    def test_parse_delete(self):
        """Test parsing DELETE."""
        from dyscount_core.partiql import parse_partiql, PartiQLOperation
        
        result = parse_partiql("DELETE FROM MyTable WHERE pk = '1'")
        
        assert result.operation == PartiQLOperation.DELETE
        assert result.table_name == "MyTable"
        assert result.where_conditions is not None
