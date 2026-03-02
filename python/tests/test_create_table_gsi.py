"""Tests for CreateTable with Global Secondary Indexes (GSI)."""

import tempfile

import pytest
from dyscount_core.models.operations import CreateTableRequest
from dyscount_core.models.table import (
    AttributeDefinition,
    GlobalSecondaryIndex,
    KeySchemaElement,
    KeyType,
    ProvisionedThroughput,
    ScalarAttributeType,
)
from dyscount_core.models.errors import ValidationException
from dyscount_core.config import Config, LoggingSettings, ServerSettings, StorageSettings
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
async def table_service(config):
    """Create a table service for testing."""
    service = TableService(config)
    yield service
    await service.close()


class TestCreateTableGSI:
    """Test CreateTable with Global Secondary Indexes."""
    
    @pytest.mark.asyncio
    async def test_create_table_with_single_gsi(self, table_service):
        """Should create table with a single GSI."""
        request = CreateTableRequest(
            TableName="TestTableWithGSI",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi_pk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexes=[
                GlobalSecondaryIndex(
                    IndexName="TestGSI",
                    KeySchema=[
                        KeySchemaElement(AttributeName="gsi_pk", KeyType=KeyType.HASH),
                    ],
                    Projection={"ProjectionType": "ALL"},
                )
            ],
        )
        
        response = await table_service.create_table(request)
        
        # Verify response
        assert response.TableDescription.TableName == "TestTableWithGSI"
        assert response.TableDescription.GlobalSecondaryIndexes is not None
        assert len(response.TableDescription.GlobalSecondaryIndexes) == 1
        
        gsi = response.TableDescription.GlobalSecondaryIndexes[0]
        assert gsi.IndexName == "TestGSI"
        assert len(gsi.KeySchema) == 1
        assert gsi.KeySchema[0].AttributeName == "gsi_pk"
        assert gsi.KeySchema[0].KeyType == KeyType.HASH
    
    @pytest.mark.asyncio
    async def test_create_table_with_gsi_composite_key(self, table_service):
        """Should create table with GSI that has composite key."""
        request = CreateTableRequest(
            TableName="TestTableWithCompositeGSI",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi_pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi_sk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexes=[
                GlobalSecondaryIndex(
                    IndexName="TestGSI",
                    KeySchema=[
                        KeySchemaElement(AttributeName="gsi_pk", KeyType=KeyType.HASH),
                        KeySchemaElement(AttributeName="gsi_sk", KeyType=KeyType.RANGE),
                    ],
                    Projection={"ProjectionType": "ALL"},
                )
            ],
        )
        
        response = await table_service.create_table(request)
        
        # Verify GSI with composite key
        gsi = response.TableDescription.GlobalSecondaryIndexes[0]
        assert gsi.IndexName == "TestGSI"
        assert len(gsi.KeySchema) == 2
        assert gsi.KeySchema[0].AttributeName == "gsi_pk"
        assert gsi.KeySchema[1].AttributeName == "gsi_sk"
    
    @pytest.mark.asyncio
    async def test_create_table_with_multiple_gsi(self, table_service):
        """Should create table with multiple GSIs."""
        request = CreateTableRequest(
            TableName="TestTableWithMultipleGSI",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi1_pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi2_pk", AttributeType=ScalarAttributeType.NUMBER),
            ],
            GlobalSecondaryIndexes=[
                GlobalSecondaryIndex(
                    IndexName="GSI1",
                    KeySchema=[
                        KeySchemaElement(AttributeName="gsi1_pk", KeyType=KeyType.HASH),
                    ],
                    Projection={"ProjectionType": "ALL"},
                ),
                GlobalSecondaryIndex(
                    IndexName="GSI2",
                    KeySchema=[
                        KeySchemaElement(AttributeName="gsi2_pk", KeyType=KeyType.HASH),
                    ],
                    Projection={"ProjectionType": "KEYS_ONLY"},
                ),
            ],
        )
        
        response = await table_service.create_table(request)
        
        # Verify multiple GSIs
        assert len(response.TableDescription.GlobalSecondaryIndexes) == 2
        index_names = {gsi.IndexName for gsi in response.TableDescription.GlobalSecondaryIndexes}
        assert "GSI1" in index_names
        assert "GSI2" in index_names
    
    @pytest.mark.asyncio
    async def test_create_table_gsi_with_projection_include(self, table_service):
        """Should create GSI with INCLUDE projection type."""
        request = CreateTableRequest(
            TableName="TestTableWithIncludeGSI",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi_pk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexes=[
                GlobalSecondaryIndex(
                    IndexName="IncludeGSI",
                    KeySchema=[
                        KeySchemaElement(AttributeName="gsi_pk", KeyType=KeyType.HASH),
                    ],
                    Projection={"ProjectionType": "INCLUDE", "NonKeyAttributes": ["attr1", "attr2"]},
                )
            ],
        )
        
        response = await table_service.create_table(request)
        
        gsi = response.TableDescription.GlobalSecondaryIndexes[0]
        assert gsi.Projection["ProjectionType"] == "INCLUDE"
        assert gsi.Projection["NonKeyAttributes"] == ["attr1", "attr2"]
    
    @pytest.mark.asyncio
    async def test_create_table_gsi_with_provisioned_throughput(self, table_service):
        """Should create GSI with provisioned throughput."""
        request = CreateTableRequest(
            TableName="TestTableWithProvisionedGSI",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi_pk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexes=[
                GlobalSecondaryIndex(
                    IndexName="ProvisionedGSI",
                    KeySchema=[
                        KeySchemaElement(AttributeName="gsi_pk", KeyType=KeyType.HASH),
                    ],
                    Projection={"ProjectionType": "ALL"},
                    ProvisionedThroughput=ProvisionedThroughput(
                        ReadCapacityUnits=10,
                        WriteCapacityUnits=5
                    ),
                )
            ],
        )
        
        response = await table_service.create_table(request)
        
        gsi = response.TableDescription.GlobalSecondaryIndexes[0]
        assert gsi.ProvisionedThroughput is not None
        # ProvisionedThroughput is stored as dict
        assert gsi.ProvisionedThroughput["ReadCapacityUnits"] == 10
        assert gsi.ProvisionedThroughput["WriteCapacityUnits"] == 5


class TestCreateTableGSIValidation:
    """Test GSI validation during CreateTable."""
    
    @pytest.mark.asyncio
    async def test_gsi_missing_attribute_definition(self, table_service):
        """Should reject GSI with undefined key attributes."""
        request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                # Missing gsi_pk attribute definition
            ],
            GlobalSecondaryIndexes=[
                GlobalSecondaryIndex(
                    IndexName="TestGSI",
                    KeySchema=[
                        KeySchemaElement(AttributeName="gsi_pk", KeyType=KeyType.HASH),
                    ],
                    Projection={"ProjectionType": "ALL"},
                )
            ],
        )
        
        with pytest.raises(ValidationException) as exc_info:
            await table_service.create_table(request)
        
        assert "gsi_pk" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_gsi_missing_index_name(self, table_service):
        """Should reject GSI without index name."""
        request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi_pk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexes=[
                GlobalSecondaryIndex(
                    IndexName="",  # Empty name
                    KeySchema=[
                        KeySchemaElement(AttributeName="gsi_pk", KeyType=KeyType.HASH),
                    ],
                    Projection={"ProjectionType": "ALL"},
                )
            ],
        )
        
        with pytest.raises(ValidationException) as exc_info:
            await table_service.create_table(request)
        
        assert "IndexName" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_gsi_empty_key_schema(self, table_service):
        """Should reject GSI with empty key schema."""
        request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexes=[
                GlobalSecondaryIndex(
                    IndexName="TestGSI",
                    KeySchema=[],  # Empty key schema
                    Projection={"ProjectionType": "ALL"},
                )
            ],
        )
        
        with pytest.raises(ValidationException) as exc_info:
            await table_service.create_table(request)
        
        assert "KeySchema" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_gsi_too_many_indexes(self, table_service):
        """Should reject more than 20 GSIs."""
        gsis = []
        attr_defs = [
            AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
        ]
        
        for i in range(21):
            attr_name = f"gsi{i}_pk"
            attr_defs.append(AttributeDefinition(AttributeName=attr_name, AttributeType=ScalarAttributeType.STRING))
            gsis.append(
                GlobalSecondaryIndex(
                    IndexName=f"GSI{i}",
                    KeySchema=[
                        KeySchemaElement(AttributeName=attr_name, KeyType=KeyType.HASH),
                    ],
                    Projection={"ProjectionType": "ALL"},
                )
            )
        
        request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=attr_defs,
            GlobalSecondaryIndexes=gsis,
        )
        
        with pytest.raises(ValidationException) as exc_info:
            await table_service.create_table(request)
        
        assert "20" in str(exc_info.value)


class TestCreateTableLSI:
    """Test CreateTable with Local Secondary Indexes."""
    
    @pytest.mark.asyncio
    async def test_create_table_with_lsi(self, table_service):
        """Should create table with LSI on composite key table."""
        from dyscount_core.models.table import LocalSecondaryIndex
        
        request = CreateTableRequest(
            TableName="TestTableWithLSI",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
                KeySchemaElement(AttributeName="sk", KeyType=KeyType.RANGE),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="sk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="lsi_sk", AttributeType=ScalarAttributeType.STRING),
            ],
            LocalSecondaryIndexes=[
                LocalSecondaryIndex(
                    IndexName="TestLSI",
                    KeySchema=[
                        KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
                        KeySchemaElement(AttributeName="lsi_sk", KeyType=KeyType.RANGE),
                    ],
                    Projection={"ProjectionType": "ALL"},
                )
            ],
        )
        
        response = await table_service.create_table(request)
        
        # Verify response
        assert response.TableDescription.TableName == "TestTableWithLSI"
        assert response.TableDescription.LocalSecondaryIndexes is not None
        assert len(response.TableDescription.LocalSecondaryIndexes) == 1
        
        lsi = response.TableDescription.LocalSecondaryIndexes[0]
        assert lsi.IndexName == "TestLSI"
        assert len(lsi.KeySchema) == 2
        assert lsi.KeySchema[0].AttributeName == "pk"  # Same as table hash key
        assert lsi.KeySchema[1].AttributeName == "lsi_sk"
    
    @pytest.mark.asyncio
    async def test_lsi_on_simple_key_table_rejected(self, table_service):
        """Should reject LSI on table with only hash key."""
        from dyscount_core.models.table import LocalSecondaryIndex
        
        request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="lsi_sk", AttributeType=ScalarAttributeType.STRING),
            ],
            LocalSecondaryIndexes=[
                LocalSecondaryIndex(
                    IndexName="TestLSI",
                    KeySchema=[
                        KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
                        KeySchemaElement(AttributeName="lsi_sk", KeyType=KeyType.RANGE),
                    ],
                    Projection={"ProjectionType": "ALL"},
                )
            ],
        )
        
        with pytest.raises(ValidationException) as exc_info:
            await table_service.create_table(request)
        
        assert "composite" in str(exc_info.value).lower() or "LocalSecondaryIndexes" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_lsi_wrong_hash_key_rejected(self, table_service):
        """Should reject LSI with different hash key than table."""
        from dyscount_core.models.table import LocalSecondaryIndex
        
        request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
                KeySchemaElement(AttributeName="sk", KeyType=KeyType.RANGE),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="sk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="wrong_pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="lsi_sk", AttributeType=ScalarAttributeType.STRING),
            ],
            LocalSecondaryIndexes=[
                LocalSecondaryIndex(
                    IndexName="TestLSI",
                    KeySchema=[
                        KeySchemaElement(AttributeName="wrong_pk", KeyType=KeyType.HASH),  # Wrong hash key
                        KeySchemaElement(AttributeName="lsi_sk", KeyType=KeyType.RANGE),
                    ],
                    Projection={"ProjectionType": "ALL"},
                )
            ],
        )
        
        with pytest.raises(ValidationException) as exc_info:
            await table_service.create_table(request)
        
        assert "hash key" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_lsi_too_many_indexes(self, table_service):
        """Should reject more than 5 LSIs."""
        from dyscount_core.models.table import LocalSecondaryIndex
        
        lsis = []
        attr_defs = [
            AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
            AttributeDefinition(AttributeName="sk", AttributeType=ScalarAttributeType.STRING),
        ]
        
        for i in range(6):
            attr_name = f"lsi{i}_sk"
            attr_defs.append(AttributeDefinition(AttributeName=attr_name, AttributeType=ScalarAttributeType.STRING))
            lsis.append(
                LocalSecondaryIndex(
                    IndexName=f"LSI{i}",
                    KeySchema=[
                        KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
                        KeySchemaElement(AttributeName=attr_name, KeyType=KeyType.RANGE),
                    ],
                    Projection={"ProjectionType": "ALL"},
                )
            )
        
        request = CreateTableRequest(
            TableName="TestTable",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
                KeySchemaElement(AttributeName="sk", KeyType=KeyType.RANGE),
            ],
            AttributeDefinitions=attr_defs,
            LocalSecondaryIndexes=lsis,
        )
        
        with pytest.raises(ValidationException) as exc_info:
            await table_service.create_table(request)
        
        assert "5" in str(exc_info.value)


class TestCreateTableMixedIndexes:
    """Test CreateTable with both GSI and LSI."""
    
    @pytest.mark.asyncio
    async def test_create_table_with_gsi_and_lsi(self, table_service):
        """Should create table with both GSI and LSI."""
        from dyscount_core.models.table import LocalSecondaryIndex
        
        request = CreateTableRequest(
            TableName="TestTableWithBothIndexes",
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
                KeySchemaElement(AttributeName="sk", KeyType=KeyType.RANGE),
            ],
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="sk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi_pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="lsi_sk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexes=[
                GlobalSecondaryIndex(
                    IndexName="TestGSI",
                    KeySchema=[
                        KeySchemaElement(AttributeName="gsi_pk", KeyType=KeyType.HASH),
                    ],
                    Projection={"ProjectionType": "ALL"},
                )
            ],
            LocalSecondaryIndexes=[
                LocalSecondaryIndex(
                    IndexName="TestLSI",
                    KeySchema=[
                        KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
                        KeySchemaElement(AttributeName="lsi_sk", KeyType=KeyType.RANGE),
                    ],
                    Projection={"ProjectionType": "ALL"},
                )
            ],
        )
        
        response = await table_service.create_table(request)
        
        # Verify both indexes exist
        assert response.TableDescription.GlobalSecondaryIndexes is not None
        assert response.TableDescription.LocalSecondaryIndexes is not None
        assert len(response.TableDescription.GlobalSecondaryIndexes) == 1
        assert len(response.TableDescription.LocalSecondaryIndexes) == 1
        
        gsi_names = {gsi.IndexName for gsi in response.TableDescription.GlobalSecondaryIndexes}
        lsi_names = {lsi.IndexName for lsi in response.TableDescription.LocalSecondaryIndexes}
        
        assert "TestGSI" in gsi_names
        assert "TestLSI" in lsi_names
