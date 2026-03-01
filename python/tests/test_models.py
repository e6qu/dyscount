"""Tests for dyscount-core models."""

import base64
from datetime import datetime, timezone

import pytest

from dyscount_core.models import (
    AttributeDefinition,
    AttributeValue,
    BillingMode,
    CreateTableRequest,
    CreateTableResponse,
    DeleteTableRequest,
    DeleteTableResponse,
    DescribeEndpointsRequest,
    DescribeEndpointsResponse,
    DescribeTableRequest,
    DescribeTableResponse,
    KeySchemaElement,
    KeyType,
    ListTablesRequest,
    ListTablesResponse,
    ProvisionedThroughput,
    ScalarAttributeType,
    TableMetadata,
    TableStatus,
    deserialize_dynamodb_json,
    serialize_to_dynamodb_json,
)


class TestAttributeValue:
    """Test AttributeValue model."""

    def test_create_string(self):
        """Test creating a string attribute value."""
        av = AttributeValue(S="hello")
        assert av.S == "hello"
        assert av.get_type() == "S"
        assert av.get_value() == "hello"

    def test_create_number(self):
        """Test creating a number attribute value."""
        av = AttributeValue(N="123.45")
        assert av.N == "123.45"
        assert av.get_type() == "N"
        assert av.get_value() == "123.45"

    def test_create_binary(self):
        """Test creating a binary attribute value."""
        data = b"binary data"
        av = AttributeValue(B=data)
        assert av.B == data
        assert av.get_type() == "B"
        assert av.get_value() == data

    def test_create_boolean(self):
        """Test creating a boolean attribute value."""
        av = AttributeValue(BOOL=True)
        assert av.BOOL is True
        assert av.get_type() == "BOOL"
        assert av.get_value() is True

    def test_create_null(self):
        """Test creating a null attribute value."""
        av = AttributeValue(NULL=True)
        assert av.NULL is True
        assert av.get_type() == "NULL"
        assert av.get_value() is None

    def test_create_map(self):
        """Test creating a map attribute value."""
        inner = AttributeValue(S="inner_value")
        av = AttributeValue(M={"inner": inner})
        assert av.M == {"inner": inner}
        assert av.get_type() == "M"
        assert av.get_value() == {"inner": inner}

    def test_create_list(self):
        """Test creating a list attribute value."""
        items = [AttributeValue(S="item1"), AttributeValue(N="42")]
        av = AttributeValue(L=items)
        assert av.L == items
        assert av.get_type() == "L"
        assert len(av.get_value()) == 2

    def test_create_string_set(self):
        """Test creating a string set attribute value."""
        av = AttributeValue(SS=["a", "b", "c"])
        assert av.SS == ["a", "b", "c"]
        assert av.get_type() == "SS"

    def test_create_number_set(self):
        """Test creating a number set attribute value."""
        av = AttributeValue(NS=["1", "2", "3.14"])
        assert av.NS == ["1", "2", "3.14"]
        assert av.get_type() == "NS"

    def test_create_binary_set(self):
        """Test creating a binary set attribute value."""
        data = [b"data1", b"data2"]
        av = AttributeValue(BS=data)
        assert av.BS == data
        assert av.get_type() == "BS"

    def test_validate_single_type(self):
        """Test that exactly one type must be set."""
        # No type set - should fail
        with pytest.raises(ValueError, match="Exactly one type must be set"):
            AttributeValue()
        
        # Multiple types set - should fail
        with pytest.raises(ValueError, match="Exactly one type must be set"):
            AttributeValue(S="hello", N="42")

    def test_to_dynamodb_json_string(self):
        """Test converting string to DynamoDB JSON."""
        av = AttributeValue(S="hello")
        json = av.to_dynamodb_json()
        assert json == {"S": "hello"}

    def test_to_dynamodb_json_number(self):
        """Test converting number to DynamoDB JSON."""
        av = AttributeValue(N="123.45")
        json = av.to_dynamodb_json()
        assert json == {"N": "123.45"}

    def test_to_dynamodb_json_binary(self):
        """Test converting binary to DynamoDB JSON."""
        data = b"binary data"
        av = AttributeValue(B=data)
        json = av.to_dynamodb_json()
        assert json == {"B": base64.b64encode(data).decode("ascii")}

    def test_to_dynamodb_json_map(self):
        """Test converting map to DynamoDB JSON."""
        av = AttributeValue(M={
            "name": AttributeValue(S="John"),
            "age": AttributeValue(N="30")
        })
        json = av.to_dynamodb_json()
        assert json == {
            "M": {
                "name": {"S": "John"},
                "age": {"N": "30"}
            }
        }

    def test_to_dynamodb_json_list(self):
        """Test converting list to DynamoDB JSON."""
        av = AttributeValue(L=[
            AttributeValue(S="item1"),
            AttributeValue(BOOL=True)
        ])
        json = av.to_dynamodb_json()
        assert json == {
            "L": [
                {"S": "item1"},
                {"BOOL": True}
            ]
        }

    def test_from_dynamodb_json_string(self):
        """Test creating from DynamoDB JSON string."""
        av = AttributeValue.from_dynamodb_json({"S": "hello"})
        assert av.S == "hello"
        assert av.get_type() == "S"

    def test_from_dynamodb_json_number(self):
        """Test creating from DynamoDB JSON number."""
        av = AttributeValue.from_dynamodb_json({"N": "123.45"})
        assert av.N == "123.45"
        assert av.get_type() == "N"

    def test_from_dynamodb_json_binary(self):
        """Test creating from DynamoDB JSON binary."""
        data = b"binary data"
        encoded = base64.b64encode(data).decode("ascii")
        av = AttributeValue.from_dynamodb_json({"B": encoded})
        assert av.B == data
        assert av.get_type() == "B"

    def test_from_dynamodb_json_map(self):
        """Test creating from DynamoDB JSON map."""
        av = AttributeValue.from_dynamodb_json({
            "M": {
                "name": {"S": "John"},
                "age": {"N": "30"}
            }
        })
        assert av.get_type() == "M"
        assert av.M["name"].S == "John"
        assert av.M["age"].N == "30"

    def test_from_dynamodb_json_invalid(self):
        """Test error handling for invalid DynamoDB JSON."""
        with pytest.raises(ValueError, match="Expected dict"):
            AttributeValue.from_dynamodb_json("not a dict")
        
        with pytest.raises(ValueError, match="Expected exactly one type descriptor"):
            AttributeValue.from_dynamodb_json({})
        
        with pytest.raises(ValueError, match="Expected exactly one type descriptor"):
            AttributeValue.from_dynamodb_json({"S": "hello", "N": "42"})
        
        with pytest.raises(ValueError, match="Unknown type descriptor"):
            AttributeValue.from_dynamodb_json({"UNKNOWN": "value"})

    def test_round_trip(self):
        """Test round-trip conversion to/from DynamoDB JSON."""
        original = AttributeValue(M={
            "name": AttributeValue(S="John"),
            "age": AttributeValue(N="30"),
            "active": AttributeValue(BOOL=True),
            "data": AttributeValue(B=b"binary"),
            "tags": AttributeValue(SS=["a", "b"])
        })
        
        json_data = original.to_dynamodb_json()
        restored = AttributeValue.from_dynamodb_json(json_data)
        
        assert restored.M["name"].S == "John"
        assert restored.M["age"].N == "30"
        assert restored.M["active"].BOOL is True
        assert restored.M["data"].B == b"binary"
        assert restored.M["tags"].SS == ["a", "b"]

    def test_from_python_value(self):
        """Test creating from Python native values."""
        assert AttributeValue.from_python_value(None).NULL is True
        assert AttributeValue.from_python_value(True).BOOL is True
        assert AttributeValue.from_python_value("hello").S == "hello"
        assert AttributeValue.from_python_value(42).N == "42"
        assert AttributeValue.from_python_value(3.14).N == "3.14"
        assert AttributeValue.from_python_value(b"data").B == b"data"
        
        # Dict
        av = AttributeValue.from_python_value({"name": "John", "age": 30})
        assert av.M["name"].S == "John"
        assert av.M["age"].N == "30"
        
        # List
        av = AttributeValue.from_python_value(["a", "b", "c"])
        assert len(av.L) == 3
        assert av.L[0].S == "a"

    def test_to_python_value(self):
        """Test converting to Python native values."""
        assert AttributeValue(NULL=True).to_python_value() is None
        assert AttributeValue(BOOL=True).to_python_value() is True
        assert AttributeValue(S="hello").to_python_value() == "hello"
        assert AttributeValue(N="42").to_python_value() == 42
        assert AttributeValue(N="3.14").to_python_value() == 3.14
        assert AttributeValue(B=b"data").to_python_value() == b"data"
        
        # Map
        av = AttributeValue(M={
            "name": AttributeValue(S="John"),
            "age": AttributeValue(N="30")
        })
        assert av.to_python_value() == {"name": "John", "age": 30}
        
        # List
        av = AttributeValue(L=[AttributeValue(S="a"), AttributeValue(N="1")])
        assert av.to_python_value() == ["a", 1]
        
        # String Set
        av = AttributeValue(SS=["a", "b", "c"])
        assert av.to_python_value() == {"a", "b", "c"}
        
        # Number Set
        av = AttributeValue(NS=["1", "2", "3"])
        assert av.to_python_value() == {1, 2, 3}


class TestSerializeDeserialize:
    """Test serialization/deserialization helpers."""

    def test_serialize_to_dynamodb_json(self):
        """Test serializing a dict to DynamoDB JSON."""
        item = {
            "pk": AttributeValue(S="user123"),
            "name": "John",  # Native Python value
            "age": 30,
        }
        result = serialize_to_dynamodb_json(item)
        assert result == {
            "pk": {"S": "user123"},
            "name": {"S": "John"},
            "age": {"N": "30"}
        }

    def test_deserialize_dynamodb_json(self):
        """Test deserializing DynamoDB JSON to AttributeValues."""
        data = {
            "pk": {"S": "user123"},
            "age": {"N": "30"}
        }
        result = deserialize_dynamodb_json(data)
        assert result["pk"].S == "user123"
        assert result["age"].N == "30"


class TestKeySchemaElement:
    """Test KeySchemaElement model."""

    def test_create_hash_key(self):
        """Test creating a hash key element."""
        key = KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH)
        assert key.AttributeName == "pk"
        assert key.KeyType == KeyType.HASH
        assert key.KeyType.value == "HASH"

    def test_create_range_key(self):
        """Test creating a range key element."""
        key = KeySchemaElement(AttributeName="sk", KeyType=KeyType.RANGE)
        assert key.AttributeName == "sk"
        assert key.KeyType == KeyType.RANGE


class TestAttributeDefinition:
    """Test AttributeDefinition model."""

    def test_create_string_attr(self):
        """Test creating a string attribute definition."""
        attr = AttributeDefinition(
            AttributeName="pk",
            AttributeType=ScalarAttributeType.STRING
        )
        assert attr.AttributeName == "pk"
        assert attr.AttributeType == ScalarAttributeType.STRING
        assert attr.AttributeType.value == "S"

    def test_create_number_attr(self):
        """Test creating a number attribute definition."""
        attr = AttributeDefinition(
            AttributeName="count",
            AttributeType=ScalarAttributeType.NUMBER
        )
        assert attr.AttributeType == ScalarAttributeType.NUMBER
        assert attr.AttributeType.value == "N"

    def test_create_binary_attr(self):
        """Test creating a binary attribute definition."""
        attr = AttributeDefinition(
            AttributeName="data",
            AttributeType=ScalarAttributeType.BINARY
        )
        assert attr.AttributeType == ScalarAttributeType.BINARY
        assert attr.AttributeType.value == "B"


class TestProvisionedThroughput:
    """Test ProvisionedThroughput model."""

    def test_create(self):
        """Test creating provisioned throughput."""
        pt = ProvisionedThroughput(ReadCapacityUnits=5, WriteCapacityUnits=10)
        assert pt.ReadCapacityUnits == 5
        assert pt.WriteCapacityUnits == 10

    def test_validation(self):
        """Test validation of capacity units."""
        with pytest.raises(ValueError):
            ProvisionedThroughput(ReadCapacityUnits=0, WriteCapacityUnits=5)
        
        with pytest.raises(ValueError):
            ProvisionedThroughput(ReadCapacityUnits=5, WriteCapacityUnits=0)


class TestTableMetadata:
    """Test TableMetadata model."""

    def test_create_minimal(self):
        """Test creating minimal table metadata."""
        metadata = TableMetadata(
            TableName="TestTable",
            KeySchema=[KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH)],
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="pk",
                    AttributeType=ScalarAttributeType.STRING
                )
            ]
        )
        assert metadata.TableName == "TestTable"
        assert metadata.table_status == TableStatus.CREATING
        assert metadata.ItemCount == 0
        assert metadata.TableSizeBytes == 0

    def test_create_full(self):
        """Test creating full table metadata."""
        now = datetime.now(timezone.utc)
        metadata = TableMetadata(
            TableName="TestTable",
            TableArn="arn:aws:dynamodb:us-east-1:123456789:table/TestTable",
            TableId="12345678-1234-1234-1234-123456789012",
            TableStatus=TableStatus.ACTIVE,
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
                KeySchemaElement(AttributeName="sk", KeyType=KeyType.RANGE)
            ],
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="pk",
                    AttributeType=ScalarAttributeType.STRING
                ),
                AttributeDefinition(
                    AttributeName="sk",
                    AttributeType=ScalarAttributeType.NUMBER
                )
            ],
            ItemCount=100,
            TableSizeBytes=4096,
            CreationDateTime=now,
        )
        assert metadata.TableArn is not None
        assert metadata.TableId is not None
        assert len(metadata.KeySchema) == 2

    def test_get_key_schema_dict(self):
        """Test getting key schema as dictionary."""
        metadata = TableMetadata(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
                KeySchemaElement(AttributeName="sk", KeyType=KeyType.RANGE)
            ],
            AttributeDefinitions=[]
        )
        schema_dict = metadata.get_key_schema_dict()
        assert schema_dict == {"pk": "HASH", "sk": "RANGE"}

    def test_get_attribute_type(self):
        """Test getting attribute type by name."""
        metadata = TableMetadata(
            TableName="TestTable",
            KeySchema=[KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH)],
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="pk",
                    AttributeType=ScalarAttributeType.STRING
                )
            ]
        )
        assert metadata.get_attribute_type("pk") == ScalarAttributeType.STRING
        assert metadata.get_attribute_type("unknown") is None

    def test_get_hash_key(self):
        """Test getting hash key element."""
        metadata = TableMetadata(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
                KeySchemaElement(AttributeName="sk", KeyType=KeyType.RANGE)
            ],
            AttributeDefinitions=[]
        )
        hash_key = metadata.get_hash_key()
        assert hash_key is not None
        assert hash_key.AttributeName == "pk"
        assert hash_key.KeyType == KeyType.HASH

    def test_get_range_key(self):
        """Test getting range key element."""
        metadata = TableMetadata(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
                KeySchemaElement(AttributeName="sk", KeyType=KeyType.RANGE)
            ],
            AttributeDefinitions=[]
        )
        range_key = metadata.get_range_key()
        assert range_key is not None
        assert range_key.AttributeName == "sk"
        assert range_key.KeyType == KeyType.RANGE

    def test_get_range_key_none(self):
        """Test getting range key when there isn't one."""
        metadata = TableMetadata(
            TableName="TestTable",
            KeySchema=[KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH)],
            AttributeDefinitions=[]
        )
        assert metadata.get_range_key() is None


class TestCreateTableRequest:
    """Test CreateTableRequest model."""

    def test_create_minimal(self):
        """Test creating minimal request."""
        request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH)],
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="pk",
                    AttributeType=ScalarAttributeType.STRING
                )
            ]
        )
        assert request.table_name == "TestTable"
        assert request.billing_mode == "PROVISIONED"
        assert request.provisioned_throughput is not None
        assert request.provisioned_throughput.ReadCapacityUnits == 5

    def test_create_with_provisioned_throughput(self):
        """Test creating with custom provisioned throughput."""
        request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH)],
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="pk",
                    AttributeType=ScalarAttributeType.STRING
                )
            ],
            BillingMode="PROVISIONED",
            ProvisionedThroughput=ProvisionedThroughput(
                ReadCapacityUnits=10,
                WriteCapacityUnits=20
            )
        )
        assert request.provisioned_throughput.ReadCapacityUnits == 10
        assert request.provisioned_throughput.WriteCapacityUnits == 20

    def test_create_on_demand(self):
        """Test creating on-demand table."""
        request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH)],
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="pk",
                    AttributeType=ScalarAttributeType.STRING
                )
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        assert request.billing_mode == "PAY_PER_REQUEST"

    def test_table_name_validation(self):
        """Test table name validation."""
        with pytest.raises(ValueError):
            CreateTableRequest(
                TableName="",  # Empty name
                KeySchema=[],
                AttributeDefinitions=[]
            )


class TestCreateTableResponse:
    """Test CreateTableResponse model."""

    def test_create(self):
        """Test creating response."""
        metadata = TableMetadata(
            TableName="TestTable",
            KeySchema=[KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH)],
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="pk",
                    AttributeType=ScalarAttributeType.STRING
                )
            ]
        )
        response = CreateTableResponse(TableDescription=metadata)
        assert response.TableDescription.TableName == "TestTable"


class TestDeleteTableRequest:
    """Test DeleteTableRequest model."""

    def test_create(self):
        """Test creating request."""
        request = DeleteTableRequest(TableName="TestTable")
        assert request.TableName == "TestTable"

    def test_validation(self):
        """Test table name validation."""
        with pytest.raises(ValueError):
            DeleteTableRequest(TableName="")


class TestDeleteTableResponse:
    """Test DeleteTableResponse model."""

    def test_create(self):
        """Test creating response."""
        metadata = TableMetadata(
            TableName="TestTable",
            KeySchema=[KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH)],
            AttributeDefinitions=[]
        )
        response = DeleteTableResponse(TableDescription=metadata)
        assert response.TableDescription.TableName == "TestTable"

    def test_create_without_metadata(self):
        """Test creating response without metadata."""
        response = DeleteTableResponse()
        assert response.TableDescription is None


class TestDescribeTableRequest:
    """Test DescribeTableRequest model."""

    def test_create(self):
        """Test creating request."""
        request = DescribeTableRequest(TableName="TestTable")
        assert request.TableName == "TestTable"


class TestDescribeTableResponse:
    """Test DescribeTableResponse model."""

    def test_create(self):
        """Test creating response."""
        metadata = TableMetadata(
            TableName="TestTable",
            KeySchema=[KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH)],
            AttributeDefinitions=[]
        )
        response = DescribeTableResponse(Table=metadata)
        assert response.Table.TableName == "TestTable"


class TestListTablesRequest:
    """Test ListTablesRequest model."""

    def test_create_empty(self):
        """Test creating empty request."""
        request = ListTablesRequest()
        assert request.ExclusiveStartTableName is None
        assert request.Limit is None

    def test_create_with_params(self):
        """Test creating with parameters."""
        request = ListTablesRequest(
            ExclusiveStartTableName="TableA",
            Limit=10
        )
        assert request.ExclusiveStartTableName == "TableA"
        assert request.Limit == 10

    def test_limit_validation(self):
        """Test limit validation."""
        with pytest.raises(ValueError):
            ListTablesRequest(Limit=0)
        
        with pytest.raises(ValueError):
            ListTablesRequest(Limit=101)


class TestListTablesResponse:
    """Test ListTablesResponse model."""

    def test_create(self):
        """Test creating response."""
        response = ListTablesResponse(
            TableNames=["TableA", "TableB", "TableC"],
            LastEvaluatedTableName="TableC"
        )
        assert len(response.TableNames) == 3
        assert response.LastEvaluatedTableName == "TableC"

    def test_create_empty(self):
        """Test creating empty response."""
        response = ListTablesResponse(TableNames=[])
        assert response.TableNames == []
        assert response.LastEvaluatedTableName is None


class TestDescribeEndpointsRequest:
    """Test DescribeEndpointsRequest model."""

    def test_create(self):
        """Test creating request."""
        request = DescribeEndpointsRequest()
        # Request has no fields, just ensure it can be instantiated
        assert request is not None


class TestDescribeEndpointsResponse:
    """Test DescribeEndpointsResponse model."""

    def test_create(self):
        """Test creating response."""
        response = DescribeEndpointsResponse(
            Endpoints=[
                {"Address": "http://localhost:8000", "CachePeriodInMinutes": 1440}
            ]
        )
        assert len(response.Endpoints) == 1
        assert response.Endpoints[0].Address == "http://localhost:8000"
        assert response.Endpoints[0].CachePeriodInMinutes == 1440
