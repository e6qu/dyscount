"""Tests for Query operation."""

import pytest
import pytest_asyncio
from dyscount_core.config import Config
from dyscount_core.services.item_service import ItemService
from dyscount_core.services.table_service import TableService
from dyscount_core.models.errors import ResourceNotFoundException, ValidationException


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
async def test_table_with_sort_key(table_service):
    """Create a test table with composite key."""
    from dyscount_core.models.table import (
        KeySchemaElement,
        AttributeDefinition,
        KeyType,
        ScalarAttributeType,
    )
    
    import uuid
    table_name = f"test_query_table_{uuid.uuid4().hex[:8]}"
    
    # Delete if exists
    try:
        await table_service.table_manager.delete_table(table_name)
    except Exception:
        pass
    
    key_schema = [
        KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
        KeySchemaElement(AttributeName="sk", KeyType=KeyType.RANGE),
    ]
    attribute_definitions = [
        AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
        AttributeDefinition(AttributeName="sk", AttributeType=ScalarAttributeType.STRING),
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


@pytest_asyncio.fixture
async def sample_items(item_service, test_table_with_sort_key):
    """Create sample items for testing."""
    from dyscount_core.models.operations import PutItemRequest
    
    items = [
        {"pk": {"S": "user#123"}, "sk": {"S": "profile"}, "name": {"S": "John"}},
        {"pk": {"S": "user#123"}, "sk": {"S": "settings"}, "theme": {"S": "dark"}},
        {"pk": {"S": "user#123"}, "sk": {"S": "orders"}, "count": {"N": "5"}},
        {"pk": {"S": "user#456"}, "sk": {"S": "profile"}, "name": {"S": "Jane"}},
    ]
    
    for item in items:
        request = PutItemRequest(
            TableName=test_table_with_sort_key,
            Item=item,
        )
        await item_service.put_item(request)
    
    return items


class TestQueryValidation:
    """Test Query request validation."""
    
    @pytest.mark.asyncio
    async def test_query_empty_table_name(self, item_service):
        """Test Query with empty table name."""
        from dyscount_core.models.operations import QueryRequest
        from pydantic import ValidationError
        
        # Empty table name is caught by Pydantic validation
        with pytest.raises(ValidationError):
            QueryRequest(
                TableName="",
                KeyConditionExpression="#pk = :pk",
            )
    
    @pytest.mark.asyncio
    async def test_query_invalid_table_name(self, item_service):
        """Test Query with invalid table name."""
        from dyscount_core.models.operations import QueryRequest
        
        request = QueryRequest(
            TableName="ab",  # Too short
            KeyConditionExpression="#pk = :pk",
        )
        
        with pytest.raises(ValidationException):
            await item_service.query(request)
    
    @pytest.mark.asyncio
    async def test_query_table_not_found(self, item_service):
        """Test Query on non-existent table."""
        from dyscount_core.models.operations import QueryRequest
        
        request = QueryRequest(
            TableName="this_table_does_not_exist",
            KeyConditionExpression="#pk = :pk",
            ExpressionAttributeNames={"#pk": "pk"},
            ExpressionAttributeValues={":pk": {"S": "test"}},
        )
        
        with pytest.raises(ResourceNotFoundException):
            await item_service.query(request)


class TestQueryPartitionKey:
    """Test Query by partition key only."""
    
    @pytest.mark.asyncio
    async def test_query_partition_key_only(self, item_service, test_table_with_sort_key, sample_items):
        """Test Query with partition key only."""
        from dyscount_core.models.operations import QueryRequest
        
        request = QueryRequest(
            TableName=test_table_with_sort_key,
            KeyConditionExpression="#pk = :pk",
            ExpressionAttributeNames={"#pk": "pk"},
            ExpressionAttributeValues={":pk": {"S": "user#123"}},
        )
        
        response = await item_service.query(request)
        
        assert response.count == 3
        assert len(response.items) == 3
        
        # Verify all items have the correct partition key
        for item in response.items:
            assert item["pk"] == {"S": "user#123"}
    
    @pytest.mark.asyncio
    async def test_query_no_matching_items(self, item_service, test_table_with_sort_key, sample_items):
        """Test Query with partition key that has no items."""
        from dyscount_core.models.operations import QueryRequest
        
        request = QueryRequest(
            TableName=test_table_with_sort_key,
            KeyConditionExpression="#pk = :pk",
            ExpressionAttributeNames={"#pk": "pk"},
            ExpressionAttributeValues={":pk": {"S": "user#999"}},
        )
        
        response = await item_service.query(request)
        
        assert response.count == 0
        assert len(response.items) == 0


class TestQuerySortKeyConditions:
    """Test Query with sort key conditions."""
    
    @pytest.mark.asyncio
    async def test_query_sort_key_eq(self, item_service, test_table_with_sort_key, sample_items):
        """Test Query with sort key equality."""
        from dyscount_core.models.operations import QueryRequest
        
        request = QueryRequest(
            TableName=test_table_with_sort_key,
            KeyConditionExpression="#pk = :pk AND #sk = :sk",
            ExpressionAttributeNames={"#pk": "pk", "#sk": "sk"},
            ExpressionAttributeValues={
                ":pk": {"S": "user#123"},
                ":sk": {"S": "profile"},
            },
        )
        
        response = await item_service.query(request)
        
        assert response.count == 1
        assert response.items[0]["pk"] == {"S": "user#123"}
        assert response.items[0]["sk"] == {"S": "profile"}
    
    @pytest.mark.asyncio
    async def test_query_sort_key_begins_with(self, item_service, test_table_with_sort_key, sample_items):
        """Test Query with sort key begins_with."""
        from dyscount_core.models.operations import QueryRequest
        
        # First add items with sortable keys
        from dyscount_core.models.operations import PutItemRequest
        await item_service.put_item(PutItemRequest(
            TableName=test_table_with_sort_key,
            Item={"pk": {"S": "user#789"}, "sk": {"S": "order#001"}, "total": {"N": "100"}},
        ))
        await item_service.put_item(PutItemRequest(
            TableName=test_table_with_sort_key,
            Item={"pk": {"S": "user#789"}, "sk": {"S": "order#002"}, "total": {"N": "200"}},
        ))
        
        request = QueryRequest(
            TableName=test_table_with_sort_key,
            KeyConditionExpression="#pk = :pk AND begins_with(#sk, :prefix)",
            ExpressionAttributeNames={"#pk": "pk", "#sk": "sk"},
            ExpressionAttributeValues={
                ":pk": {"S": "user#789"},
                ":prefix": {"S": "order"},
            },
        )
        
        response = await item_service.query(request)
        
        assert response.count == 2
        for item in response.items:
            assert item["sk"]["S"].startswith("order")
    
    @pytest.mark.asyncio
    async def test_query_sort_key_between(self, item_service, test_table_with_sort_key):
        """Test Query with sort key BETWEEN."""
        from dyscount_core.models.operations import QueryRequest, PutItemRequest
        
        # Add items with sortable keys
        for i in range(1, 6):
            await item_service.put_item(PutItemRequest(
                TableName=test_table_with_sort_key,
                Item={"pk": {"S": "user#000"}, "sk": {"S": f"item{i:03d}"}, "idx": {"N": str(i)}},
            ))
        
        request = QueryRequest(
            TableName=test_table_with_sort_key,
            KeyConditionExpression="#pk = :pk AND #sk BETWEEN :low AND :high",
            ExpressionAttributeNames={"#pk": "pk", "#sk": "sk"},
            ExpressionAttributeValues={
                ":pk": {"S": "user#000"},
                ":low": {"S": "item002"},
                ":high": {"S": "item004"},
            },
        )
        
        response = await item_service.query(request)
        
        assert response.count == 3
        sk_values = [item["sk"]["S"] for item in response.items]
        assert "item002" in sk_values
        assert "item003" in sk_values
        assert "item004" in sk_values


class TestQueryPagination:
    """Test Query pagination."""
    
    @pytest.mark.asyncio
    async def test_query_with_limit(self, item_service, test_table_with_sort_key):
        """Test Query with Limit."""
        from dyscount_core.models.operations import QueryRequest, PutItemRequest
        
        # Add 5 items
        for i in range(5):
            await item_service.put_item(PutItemRequest(
                TableName=test_table_with_sort_key,
                Item={"pk": {"S": "limit_test"}, "sk": {"S": f"item{i}"}, "num": {"N": str(i)}},
            ))
        
        request = QueryRequest(
            TableName=test_table_with_sort_key,
            KeyConditionExpression="#pk = :pk",
            ExpressionAttributeNames={"#pk": "pk"},
            ExpressionAttributeValues={":pk": {"S": "limit_test"}},
            Limit=3,
        )
        
        response = await item_service.query(request)
        
        assert response.count == 3
        assert response.last_evaluated_key is not None


class TestQueryFilterExpression:
    """Test Query with FilterExpression."""
    
    @pytest.mark.asyncio
    async def test_query_with_filter(self, item_service, test_table_with_sort_key):
        """Test Query with FilterExpression."""
        from dyscount_core.models.operations import QueryRequest, PutItemRequest
        
        # Add items with status
        await item_service.put_item(PutItemRequest(
            TableName=test_table_with_sort_key,
            Item={"pk": {"S": "filter_test"}, "sk": {"S": "item1"}, "status": {"S": "active"}},
        ))
        await item_service.put_item(PutItemRequest(
            TableName=test_table_with_sort_key,
            Item={"pk": {"S": "filter_test"}, "sk": {"S": "item2"}, "status": {"S": "inactive"}},
        ))
        await item_service.put_item(PutItemRequest(
            TableName=test_table_with_sort_key,
            Item={"pk": {"S": "filter_test"}, "sk": {"S": "item3"}, "status": {"S": "active"}},
        ))
        
        request = QueryRequest(
            TableName=test_table_with_sort_key,
            KeyConditionExpression="#pk = :pk",
            FilterExpression="#s = :status",
            ExpressionAttributeNames={"#pk": "pk", "#s": "status"},
            ExpressionAttributeValues={
                ":pk": {"S": "filter_test"},
                ":status": {"S": "active"},
            },
        )
        
        response = await item_service.query(request)
        
        assert response.count == 2
        for item in response.items:
            assert item["status"] == {"S": "active"}


class TestQueryConsumedCapacity:
    """Test Query ConsumedCapacity."""
    
    @pytest.mark.asyncio
    async def test_query_returns_consumed_capacity(self, item_service, test_table_with_sort_key, sample_items):
        """Test Query returns ConsumedCapacity."""
        from dyscount_core.models.operations import QueryRequest
        
        request = QueryRequest(
            TableName=test_table_with_sort_key,
            KeyConditionExpression="#pk = :pk",
            ExpressionAttributeNames={"#pk": "pk"},
            ExpressionAttributeValues={":pk": {"S": "user#123"}},
            ReturnConsumedCapacity="TOTAL",
        )
        
        response = await item_service.query(request)
        
        assert response.consumed_capacity is not None
        assert response.consumed_capacity.table_name == test_table_with_sort_key
        assert response.consumed_capacity.capacity_units > 0
