"""Tests for UpdateTable with Global Secondary Index operations."""

import tempfile

import pytest
from dyscount_core.models.operations import (
    CreateTableRequest,
    UpdateTableRequest,
)
from dyscount_core.models.table import (
    AttributeDefinition,
    GlobalSecondaryIndex,
    KeySchemaElement,
    KeyType,
    ScalarAttributeType,
)
from dyscount_core.models.errors import ValidationException, ResourceNotFoundException
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


@pytest.fixture
async def test_table(table_service):
    """Create a test table without GSI."""
    request = CreateTableRequest(
        TableName="TestTableForUpdate",
        KeySchema=[
            KeySchemaElement(AttributeName="pk", KeyType=KeyType.HASH),
        ],
        AttributeDefinitions=[
            AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
            AttributeDefinition(AttributeName="gsi_pk", AttributeType=ScalarAttributeType.STRING),
        ],
    )
    
    await table_service.create_table(request)
    yield "TestTableForUpdate"


class TestUpdateTableCreateGSI:
    """Test creating GSIs via UpdateTable."""
    
    @pytest.mark.asyncio
    async def test_update_table_create_single_gsi(self, table_service, test_table):
        """Should create a single GSI via UpdateTable."""
        update_request = UpdateTableRequest(
            TableName=test_table,
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi_pk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    "Create": {
                        "IndexName": "NewGSI",
                        "KeySchema": [
                            {"AttributeName": "gsi_pk", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                }
            ],
        )
        
        response = await table_service.update_table(update_request)
        
        # Verify GSI was created
        assert response.TableDescription.GlobalSecondaryIndexes is not None
        assert len(response.TableDescription.GlobalSecondaryIndexes) == 1
        
        gsi = response.TableDescription.GlobalSecondaryIndexes[0]
        assert gsi.IndexName == "NewGSI"
        assert gsi.KeySchema[0].AttributeName == "gsi_pk"
    
    @pytest.mark.asyncio
    async def test_update_table_create_multiple_gsi(self, table_service, test_table):
        """Should create multiple GSIs via UpdateTable."""
        update_request = UpdateTableRequest(
            TableName=test_table,
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi_pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi2_pk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    "Create": {
                        "IndexName": "GSI1",
                        "KeySchema": [
                            {"AttributeName": "gsi_pk", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                },
                {
                    "Create": {
                        "IndexName": "GSI2",
                        "KeySchema": [
                            {"AttributeName": "gsi2_pk", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "KEYS_ONLY"},
                    }
                },
            ],
        )
        
        response = await table_service.update_table(update_request)
        
        # Verify both GSIs were created
        assert len(response.TableDescription.GlobalSecondaryIndexes) == 2
        index_names = {gsi.IndexName for gsi in response.TableDescription.GlobalSecondaryIndexes}
        assert "GSI1" in index_names
        assert "GSI2" in index_names
    
    @pytest.mark.asyncio
    async def test_update_table_create_gsi_with_provisioned_throughput(self, table_service, test_table):
        """Should create GSI with provisioned throughput."""
        update_request = UpdateTableRequest(
            TableName=test_table,
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi_pk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    "Create": {
                        "IndexName": "ProvisionedGSI",
                        "KeySchema": [
                            {"AttributeName": "gsi_pk", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 10,
                            "WriteCapacityUnits": 5,
                        },
                    }
                }
            ],
        )
        
        response = await table_service.update_table(update_request)
        
        gsi = response.TableDescription.GlobalSecondaryIndexes[0]
        assert gsi.IndexName == "ProvisionedGSI"
        assert gsi.ProvisionedThroughput is not None
        assert gsi.ProvisionedThroughput["ReadCapacityUnits"] == 10
        assert gsi.ProvisionedThroughput["WriteCapacityUnits"] == 5
    
    @pytest.mark.asyncio
    async def test_update_table_create_gsi_duplicate_name(self, table_service, test_table):
        """Should reject creating GSI with duplicate name."""
        # First, create a GSI
        update_request = UpdateTableRequest(
            TableName=test_table,
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi_pk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    "Create": {
                        "IndexName": "DuplicateGSI",
                        "KeySchema": [
                            {"AttributeName": "gsi_pk", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                }
            ],
        )
        
        await table_service.update_table(update_request)
        
        # Try to create another GSI with the same name
        with pytest.raises(ValidationException) as exc_info:
            await table_service.update_table(update_request)
        
        assert "already exists" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_table_create_gsi_exceeds_limit(self, table_service, test_table):
        """Should reject creating more than 20 GSIs."""
        # Create GSIs up to the limit
        attr_defs = [
            AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
        ]
        gsi_updates = []
        
        for i in range(20):
            attr_name = f"gsi{i}_pk"
            attr_defs.append(AttributeDefinition(AttributeName=attr_name, AttributeType=ScalarAttributeType.STRING))
            gsi_updates.append({
                "Create": {
                    "IndexName": f"GSI{i}",
                    "KeySchema": [{"AttributeName": attr_name, "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            })
        
        update_request = UpdateTableRequest(
            TableName=test_table,
            AttributeDefinitions=attr_defs,
            GlobalSecondaryIndexUpdates=gsi_updates,
        )
        
        await table_service.update_table(update_request)
        
        # Try to create one more GSI
        extra_update = UpdateTableRequest(
            TableName=test_table,
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="extra_gsi_pk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    "Create": {
                        "IndexName": "ExtraGSI",
                        "KeySchema": [{"AttributeName": "extra_gsi_pk", "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                }
            ],
        )
        
        with pytest.raises(ValidationException) as exc_info:
            await table_service.update_table(extra_update)
        
        assert "20" in str(exc_info.value)


class TestUpdateTableDeleteGSI:
    """Test deleting GSIs via UpdateTable."""
    
    @pytest.mark.asyncio
    async def test_update_table_delete_gsi(self, table_service, test_table):
        """Should delete a GSI via UpdateTable."""
        # First create a GSI
        create_request = UpdateTableRequest(
            TableName=test_table,
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="gsi_pk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    "Create": {
                        "IndexName": "GSIToDelete",
                        "KeySchema": [
                            {"AttributeName": "gsi_pk", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                }
            ],
        )
        
        await table_service.update_table(create_request)
        
        # Now delete the GSI
        delete_request = UpdateTableRequest(
            TableName=test_table,
            GlobalSecondaryIndexUpdates=[
                {
                    "Delete": {
                        "IndexName": "GSIToDelete",
                    }
                }
            ],
        )
        
        response = await table_service.update_table(delete_request)
        
        # Verify GSI was deleted
        assert response.TableDescription.GlobalSecondaryIndexes is None or len(response.TableDescription.GlobalSecondaryIndexes) == 0
    
    @pytest.mark.asyncio
    async def test_update_table_delete_nonexistent_gsi(self, table_service, test_table):
        """Should reject deleting non-existent GSI."""
        delete_request = UpdateTableRequest(
            TableName=test_table,
            GlobalSecondaryIndexUpdates=[
                {
                    "Delete": {
                        "IndexName": "NonExistentGSI",
                    }
                }
            ],
        )
        
        with pytest.raises(ResourceNotFoundException) as exc_info:
            await table_service.update_table(delete_request)
        
        assert "not found" in str(exc_info.value).lower()


class TestUpdateTableMixedOperations:
    """Test mixed GSI operations in single UpdateTable call."""
    
    @pytest.mark.asyncio
    async def test_update_table_create_and_delete_gsi(self, table_service, test_table):
        """Should handle create and delete in same UpdateTable."""
        # First create a GSI to delete
        create_request = UpdateTableRequest(
            TableName=test_table,
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="old_gsi_pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="new_gsi_pk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    "Create": {
                        "IndexName": "OldGSI",
                        "KeySchema": [
                            {"AttributeName": "old_gsi_pk", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                }
            ],
        )
        
        await table_service.update_table(create_request)
        
        # Now delete old GSI and create new one
        mixed_request = UpdateTableRequest(
            TableName=test_table,
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="old_gsi_pk", AttributeType=ScalarAttributeType.STRING),
                AttributeDefinition(AttributeName="new_gsi_pk", AttributeType=ScalarAttributeType.STRING),
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    "Delete": {
                        "IndexName": "OldGSI",
                    }
                },
                {
                    "Create": {
                        "IndexName": "NewGSI",
                        "KeySchema": [
                            {"AttributeName": "new_gsi_pk", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                },
            ],
        )
        
        response = await table_service.update_table(mixed_request)
        
        # Verify: OldGSI deleted, NewGSI created
        gs_is = response.TableDescription.GlobalSecondaryIndexes
        assert len(gs_is) == 1
        assert gs_is[0].IndexName == "NewGSI"


class TestUpdateTableOtherSettings:
    """Test updating other table settings via UpdateTable."""
    
    @pytest.mark.asyncio
    async def test_update_table_provisioned_throughput(self, table_service, test_table):
        """Should update table provisioned throughput."""
        update_request = UpdateTableRequest(
            TableName=test_table,
            ProvisionedThroughput={
                "ReadCapacityUnits": 25,
                "WriteCapacityUnits": 15,
            },
        )
        
        response = await table_service.update_table(update_request)
        
        assert response.TableDescription.provisioned_throughput["ReadCapacityUnits"] == 25
        assert response.TableDescription.provisioned_throughput["WriteCapacityUnits"] == 15
    
    @pytest.mark.asyncio
    async def test_update_table_billing_mode(self, table_service, test_table):
        """Should update table billing mode."""
        from dyscount_core.models.table import BillingMode
        
        update_request = UpdateTableRequest(
            TableName=test_table,
            BillingMode=BillingMode.PAY_PER_REQUEST,
        )
        
        response = await table_service.update_table(update_request)
        
        assert response.TableDescription.billing_mode_summary["BillingMode"] == "PAY_PER_REQUEST"
    
    @pytest.mark.asyncio
    async def test_update_table_deletion_protection(self, table_service, test_table):
        """Should update table deletion protection."""
        update_request = UpdateTableRequest(
            TableName=test_table,
            DeletionProtectionEnabled=True,
        )
        
        response = await table_service.update_table(update_request)
        
        assert response.TableDescription.DeletionProtectionEnabled is True
    
    @pytest.mark.asyncio
    async def test_update_table_table_not_found(self, table_service):
        """Should reject UpdateTable for non-existent table."""
        update_request = UpdateTableRequest(
            TableName="NonExistentTable",
            ProvisionedThroughput={
                "ReadCapacityUnits": 10,
                "WriteCapacityUnits": 5,
            },
        )
        
        with pytest.raises(ResourceNotFoundException) as exc_info:
            await table_service.update_table(update_request)
        
        assert "not found" in str(exc_info.value).lower()
