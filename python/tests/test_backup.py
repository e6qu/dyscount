"""Tests for Backup & Restore operations (M2 Phase 2)."""

import pytest
import pytest_asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from dyscount_core.config import Config, StorageSettings, ServerSettings
from dyscount_core.services.table_service import TableService
from dyscount_core.services.item_service import ItemService
from dyscount_core.models.operations import (
    CreateTableRequest,
    AttributeDefinition,
    KeySchemaElement,
    PutItemRequest,
    GetItemRequest,
    CreateBackupRequest,
    RestoreTableFromBackupRequest,
    ListBackupsRequest,
    DeleteBackupRequest,
)
from dyscount_core.models.errors import ResourceNotFoundException, TableAlreadyExistsException


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
    """Create a table with some items for backup testing."""
    service = TableService(config)
    
    # Create table
    create_request = CreateTableRequest(
        TableName="BackupTestTable",
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
    for i in range(5):
        put_request = PutItemRequest(
            TableName="BackupTestTable",
            Item={
                "pk": {"S": f"item{i}"},
                "data": {"S": f"value{i}"},
            },
        )
        await item_service.put_item(put_request)
    
    await item_service.close()
    
    yield service
    
    await service.close()


class TestCreateBackup:
    """Tests for CreateBackup operation."""
    
    @pytest.mark.asyncio
    async def test_create_backup_success(self, table_with_items, config):
        """Test creating a backup of an existing table."""
        service = table_with_items
        
        request = CreateBackupRequest(
            TableName="BackupTestTable",
            BackupName="TestBackup",
        )
        
        response = await service.create_backup(request)
        
        assert response.backup_details.backup_name == "TestBackup"
        assert response.backup_details.table_name == "BackupTestTable"
        assert response.backup_details.backup_status == "AVAILABLE"
        assert response.backup_details.backup_type == "USER"
        assert response.backup_details.backup_arn is not None
        assert response.backup_details.creation_date_time is not None
        assert response.backup_details.backup_size_bytes >= 0
    
    @pytest.mark.asyncio
    async def test_create_backup_without_name(self, table_with_items, config):
        """Test creating a backup without providing a name."""
        service = table_with_items
        
        request = CreateBackupRequest(
            TableName="BackupTestTable",
        )
        
        response = await service.create_backup(request)
        
        assert response.backup_details.backup_name is not None
        assert "BackupTestTable" in response.backup_details.backup_name
        assert response.backup_details.backup_status == "AVAILABLE"
    
    @pytest.mark.asyncio
    async def test_create_backup_table_not_found(self, config):
        """Test creating a backup of a non-existent table."""
        service = TableService(config)
        
        request = CreateBackupRequest(
            TableName="NonExistentTable",
            BackupName="TestBackup",
        )
        
        with pytest.raises(ResourceNotFoundException) as exc_info:
            await service.create_backup(request)
        
        assert "Table not found" in str(exc_info.value)
        await service.close()


class TestRestoreTableFromBackup:
    """Tests for RestoreTableFromBackup operation."""
    
    @pytest.mark.asyncio
    async def test_restore_table_success(self, table_with_items, config):
        """Test restoring a table from a backup."""
        service = table_with_items
        
        # First create a backup
        backup_request = CreateBackupRequest(
            TableName="BackupTestTable",
            BackupName="TestBackup",
        )
        backup_response = await service.create_backup(backup_request)
        backup_arn = backup_response.backup_details.backup_arn
        
        # Restore from backup
        restore_request = RestoreTableFromBackupRequest(
            BackupArn=backup_arn,
            TargetTableName="RestoredTable",
        )
        
        response = await service.restore_table_from_backup(restore_request)
        
        assert response.table_description.TableName == "RestoredTable"
        assert response.table_description.table_status == "ACTIVE"
        
        # Verify items were restored
        item_service = ItemService(config)
        for i in range(5):
            get_request = GetItemRequest(
                TableName="RestoredTable",
                Key={"pk": {"S": f"item{i}"}},
            )
            get_response = await item_service.get_item(get_request)
            assert get_response.item is not None
            assert get_response.item["data"]["S"] == f"value{i}"
        
        await item_service.close()
    
    @pytest.mark.asyncio
    async def test_restore_table_already_exists(self, table_with_items, config):
        """Test restoring to a table name that already exists."""
        service = table_with_items
        
        # First create a backup
        backup_request = CreateBackupRequest(
            TableName="BackupTestTable",
            BackupName="TestBackup",
        )
        backup_response = await service.create_backup(backup_request)
        backup_arn = backup_response.backup_details.backup_arn
        
        # Try to restore to existing table name
        restore_request = RestoreTableFromBackupRequest(
            BackupArn=backup_arn,
            TargetTableName="BackupTestTable",  # Same as original
        )
        
        with pytest.raises(TableAlreadyExistsException) as exc_info:
            await service.restore_table_from_backup(restore_request)
        
        assert "Table already exists" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_restore_backup_not_found(self, config):
        """Test restoring from a non-existent backup."""
        service = TableService(config)
        
        restore_request = RestoreTableFromBackupRequest(
            BackupArn="arn:aws:dynamodb:local:default:backup/nonexistent",
            TargetTableName="RestoredTable",
        )
        
        with pytest.raises(ResourceNotFoundException) as exc_info:
            await service.restore_table_from_backup(restore_request)
        
        assert "Backup not found" in str(exc_info.value)
        await service.close()


class TestListBackups:
    """Tests for ListBackups operation."""
    
    @pytest.mark.asyncio
    async def test_list_backups_empty(self, config):
        """Test listing backups when there are none."""
        service = TableService(config)
        
        request = ListBackupsRequest()
        response = await service.list_backups(request)
        
        assert response.backup_summaries == []
        await service.close()
    
    @pytest.mark.asyncio
    async def test_list_backups_with_data(self, table_with_items, config):
        """Test listing backups with existing backups."""
        service = table_with_items
        
        # Create multiple backups
        for i in range(3):
            backup_request = CreateBackupRequest(
                TableName="BackupTestTable",
                BackupName=f"TestBackup{i}",
            )
            await service.create_backup(backup_request)
        
        # List backups
        request = ListBackupsRequest()
        response = await service.list_backups(request)
        
        assert len(response.backup_summaries) == 3
        backup_names = [b.backup_name for b in response.backup_summaries]
        assert "TestBackup0" in backup_names
        assert "TestBackup1" in backup_names
        assert "TestBackup2" in backup_names
    
    @pytest.mark.asyncio
    async def test_list_backups_filter_by_table(self, table_with_items, config):
        """Test filtering backups by table name."""
        service = table_with_items
        
        # Create backup
        backup_request = CreateBackupRequest(
            TableName="BackupTestTable",
            BackupName="TestBackup",
        )
        await service.create_backup(backup_request)
        
        # Create another table and backup
        create_request = CreateTableRequest(
            TableName="OtherTable",
            AttributeDefinitions=[
                AttributeDefinition(AttributeName="pk", AttributeType="S"),
            ],
            KeySchema=[
                KeySchemaElement(AttributeName="pk", KeyType="HASH"),
            ],
        )
        await service.create_table(create_request)
        
        other_backup_request = CreateBackupRequest(
            TableName="OtherTable",
            BackupName="OtherBackup",
        )
        await service.create_backup(other_backup_request)
        
        # List backups for specific table
        request = ListBackupsRequest(TableName="BackupTestTable")
        response = await service.list_backups(request)
        
        assert len(response.backup_summaries) == 1
        assert response.backup_summaries[0].backup_name == "TestBackup"
    
    @pytest.mark.asyncio
    async def test_list_backups_with_limit(self, table_with_items, config):
        """Test listing backups with a limit."""
        service = table_with_items
        
        # Create multiple backups
        for i in range(5):
            backup_request = CreateBackupRequest(
                TableName="BackupTestTable",
                BackupName=f"TestBackup{i}",
            )
            await service.create_backup(backup_request)
        
        # List backups with limit
        request = ListBackupsRequest(Limit=3)
        response = await service.list_backups(request)
        
        assert len(response.backup_summaries) == 3


class TestDeleteBackup:
    """Tests for DeleteBackup operation."""
    
    @pytest.mark.asyncio
    async def test_delete_backup_success(self, table_with_items, config):
        """Test deleting a backup."""
        service = table_with_items
        
        # Create a backup
        backup_request = CreateBackupRequest(
            TableName="BackupTestTable",
            BackupName="TestBackup",
        )
        backup_response = await service.create_backup(backup_request)
        backup_arn = backup_response.backup_details.backup_arn
        
        # Delete the backup
        delete_request = DeleteBackupRequest(BackupArn=backup_arn)
        delete_response = await service.delete_backup(delete_request)
        
        assert delete_response.backup_description.backup_arn == backup_arn
        assert delete_response.backup_description.backup_status == "DELETED"
        
        # Verify backup is gone
        list_request = ListBackupsRequest()
        list_response = await service.list_backups(list_request)
        assert len(list_response.backup_summaries) == 0
    
    @pytest.mark.asyncio
    async def test_delete_backup_not_found(self, config):
        """Test deleting a non-existent backup."""
        service = TableService(config)
        
        delete_request = DeleteBackupRequest(
            BackupArn="arn:aws:dynamodb:local:default:backup/nonexistent"
        )
        
        with pytest.raises(ResourceNotFoundException) as exc_info:
            await service.delete_backup(delete_request)
        
        assert "Backup not found" in str(exc_info.value)
        await service.close()


class TestBackupE2E:
    """End-to-end tests for backup workflow."""
    
    @pytest.mark.asyncio
    async def test_full_backup_restore_cycle(self, table_with_items, config):
        """Test complete backup and restore cycle."""
        service = table_with_items
        item_service = ItemService(config)
        
        # Create backup
        backup_request = CreateBackupRequest(
            TableName="BackupTestTable",
            BackupName="FullCycleBackup",
        )
        backup_response = await service.create_backup(backup_request)
        backup_arn = backup_response.backup_details.backup_arn
        
        # Add more items to original table
        put_request = PutItemRequest(
            TableName="BackupTestTable",
            Item={
                "pk": {"S": "new_item"},
                "data": {"S": "new_value"},
            },
        )
        await item_service.put_item(put_request)
        
        # Restore to new table
        restore_request = RestoreTableFromBackupRequest(
            BackupArn=backup_arn,
            TargetTableName="RestoredTable",
        )
        await service.restore_table_from_backup(restore_request)
        
        # Verify restored table has original items but not new item
        for i in range(5):
            get_request = GetItemRequest(
                TableName="RestoredTable",
                Key={"pk": {"S": f"item{i}"}},
            )
            get_response = await item_service.get_item(get_request)
            assert get_response.item is not None
        
        # Verify new item is not in restored table
        get_request = GetItemRequest(
            TableName="RestoredTable",
            Key={"pk": {"S": "new_item"}},
        )
        get_response = await item_service.get_item(get_request)
        assert get_response.item is None
        
        # Verify new item is in original table
        get_request = GetItemRequest(
            TableName="BackupTestTable",
            Key={"pk": {"S": "new_item"}},
        )
        get_response = await item_service.get_item(get_request)
        assert get_response.item is not None
        
        await item_service.close()
