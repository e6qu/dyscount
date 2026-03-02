"""E2E tests for DynamoDB data operations using boto3."""

import pytest
from botocore.exceptions import ClientError


class TestPutItem:
    """E2E tests for PutItem operation."""
    
    def test_put_new_item(self, dynamodb_client, test_table):
        """Test putting a new item into a table."""
        item = {
            "pk": {"S": "test_item"},
            "name": {"S": "Test Name"},
            "count": {"N": "42"},
        }
        
        response = dynamodb_client.put_item(
            TableName=test_table,
            Item=item,
        )
        
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        
        # Verify item was stored
        get_response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "test_item"}},
        )
        assert get_response["Item"] == item
    
    def test_put_item_return_values_all_old_new_item(self, dynamodb_client, test_table):
        """Test PutItem on new item with ReturnValues=ALL_OLD."""
        item = {
            "pk": {"S": "test_item"},
            "name": {"S": "Test Name"},
        }
        
        response = dynamodb_client.put_item(
            TableName=test_table,
            Item=item,
            ReturnValues="ALL_OLD",
        )
        
        # For new items, Attributes should not be present
        assert "Attributes" not in response
    
    def test_put_item_replace_existing(self, dynamodb_client, test_table):
        """Test replacing an existing item."""
        # First put
        item1 = {
            "pk": {"S": "test_item"},
            "name": {"S": "Original Name"},
            "count": {"N": "10"},
        }
        dynamodb_client.put_item(TableName=test_table, Item=item1)
        
        # Replace with new item
        item2 = {
            "pk": {"S": "test_item"},
            "name": {"S": "Updated Name"},
            "status": {"S": "active"},
        }
        
        response = dynamodb_client.put_item(
            TableName=test_table,
            Item=item2,
            ReturnValues="ALL_OLD",
        )
        
        # Should return old attributes
        assert response["Attributes"] == item1
        
        # Verify new item
        get_response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "test_item"}},
        )
        assert get_response["Item"] == item2
    
    def test_put_item_all_attribute_types(self, dynamodb_client, test_table):
        """Test putting item with all DynamoDB attribute types."""
        item = {
            "pk": {"S": "all_types"},
            "string_attr": {"S": "hello"},
            "number_attr": {"N": "123.456"},
            "bool_attr": {"BOOL": True},
            "null_attr": {"NULL": True},
            "list_attr": {"L": [{"S": "item1"}, {"N": "42"}]},
            "map_attr": {"M": {"nested": {"S": "value"}}},
            "string_set": {"SS": ["a", "b", "c"]},
            "number_set": {"NS": ["1", "2", "3"]},
        }
        
        response = dynamodb_client.put_item(
            TableName=test_table,
            Item=item,
        )
        
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        
        # Verify all attributes stored correctly
        get_response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "all_types"}},
        )
        assert get_response["Item"] == item
    
    def test_put_item_conditional(self, dynamodb_client, test_table):
        """Test conditional put using ConditionExpression."""
        # First put an item
        dynamodb_client.put_item(
            TableName=test_table,
            Item={"pk": {"S": "conditional"}, "status": {"S": "pending"}},
        )
        
        # Conditional put that should succeed
        response = dynamodb_client.put_item(
            TableName=test_table,
            Item={"pk": {"S": "conditional"}, "status": {"S": "active"}},
            ConditionExpression="#s = :expected",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":expected": {"S": "pending"}},
        )
        
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    def test_put_item_conditional_failure(self, dynamodb_client, test_table):
        """Test conditional put that fails."""
        # First put an item
        dynamodb_client.put_item(
            TableName=test_table,
            Item={"pk": {"S": "conditional"}, "status": {"S": "active"}},
        )
        
        # Conditional put that should fail
        with pytest.raises(ClientError) as exc_info:
            dynamodb_client.put_item(
                TableName=test_table,
                Item={"pk": {"S": "conditional"}, "status": {"S": "inactive"}},
                ConditionExpression="#s = :expected",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":expected": {"S": "pending"}},
            )
        
        assert exc_info.value.response["Error"]["Code"] == "ConditionalCheckFailedException"


class TestGetItem:
    """E2E tests for GetItem operation."""
    
    def test_get_existing_item(self, dynamodb_client, test_table, sample_item):
        """Test retrieving an existing item."""
        # Put the item first
        dynamodb_client.put_item(
            TableName=test_table,
            Item=sample_item,
        )
        
        response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "user#123"}},
        )
        
        assert response["Item"] == sample_item
    
    def test_get_nonexistent_item(self, dynamodb_client, test_table):
        """Test retrieving a non-existent item."""
        response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "does_not_exist"}},
        )
        
        assert "Item" not in response
    
    def test_get_item_with_projection(self, dynamodb_client, test_table, sample_item):
        """Test GetItem with ProjectionExpression."""
        dynamodb_client.put_item(
            TableName=test_table,
            Item=sample_item,
        )
        
        response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "user#123"}},
            ProjectionExpression="#n, #a",
            ExpressionAttributeNames={"#n": "name", "#a": "age"},
        )
        
        # Should only return projected attributes + pk
        assert "name" in response["Item"]
        assert "age" in response["Item"]
        assert "active" not in response["Item"]
    
    def test_get_item_consistent_read(self, dynamodb_client, test_table, sample_item):
        """Test GetItem with ConsistentRead=True."""
        dynamodb_client.put_item(
            TableName=test_table,
            Item=sample_item,
        )
        
        response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "user#123"}},
            ConsistentRead=True,
        )
        
        assert response["Item"] == sample_item
        
    def test_get_item_consumed_capacity(self, dynamodb_client, test_table, sample_item):
        """Test GetItem returns ConsumedCapacity."""
        dynamodb_client.put_item(
            TableName=test_table,
            Item=sample_item,
        )
        
        response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "user#123"}},
            ReturnConsumedCapacity="TOTAL",
        )
        
        assert "ConsumedCapacity" in response
        assert response["ConsumedCapacity"]["TableName"] == test_table
        assert "CapacityUnits" in response["ConsumedCapacity"]


class TestUpdateItem:
    """E2E tests for UpdateItem operation."""
    
    def test_update_set_attribute(self, dynamodb_client, test_table):
        """Test updating an attribute with SET."""
        # Create initial item
        dynamodb_client.put_item(
            TableName=test_table,
            Item={"pk": {"S": "update_test"}, "name": {"S": "Original"}},
        )
        
        response = dynamodb_client.update_item(
            TableName=test_table,
            Key={"pk": {"S": "update_test"}},
            UpdateExpression="SET #n = :new_name",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":new_name": {"S": "Updated"}},
        )
        
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        
        # Verify update
        get_response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "update_test"}},
        )
        assert get_response["Item"]["name"] == {"S": "Updated"}
    
    def test_update_remove_attribute(self, dynamodb_client, test_table):
        """Test removing an attribute with REMOVE."""
        # Create item with multiple attributes
        dynamodb_client.put_item(
            TableName=test_table,
            Item={
                "pk": {"S": "remove_test"},
                "name": {"S": "Test"},
                "temp": {"S": "to_be_removed"},
            },
        )
        
        dynamodb_client.update_item(
            TableName=test_table,
            Key={"pk": {"S": "remove_test"}},
            UpdateExpression="REMOVE #t",
            ExpressionAttributeNames={"#t": "temp"},
        )
        
        # Verify attribute removed
        get_response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "remove_test"}},
        )
        assert "temp" not in get_response["Item"]
        assert "name" in get_response["Item"]
    
    def test_update_add_to_number(self, dynamodb_client, test_table):
        """Test adding to a number with ADD."""
        dynamodb_client.put_item(
            TableName=test_table,
            Item={"pk": {"S": "add_test"}, "counter": {"N": "10"}},
        )
        
        dynamodb_client.update_item(
            TableName=test_table,
            Key={"pk": {"S": "add_test"}},
            UpdateExpression="ADD #c :inc",
            ExpressionAttributeNames={"#c": "counter"},
            ExpressionAttributeValues={":inc": {"N": "5"}},
        )
        
        get_response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "add_test"}},
        )
        assert get_response["Item"]["counter"] == {"N": "15"}
    
    def test_update_return_values(self, dynamodb_client, test_table):
        """Test UpdateItem with different ReturnValues options."""
        # Create initial item
        dynamodb_client.put_item(
            TableName=test_table,
            Item={"pk": {"S": "return_test"}, "name": {"S": "Original"}},
        )
        
        # Test ALL_OLD
        response = dynamodb_client.update_item(
            TableName=test_table,
            Key={"pk": {"S": "return_test"}},
            UpdateExpression="SET #n = :new_name",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":new_name": {"S": "Updated"}},
            ReturnValues="ALL_OLD",
        )
        assert response["Attributes"]["name"] == {"S": "Original"}
        
        # Test ALL_NEW
        response = dynamodb_client.update_item(
            TableName=test_table,
            Key={"pk": {"S": "return_test"}},
            UpdateExpression="SET #s = :status",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":status": {"S": "active"}},
            ReturnValues="ALL_NEW",
        )
        assert response["Attributes"]["name"] == {"S": "Updated"}
        assert response["Attributes"]["status"] == {"S": "active"}
    
    def test_update_conditional(self, dynamodb_client, test_table):
        """Test conditional update."""
        dynamodb_client.put_item(
            TableName=test_table,
            Item={"pk": {"S": "cond_update"}, "status": {"S": "pending"}},
        )
        
        response = dynamodb_client.update_item(
            TableName=test_table,
            Key={"pk": {"S": "cond_update"}},
            UpdateExpression="SET #s = :new_status",
            ConditionExpression="#s = :expected",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":new_status": {"S": "active"},
                ":expected": {"S": "pending"},
            },
            ReturnValues="ALL_NEW",
        )
        
        assert response["Attributes"]["status"] == {"S": "active"}


class TestDeleteItem:
    """E2E tests for DeleteItem operation."""
    
    def test_delete_existing_item(self, dynamodb_client, test_table):
        """Test deleting an existing item."""
        # Create item
        dynamodb_client.put_item(
            TableName=test_table,
            Item={"pk": {"S": "to_delete"}, "name": {"S": "Delete Me"}},
        )
        
        response = dynamodb_client.delete_item(
            TableName=test_table,
            Key={"pk": {"S": "to_delete"}},
        )
        
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        
        # Verify deletion
        get_response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "to_delete"}},
        )
        assert "Item" not in get_response
    
    def test_delete_nonexistent_item(self, dynamodb_client, test_table):
        """Test deleting a non-existent item (should not error)."""
        response = dynamodb_client.delete_item(
            TableName=test_table,
            Key={"pk": {"S": "does_not_exist"}},
        )
        
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    def test_delete_return_values_all_old(self, dynamodb_client, test_table):
        """Test DeleteItem with ReturnValues=ALL_OLD."""
        item = {"pk": {"S": "delete_return"}, "name": {"S": "To Delete"}}
        dynamodb_client.put_item(
            TableName=test_table,
            Item=item,
        )
        
        response = dynamodb_client.delete_item(
            TableName=test_table,
            Key={"pk": {"S": "delete_return"}},
            ReturnValues="ALL_OLD",
        )
        
        assert response["Attributes"] == item
    
    def test_delete_conditional(self, dynamodb_client, test_table):
        """Test conditional delete."""
        dynamodb_client.put_item(
            TableName=test_table,
            Item={"pk": {"S": "cond_delete"}, "status": {"S": "archived"}},
        )
        
        response = dynamodb_client.delete_item(
            TableName=test_table,
            Key={"pk": {"S": "cond_delete"}},
            ConditionExpression="#s = :expected",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":expected": {"S": "archived"}},
        )
        
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        
        # Verify deleted
        get_response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "cond_delete"}},
        )
        assert "Item" not in get_response
    
    def test_delete_conditional_failure(self, dynamodb_client, test_table):
        """Test conditional delete that fails."""
        dynamodb_client.put_item(
            TableName=test_table,
            Item={"pk": {"S": "cond_delete"}, "status": {"S": "active"}},
        )
        
        with pytest.raises(ClientError) as exc_info:
            dynamodb_client.delete_item(
                TableName=test_table,
                Key={"pk": {"S": "cond_delete"}},
                ConditionExpression="#s = :expected",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":expected": {"S": "archived"}},
            )
        
        assert exc_info.value.response["Error"]["Code"] == "ConditionalCheckFailedException"


class TestItemLifecycle:
    """Integration tests for complete item lifecycle."""
    
    def test_full_item_lifecycle(self, dynamodb_client, test_table):
        """Test complete lifecycle: Put → Get → Update → Get → Delete → Get."""
        pk = {"S": "lifecycle_test"}
        
        # 1. Put new item
        initial_item = {
            "pk": pk,
            "name": {"S": "Initial"},
            "count": {"N": "0"},
        }
        dynamodb_client.put_item(
            TableName=test_table,
            Item=initial_item,
        )
        
        # 2. Get and verify
        get_response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": pk},
        )
        assert get_response["Item"] == initial_item
        
        # 3. Update
        dynamodb_client.update_item(
            TableName=test_table,
            Key={"pk": pk},
            UpdateExpression="SET #n = :new_name, #c = :new_count",
            ExpressionAttributeNames={"#n": "name", "#c": "count"},
            ExpressionAttributeValues={
                ":new_name": {"S": "Updated"},
                ":new_count": {"N": "42"},
            },
        )
        
        # 4. Get and verify update
        get_response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": pk},
        )
        assert get_response["Item"]["name"] == {"S": "Updated"}
        assert get_response["Item"]["count"] == {"N": "42"}
        
        # 5. Delete
        dynamodb_client.delete_item(
            TableName=test_table,
            Key={"pk": pk},
        )
        
        # 6. Get and verify deletion
        get_response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": pk},
        )
        assert "Item" not in get_response
    
    def test_multiple_items_same_table(self, dynamodb_client, test_table):
        """Test operations with multiple items in same table."""
        items = [
            {"pk": {"S": "item1"}, "data": {"S": "data1"}},
            {"pk": {"S": "item2"}, "data": {"S": "data2"}},
            {"pk": {"S": "item3"}, "data": {"S": "data3"}},
        ]
        
        # Put all items
        for item in items:
            dynamodb_client.put_item(
                TableName=test_table,
                Item=item,
            )
        
        # Get each item
        for item in items:
            pk = item["pk"]["S"]
            response = dynamodb_client.get_item(
                TableName=test_table,
                Key={"pk": {"S": pk}},
            )
            assert response["Item"] == item
        
        # Update one item
        dynamodb_client.update_item(
            TableName=test_table,
            Key={"pk": {"S": "item2"}},
            UpdateExpression="SET #d = :new_data",
            ExpressionAttributeNames={"#d": "data"},
            ExpressionAttributeValues={":new_data": {"S": "updated_data2"}},
        )
        
        # Verify only that item was updated
        response = dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "item2"}},
        )
        assert response["Item"]["data"] == {"S": "updated_data2"}
        
        # Delete one item
        dynamodb_client.delete_item(
            TableName=test_table,
            Key={"pk": {"S": "item1"}},
        )
        
        # Verify deleted and others still exist
        assert "Item" not in dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "item1"}},
        )
        assert "Item" in dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "item2"}},
        )
        assert "Item" in dynamodb_client.get_item(
            TableName=test_table,
            Key={"pk": {"S": "item3"}},
        )


class TestCompositeKey:
    """E2E tests for tables with composite primary key."""
    
    def test_put_and_get_with_sort_key(self, dynamodb_client, test_table_with_sort_key):
        """Test PutItem and GetItem with composite key."""
        item = {
            "pk": {"S": "user#123"},
            "sk": {"S": "profile"},
            "name": {"S": "John"},
        }
        
        dynamodb_client.put_item(
            TableName=test_table_with_sort_key,
            Item=item,
        )
        
        response = dynamodb_client.get_item(
            TableName=test_table_with_sort_key,
            Key={
                "pk": {"S": "user#123"},
                "sk": {"S": "profile"},
            },
        )
        
        assert response["Item"] == item
    
    def test_multiple_items_same_pk(self, dynamodb_client, test_table_with_sort_key):
        """Test multiple items with same partition key but different sort keys."""
        items = [
            {"pk": {"S": "user#123"}, "sk": {"S": "profile"}, "data": {"S": "profile_data"}},
            {"pk": {"S": "user#123"}, "sk": {"S": "settings"}, "data": {"S": "settings_data"}},
            {"pk": {"S": "user#123"}, "sk": {"S": "orders"}, "data": {"S": "orders_data"}},
        ]
        
        for item in items:
            dynamodb_client.put_item(
                TableName=test_table_with_sort_key,
                Item=item,
            )
        
        # Get each item individually
        for item in items:
            response = dynamodb_client.get_item(
                TableName=test_table_with_sort_key,
                Key={
                    "pk": item["pk"],
                    "sk": item["sk"],
                },
            )
            assert response["Item"] == item
    
    def test_update_with_composite_key(self, dynamodb_client, test_table_with_sort_key):
        """Test UpdateItem with composite key."""
        dynamodb_client.put_item(
            TableName=test_table_with_sort_key,
            Item={
                "pk": {"S": "user#123"},
                "sk": {"S": "profile"},
                "name": {"S": "Original"},
            },
        )
        
        dynamodb_client.update_item(
            TableName=test_table_with_sort_key,
            Key={
                "pk": {"S": "user#123"},
                "sk": {"S": "profile"},
            },
            UpdateExpression="SET #n = :new_name",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":new_name": {"S": "Updated"}},
        )
        
        response = dynamodb_client.get_item(
            TableName=test_table_with_sort_key,
            Key={
                "pk": {"S": "user#123"},
                "sk": {"S": "profile"},
            },
        )
        
        assert response["Item"]["name"] == {"S": "Updated"}
    
    def test_delete_with_composite_key(self, dynamodb_client, test_table_with_sort_key):
        """Test DeleteItem with composite key."""
        dynamodb_client.put_item(
            TableName=test_table_with_sort_key,
            Item={
                "pk": {"S": "user#123"},
                "sk": {"S": "to_delete"},
                "data": {"S": "delete_me"},
            },
        )
        
        dynamodb_client.delete_item(
            TableName=test_table_with_sort_key,
            Key={
                "pk": {"S": "user#123"},
                "sk": {"S": "to_delete"},
            },
        )
        
        response = dynamodb_client.get_item(
            TableName=test_table_with_sort_key,
            Key={
                "pk": {"S": "user#123"},
                "sk": {"S": "to_delete"},
            },
        )
        
        assert "Item" not in response


class TestErrorHandling:
    """E2E tests for error scenarios."""
    
    def test_get_item_table_not_found(self, dynamodb_client):
        """Test GetItem with non-existent table."""
        with pytest.raises(ClientError) as exc_info:
            dynamodb_client.get_item(
                TableName="this_table_does_not_exist",
                Key={"pk": {"S": "test"}},
            )
        
        assert exc_info.value.response["Error"]["Code"] == "ResourceNotFoundException"
    
    def test_put_item_table_not_found(self, dynamodb_client):
        """Test PutItem with non-existent table."""
        with pytest.raises(ClientError) as exc_info:
            dynamodb_client.put_item(
                TableName="this_table_does_not_exist",
                Item={"pk": {"S": "test"}},
            )
        
        assert exc_info.value.response["Error"]["Code"] == "ResourceNotFoundException"
    
    def test_put_item_missing_key(self, dynamodb_client, test_table):
        """Test PutItem without partition key."""
        with pytest.raises(ClientError) as exc_info:
            dynamodb_client.put_item(
                TableName=test_table,
                Item={"name": {"S": "no_key"}},
            )
        
        assert exc_info.value.response["Error"]["Code"] == "ValidationException"
