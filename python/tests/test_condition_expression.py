"""Tests for ConditionExpression functionality."""

import pytest
import pytest_asyncio
from dyscount_core.config import Config
from dyscount_core.services.item_service import ItemService
from dyscount_core.models.errors import ConditionalCheckFailedException


@pytest_asyncio.fixture
async def item_service():
    """Create an item service for testing."""
    config = Config()
    service = ItemService(config)
    yield service
    await service.close()


@pytest_asyncio.fixture
async def test_table(item_service):
    """Create a test table."""
    from dyscount_core.models.table import (
        KeySchemaElement,
        AttributeDefinition,
        KeyType,
        ScalarAttributeType,
    )
    
    # Delete table if it exists
    try:
        await item_service.table_manager.delete_table("test_condition_table")
    except Exception:
        pass
    
    # Create table
    key_schema = [
        KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
        KeySchemaElement(AttributeName="sk", KeyType=KeyType.RANGE),
    ]
    attribute_definitions = [
        AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
        AttributeDefinition(AttributeName="sk", AttributeType=ScalarAttributeType.STRING),
    ]
    
    await item_service.table_manager.create_table(
        "test_condition_table",
        key_schema=key_schema,
        attribute_definitions=attribute_definitions,
    )
    
    yield "test_condition_table"
    
    # Cleanup
    try:
        await item_service.table_manager.delete_table("test_condition_table")
    except Exception:
        pass


@pytest_asyncio.fixture
async def sample_item(item_service, test_table):
    """Create a sample item for testing - resets on each test."""
    from dyscount_core.models.operations import PutItemRequest
    import uuid
    
    # Use unique IDs to ensure test isolation
    test_id = str(uuid.uuid4())[:8]
    item = {
        "pk": {"S": f"user#{test_id}"},
        "sk": {"S": "profile"},
        "name": {"S": "John Doe"},
        "age": {"N": "30"},
        "active": {"BOOL": True},
        "tags": {"L": [{"S": "tag1"}, {"S": "tag2"}]},
        "metadata": {"M": {"key1": {"S": "value1"}}},
    }
    
    request = PutItemRequest(
        TableName=test_table,
        Item=item,
    )
    await item_service.put_item(request)
    
    return item


class TestComparisonOperators:
    """Test comparison operators in ConditionExpression."""
    
    @pytest.mark.asyncio
    async def test_eq_operator_true(self, item_service, test_table, sample_item):
        """Test equality operator when condition is true."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="#n = :val",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":val": {"S": "John Doe"}},
        )
        
        response = await item_service.put_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_eq_operator_false(self, item_service, test_table, sample_item):
        """Test equality operator when condition is false."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="#n = :val",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":val": {"S": "Wrong Name"}},
        )
        
        with pytest.raises(ConditionalCheckFailedException):
            await item_service.put_item(request)
    
    @pytest.mark.asyncio
    async def test_ne_operator_true(self, item_service, test_table, sample_item):
        """Test not-equal operator when condition is true."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="#n <> :val",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":val": {"S": "Wrong Name"}},
        )
        
        response = await item_service.put_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_lt_operator(self, item_service, test_table, sample_item):
        """Test less-than operator."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "age": {"N": "35"},
            },
            ConditionExpression="#a < :val",
            ExpressionAttributeNames={"#a": "age"},
            ExpressionAttributeValues={":val": {"N": "40"}},
        )
        
        response = await item_service.put_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_le_operator(self, item_service, test_table, sample_item):
        """Test less-than-or-equal operator."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "age": {"N": "35"},
            },
            ConditionExpression="#a <= :val",
            ExpressionAttributeNames={"#a": "age"},
            ExpressionAttributeValues={":val": {"N": "35"}},
        )
        
        response = await item_service.put_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_gt_operator(self, item_service, test_table, sample_item):
        """Test greater-than operator."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "age": {"N": "35"},
            },
            ConditionExpression="#a > :val",
            ExpressionAttributeNames={"#a": "age"},
            ExpressionAttributeValues={":val": {"N": "20"}},
        )
        
        response = await item_service.put_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_ge_operator(self, item_service, test_table, sample_item):
        """Test greater-than-or-equal operator."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "age": {"N": "35"},
            },
            ConditionExpression="#a >= :val",
            ExpressionAttributeNames={"#a": "age"},
            ExpressionAttributeValues={":val": {"N": "30"}},
        )
        
        response = await item_service.put_item(request)
        assert response is not None


class TestLogicalOperators:
    """Test logical operators in ConditionExpression."""
    
    @pytest.mark.asyncio
    async def test_and_operator_true(self, item_service, test_table, sample_item):
        """Test AND operator when both conditions are true."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="#n = :name AND #a = :age",
            ExpressionAttributeNames={"#n": "name", "#a": "age"},
            ExpressionAttributeValues={
                ":name": {"S": "John Doe"},
                ":age": {"N": "30"},
            },
        )
        
        response = await item_service.put_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_and_operator_false(self, item_service, test_table, sample_item):
        """Test AND operator when one condition is false."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="#n = :name AND #a = :age",
            ExpressionAttributeNames={"#n": "name", "#a": "age"},
            ExpressionAttributeValues={
                ":name": {"S": "John Doe"},
                ":age": {"N": "999"},
            },
        )
        
        with pytest.raises(ConditionalCheckFailedException):
            await item_service.put_item(request)
    
    @pytest.mark.asyncio
    async def test_or_operator_true(self, item_service, test_table, sample_item):
        """Test OR operator when one condition is true."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="#n = :name OR #a = :wrong_age",
            ExpressionAttributeNames={"#n": "name", "#a": "age"},
            ExpressionAttributeValues={
                ":name": {"S": "John Doe"},
                ":wrong_age": {"N": "999"},
            },
        )
        
        response = await item_service.put_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_or_operator_false(self, item_service, test_table, sample_item):
        """Test OR operator when both conditions are false."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="#n = :wrong_name OR #a = :wrong_age",
            ExpressionAttributeNames={"#n": "name", "#a": "age"},
            ExpressionAttributeValues={
                ":wrong_name": {"S": "Wrong Name"},
                ":wrong_age": {"N": "999"},
            },
        )
        
        with pytest.raises(ConditionalCheckFailedException):
            await item_service.put_item(request)
    
    @pytest.mark.asyncio
    async def test_not_operator(self, item_service, test_table, sample_item):
        """Test NOT operator."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="NOT #n = :wrong_name",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":wrong_name": {"S": "Wrong Name"}},
        )
        
        response = await item_service.put_item(request)
        assert response is not None


class TestFunctionConditions:
    """Test function conditions in ConditionExpression."""
    
    @pytest.mark.asyncio
    async def test_attribute_exists_true(self, item_service, test_table, sample_item):
        """Test attribute_exists when attribute exists."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="attribute_exists(#n)",
            ExpressionAttributeNames={"#n": "name"},
        )
        
        response = await item_service.put_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_attribute_exists_false(self, item_service, test_table, sample_item):
        """Test attribute_exists when attribute doesn't exist."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="attribute_exists(#n)",
            ExpressionAttributeNames={"#n": "nonexistent"},
        )
        
        with pytest.raises(ConditionalCheckFailedException):
            await item_service.put_item(request)
    
    @pytest.mark.asyncio
    async def test_attribute_not_exists_true(self, item_service, test_table, sample_item):
        """Test attribute_not_exists when attribute doesn't exist."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="attribute_not_exists(#n)",
            ExpressionAttributeNames={"#n": "nonexistent"},
        )
        
        response = await item_service.put_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_attribute_not_exists_false(self, item_service, test_table, sample_item):
        """Test attribute_not_exists when attribute exists."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="attribute_not_exists(#n)",
            ExpressionAttributeNames={"#n": "name"},
        )
        
        with pytest.raises(ConditionalCheckFailedException):
            await item_service.put_item(request)
    
    @pytest.mark.asyncio
    async def test_begins_with_true(self, item_service, test_table, sample_item):
        """Test begins_with when string begins with prefix."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="begins_with(#n, :prefix)",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":prefix": {"S": "John"}},
        )
        
        response = await item_service.put_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_begins_with_false(self, item_service, test_table, sample_item):
        """Test begins_with when string doesn't begin with prefix."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="begins_with(#n, :prefix)",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":prefix": {"S": "Jane"}},
        )
        
        with pytest.raises(ConditionalCheckFailedException):
            await item_service.put_item(request)
    
    @pytest.mark.asyncio
    async def test_contains_string_true(self, item_service, test_table, sample_item):
        """Test contains when string contains substring."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="contains(#n, :substring)",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":substring": {"S": "Doe"}},
        )
        
        response = await item_service.put_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_contains_list_true(self, item_service, test_table, sample_item):
        """Test contains when list contains value."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="contains(#t, :value)",
            ExpressionAttributeNames={"#t": "tags"},
            ExpressionAttributeValues={":value": {"S": "tag1"}},
        )
        
        response = await item_service.put_item(request)
        assert response is not None


class TestBetweenAndIn:
    """Test BETWEEN and IN operators."""
    
    @pytest.mark.asyncio
    async def test_between_true(self, item_service, test_table, sample_item):
        """Test BETWEEN when value is in range."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "age": {"N": "35"},
            },
            ConditionExpression="#a BETWEEN :low AND :high",
            ExpressionAttributeNames={"#a": "age"},
            ExpressionAttributeValues={
                ":low": {"N": "20"},
                ":high": {"N": "40"},
            },
        )
        
        response = await item_service.put_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_between_false(self, item_service, test_table, sample_item):
        """Test BETWEEN when value is out of range."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "age": {"N": "35"},
            },
            ConditionExpression="#a BETWEEN :low AND :high",
            ExpressionAttributeNames={"#a": "age"},
            ExpressionAttributeValues={
                ":low": {"N": "50"},
                ":high": {"N": "60"},
            },
        )
        
        with pytest.raises(ConditionalCheckFailedException):
            await item_service.put_item(request)
    
    @pytest.mark.asyncio
    async def test_in_true(self, item_service, test_table, sample_item):
        """Test IN when value is in list."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="#n IN (:val1, :val2, :val3)",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={
                ":val1": {"S": "Wrong Name"},
                ":val2": {"S": "John Doe"},
                ":val3": {"S": "Another Wrong Name"},
            },
        )
        
        response = await item_service.put_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_in_false(self, item_service, test_table, sample_item):
        """Test IN when value is not in list."""
        from dyscount_core.models.operations import PutItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": pk},
                "sk": {"S": sk},
                "name": {"S": "Updated Name"},
            },
            ConditionExpression="#n IN (:val1, :val2, :val3)",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={
                ":val1": {"S": "Wrong Name 1"},
                ":val2": {"S": "Wrong Name 2"},
                ":val3": {"S": "Wrong Name 3"},
            },
        )
        
        with pytest.raises(ConditionalCheckFailedException):
            await item_service.put_item(request)


class TestDeleteItemConditions:
    """Test ConditionExpression with DeleteItem."""
    
    @pytest.mark.asyncio
    async def test_delete_with_condition_true(self, item_service, test_table, sample_item):
        """Test DeleteItem with condition that is true."""
        from dyscount_core.models.operations import DeleteItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = DeleteItemRequest(
            TableName=test_table,
            Key={
                "pk": {"S": pk},
                "sk": {"S": sk},
            },
            ConditionExpression="#n = :val",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":val": {"S": "John Doe"}},
        )
        
        response = await item_service.delete_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_delete_with_condition_false(self, item_service, test_table, sample_item):
        """Test DeleteItem with condition that is false."""
        from dyscount_core.models.operations import DeleteItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = DeleteItemRequest(
            TableName=test_table,
            Key={
                "pk": {"S": pk},
                "sk": {"S": sk},
            },
            ConditionExpression="#n = :val",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":val": {"S": "Wrong Name"}},
        )
        
        with pytest.raises(ConditionalCheckFailedException):
            await item_service.delete_item(request)


class TestUpdateItemConditions:
    """Test ConditionExpression with UpdateItem."""
    
    @pytest.mark.asyncio
    async def test_update_with_condition_true(self, item_service, test_table, sample_item):
        """Test UpdateItem with condition that is true."""
        from dyscount_core.models.operations import UpdateItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = UpdateItemRequest(
            TableName=test_table,
            Key={
                "pk": {"S": pk},
                "sk": {"S": sk},
            },
            UpdateExpression="SET #n = :new_name",
            ConditionExpression="#n = :old_name",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={
                ":old_name": {"S": "John Doe"},
                ":new_name": {"S": "Updated Name"},
            },
        )
        
        response = await item_service.update_item(request)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_update_with_condition_false(self, item_service, test_table, sample_item):
        """Test UpdateItem with condition that is false."""
        from dyscount_core.models.operations import UpdateItemRequest
        
        pk = sample_item["pk"]["S"]
        sk = sample_item["sk"]["S"]
        
        request = UpdateItemRequest(
            TableName=test_table,
            Key={
                "pk": {"S": pk},
                "sk": {"S": sk},
            },
            UpdateExpression="SET #n = :new_name",
            ConditionExpression="#n = :wrong_name",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={
                ":wrong_name": {"S": "Wrong Name"},
                ":new_name": {"S": "Updated Name"},
            },
        )
        
        with pytest.raises(ConditionalCheckFailedException):
            await item_service.update_item(request)


class TestConditionalPutNewItem:
    """Test ConditionExpression for new items (attribute_not_exists on pk)."""
    
    @pytest.mark.asyncio
    async def test_put_new_item_if_not_exists(self, item_service, test_table):
        """Test putting a new item only if it doesn't exist."""
        from dyscount_core.models.operations import PutItemRequest
        
        # First put - should succeed
        request = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "user#new"},
                "sk": {"S": "profile"},
                "name": {"S": "New User"},
            },
            ConditionExpression="attribute_not_exists(#pk)",
            ExpressionAttributeNames={"#pk": "pk"},
        )
        
        response = await item_service.put_item(request)
        assert response is not None
        
        # Second put - should fail because item exists
        request2 = PutItemRequest(
            TableName=test_table,
            Item={
                "pk": {"S": "user#new"},
                "sk": {"S": "profile"},
                "name": {"S": "Updated User"},
            },
            ConditionExpression="attribute_not_exists(#pk)",
            ExpressionAttributeNames={"#pk": "pk"},
        )
        
        with pytest.raises(ConditionalCheckFailedException):
            await item_service.put_item(request2)
