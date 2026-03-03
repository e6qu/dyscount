"""Tests for Import/Export operations (M4 Phase 1)."""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path

import pytest
import pytest_asyncio

from dyscount_core.config import Config, StorageSettings, ServerSettings, AuthSettings, LoggingSettings
from dyscount_core.models.operations import (
    CreateTableRequest,
    PutItemRequest,
    GetItemRequest,
    ExportTableToPointInTimeRequest,
    DescribeExportRequest,
    ListExportsRequest,
    ImportTableRequest,
    DescribeImportRequest,
    ListImportsRequest,
    ExportStatus,
    ImportStatus,
    S3BucketSource,
    TableCreationParameters,
    InputFormat,
)
from dyscount_core.models.table import (
    AttributeDefinition,
    KeySchemaElement,
    ScalarAttributeType,
    KeyType,
)
from dyscount_core.services.table_service import TableService
from dyscount_core.services.item_service import ItemService
from dyscount_core.services.import_export_service import ImportExportService


@pytest_asyncio.fixture
async def test_config():
    """Create a test configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config(
            server=ServerSettings(
                host="localhost",
                port=8000,
            ),
            storage=StorageSettings(
                data_directory=tmpdir,
                namespace="test",
            ),
            auth=AuthSettings(
                mode="local",
            ),
            logging=LoggingSettings(
                level="info",
                format="json",
            ),
        )
        yield config


@pytest_asyncio.fixture
async def test_table(test_config):
    """Create a test table with sample data."""
    table_service = TableService(test_config)
    item_service = ItemService(test_config)
    
    table_name = f"TestTable_{int(time.time())}"
    
    try:
        # Create table
        create_request = CreateTableRequest(
            TableName=table_name,
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="pk",
                    AttributeType=ScalarAttributeType.STRING,
                ),
            ],
            KeySchema=[
                KeySchemaElement(
                    AttributeName="pk",
                    KeyType=KeyType.HASH,
                ),
            ],
        )
        
        await table_service.create_table(create_request)
        
        # Add sample items
        for i in range(10):
            put_request = PutItemRequest(
                TableName=table_name,
                Item={
                    "pk": {"S": f"user{i}"},
                    "name": {"S": f"User {i}"},
                    "age": {"N": str(20 + i)},
                },
            )
            await item_service.put_item(put_request)
        
        yield table_name
        
    finally:
        # Cleanup
        try:
            from dyscount_core.models.operations import DeleteTableRequest
            delete_request = DeleteTableRequest(TableName=table_name)
            await table_service.delete_table(delete_request)
        except Exception:
            pass
        
        await table_service.close()
        await item_service.close()


class TestExportOperations:
    """Tests for export operations."""
    
    @pytest.mark.asyncio
    async def test_export_table_to_point_in_time(self, test_config, test_table):
        """Test ExportTableToPointInTime operation."""
        table_service = TableService(test_config)
        item_service = ItemService(test_config)
        export_service = ImportExportService(
            data_directory=test_config.storage.data_directory,
            namespace="test",
        )
        
        try:
            # Create export request
            request = ExportTableToPointInTimeRequest(
                TableArn=f"arn:aws:dynamodb:::table/{test_table}",
                S3Bucket="test-exports",
            )
            
            # Execute export
            response = await export_service.export_table_to_point_in_time(
                request=request,
                table_manager=table_service.table_manager,
                item_service=item_service,
            )
            
            # Verify response
            assert response.export_description is not None
            assert response.export_description.export_arn is not None
            assert response.export_description.export_status == ExportStatus.IN_PROGRESS
            assert response.export_description.table_arn == request.table_arn
            assert response.export_description.s3_bucket == "test-exports"
            assert response.export_description.start_time is not None
            
            # Wait for export to complete
            await asyncio.sleep(0.5)
            
            # Verify export completed
            describe_response = await export_service.describe_export(
                response.export_description.export_arn
            )
            
            # Export should be completed or still in progress
            assert describe_response.export_description.export_status in [
                ExportStatus.IN_PROGRESS,
                ExportStatus.COMPLETED,
            ]
            
        finally:
            await table_service.close()
            await item_service.close()
    
    @pytest.mark.asyncio
    async def test_describe_export(self, test_config, test_table):
        """Test DescribeExport operation."""
        table_service = TableService(test_config)
        item_service = ItemService(test_config)
        export_service = ImportExportService(
            data_directory=test_config.storage.data_directory,
            namespace="test",
        )
        
        try:
            # Create an export first
            request = ExportTableToPointInTimeRequest(
                TableArn=f"arn:aws:dynamodb:::table/{test_table}",
                S3Bucket="test-exports",
            )
            
            export_response = await export_service.export_table_to_point_in_time(
                request=request,
                table_manager=table_service.table_manager,
                item_service=item_service,
            )
            
            export_arn = export_response.export_description.export_arn
            
            # Describe the export
            describe_response = await export_service.describe_export(export_arn)
            
            # Verify description
            assert describe_response.export_description.export_arn == export_arn
            assert describe_response.export_description.export_status is not None
            assert describe_response.export_description.table_arn == request.table_arn
            
        finally:
            await table_service.close()
            await item_service.close()
    
    @pytest.mark.asyncio
    async def test_describe_export_not_found(self, test_config):
        """Test DescribeExport with non-existent export."""
        export_service = ImportExportService(
            data_directory=test_config.storage.data_directory,
            namespace="test",
        )
        
        from dyscount_core.models.errors import ResourceNotFoundException
        
        with pytest.raises(ResourceNotFoundException):
            await export_service.describe_export(
                "arn:aws:dynamodb:test:export/non-existent"
            )
    
    @pytest.mark.asyncio
    async def test_list_exports(self, test_config, test_table):
        """Test ListExports operation."""
        table_service = TableService(test_config)
        item_service = ItemService(test_config)
        export_service = ImportExportService(
            data_directory=test_config.storage.data_directory,
            namespace="test",
        )
        
        try:
            # Create multiple exports
            table_arn = f"arn:aws:dynamodb:::table/{test_table}"
            
            for i in range(3):
                request = ExportTableToPointInTimeRequest(
                    TableArn=table_arn,
                    S3Bucket=f"test-exports-{i}",
                )
                
                await export_service.export_table_to_point_in_time(
                    request=request,
                    table_manager=table_service.table_manager,
                    item_service=item_service,
                )
            
            # List exports
            list_response = await export_service.list_exports()
            
            # Verify response
            assert len(list_response.export_summaries) == 3
            
            # List with table filter
            filtered_response = await export_service.list_exports(table_arn=table_arn)
            assert len(filtered_response.export_summaries) == 3
            
            # List with pagination
            paginated_response = await export_service.list_exports(max_results=2)
            assert len(paginated_response.export_summaries) == 2
            
        finally:
            await table_service.close()
            await item_service.close()
    
    @pytest.mark.asyncio
    async def test_export_table_not_found(self, test_config):
        """Test ExportTableToPointInTime with non-existent table."""
        table_service = TableService(test_config)
        item_service = ItemService(test_config)
        export_service = ImportExportService(
            data_directory=test_config.storage.data_directory,
            namespace="test",
        )
        
        try:
            request = ExportTableToPointInTimeRequest(
                TableArn="arn:aws:dynamodb:::table/NonExistentTable",
                S3Bucket="test-exports",
            )
            
            from dyscount_core.models.errors import ResourceNotFoundException
            
            with pytest.raises(ResourceNotFoundException):
                await export_service.export_table_to_point_in_time(
                    request=request,
                    table_manager=table_service.table_manager,
                    item_service=item_service,
                )
                
        finally:
            await table_service.close()
            await item_service.close()


class TestImportOperations:
    """Tests for import operations."""
    
    @pytest.mark.asyncio
    async def test_import_table(self, test_config, test_table):
        """Test ImportTable operation."""
        table_service = TableService(test_config)
        item_service = ItemService(test_config)
        export_service = ImportExportService(
            data_directory=test_config.storage.data_directory,
            namespace="test",
        )
        
        try:
            # First, export a table
            export_request = ExportTableToPointInTimeRequest(
                TableArn=f"arn:aws:dynamodb:::table/{test_table}",
                S3Bucket="test-exports",
            )
            
            export_response = await export_service.export_table_to_point_in_time(
                request=export_request,
                table_manager=table_service.table_manager,
                item_service=item_service,
            )
            
            export_arn = export_response.export_description.export_arn
            
            # Wait for export to complete
            await asyncio.sleep(1)
            
            # Now import to a new table
            import_table_name = f"ImportedTable_{int(time.time())}"
            
            import_request = ImportTableRequest(
                InputFormat=InputFormat.DYNAMODB_JSON,
                S3BucketSource=S3BucketSource(
                    S3Bucket="test-exports",
                    S3KeyPrefix=export_arn.split("/")[-1],
                ),
                TableCreationParameters=TableCreationParameters(
                    TableName=import_table_name,
                    AttributeDefinitions=[
                        AttributeDefinition(
                            AttributeName="pk",
                            AttributeType=ScalarAttributeType.STRING,
                        ),
                    ],
                    KeySchema=[
                        KeySchemaElement(
                            AttributeName="pk",
                            KeyType=KeyType.HASH,
                        ),
                    ],
                ),
            )
            
            import_response = await export_service.import_table(
                request=import_request,
                table_manager=table_service.table_manager,
                item_service=item_service,
            )
            
            # Verify response
            assert import_response.import_table_description is not None
            assert import_response.import_table_description.import_arn is not None
            assert import_response.import_table_description.import_status == ImportStatus.IN_PROGRESS
            assert import_response.import_table_description.table_name == import_table_name
            
            # Wait for import to complete
            await asyncio.sleep(0.5)
            
            # Verify import completed
            describe_response = await export_service.describe_import(
                import_response.import_table_description.import_arn
            )
            
            assert describe_response.import_table_description.import_status in [
                ImportStatus.IN_PROGRESS,
                ImportStatus.COMPLETED,
            ]
            
            # Cleanup imported table
            try:
                from dyscount_core.models.operations import DeleteTableRequest
                await table_service.delete_table(
                    DeleteTableRequest(TableName=import_table_name)
                )
            except Exception:
                pass
                
        finally:
            await table_service.close()
            await item_service.close()
    
    @pytest.mark.asyncio
    async def test_describe_import(self, test_config, test_table):
        """Test DescribeImport operation."""
        table_service = TableService(test_config)
        item_service = ItemService(test_config)
        export_service = ImportExportService(
            data_directory=test_config.storage.data_directory,
            namespace="test",
        )
        
        try:
            # Create an import
            import_table_name = f"ImportedTable_{int(time.time())}"
            
            # Create dummy export data
            export_id = "test-export-123"
            export_dir = Path(test_config.storage.data_directory) / "test-import-bucket" / export_id
            export_dir.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                "Items": [
                    {"pk": {"S": "user1"}, "name": {"S": "User 1"}},
                    {"pk": {"S": "user2"}, "name": {"S": "User 2"}},
                ],
                "ExportMetadata": {
                    "ItemCount": 2,
                }
            }
            
            with open(export_dir / "data.json", "w") as f:
                json.dump(export_data, f)
            
            import_request = ImportTableRequest(
                InputFormat=InputFormat.DYNAMODB_JSON,
                S3BucketSource=S3BucketSource(
                    S3Bucket="test-import-bucket",
                    S3KeyPrefix=export_id,
                ),
                TableCreationParameters=TableCreationParameters(
                    TableName=import_table_name,
                    AttributeDefinitions=[
                        AttributeDefinition(
                            AttributeName="pk",
                            AttributeType=ScalarAttributeType.STRING,
                        ),
                    ],
                    KeySchema=[
                        KeySchemaElement(
                            AttributeName="pk",
                            KeyType=KeyType.HASH,
                        ),
                    ],
                ),
            )
            
            import_response = await export_service.import_table(
                request=import_request,
                table_manager=table_service.table_manager,
                item_service=item_service,
            )
            
            import_arn = import_response.import_table_description.import_arn
            
            # Describe the import
            describe_response = await export_service.describe_import(import_arn)
            
            # Verify description
            assert describe_response.import_table_description.import_arn == import_arn
            assert describe_response.import_table_description.import_status is not None
            assert describe_response.import_table_description.table_name == import_table_name
            
            # Cleanup
            try:
                from dyscount_core.models.operations import DeleteTableRequest
                await table_service.delete_table(
                    DeleteTableRequest(TableName=import_table_name)
                )
            except Exception:
                pass
                
        finally:
            await table_service.close()
            await item_service.close()
    
    @pytest.mark.asyncio
    async def test_describe_import_not_found(self, test_config):
        """Test DescribeImport with non-existent import."""
        export_service = ImportExportService(
            data_directory=test_config.storage.data_directory,
            namespace="test",
        )
        
        from dyscount_core.models.errors import ResourceNotFoundException
        
        with pytest.raises(ResourceNotFoundException):
            await export_service.describe_import(
                "arn:aws:dynamodb:test:import/non-existent"
            )
    
    @pytest.mark.asyncio
    async def test_list_imports(self, test_config):
        """Test ListImports operation."""
        export_service = ImportExportService(
            data_directory=test_config.storage.data_directory,
            namespace="test",
        )
        
        # Initially should be empty
        list_response = await export_service.list_imports()
        assert len(list_response.import_summary_list) == 0
    
    @pytest.mark.asyncio
    async def test_import_unsupported_format(self, test_config):
        """Test ImportTable with unsupported format."""
        table_service = TableService(test_config)
        item_service = ItemService(test_config)
        export_service = ImportExportService(
            data_directory=test_config.storage.data_directory,
            namespace="test",
        )
        
        try:
            import_request = ImportTableRequest(
                InputFormat=InputFormat.CSV,  # Not yet supported
                S3BucketSource=S3BucketSource(S3Bucket="test-bucket"),
                TableCreationParameters=TableCreationParameters(
                    TableName="TestTable",
                    AttributeDefinitions=[
                        AttributeDefinition(
                            AttributeName="pk",
                            AttributeType=ScalarAttributeType.STRING,
                        ),
                    ],
                    KeySchema=[
                        KeySchemaElement(
                            AttributeName="pk",
                            KeyType=KeyType.HASH,
                        ),
                    ],
                ),
            )
            
            from dyscount_core.models.errors import ValidationException
            
            with pytest.raises(ValidationException) as exc_info:
                await export_service.import_table(
                    request=import_request,
                    table_manager=table_service.table_manager,
                    item_service=item_service,
                )
            
            assert "not yet supported" in str(exc_info.value)
            
        finally:
            await table_service.close()
            await item_service.close()


class TestExportImportRoundTrip:
    """Tests for export-import round-trip scenarios."""
    
    @pytest.mark.asyncio
    async def test_export_import_round_trip(self, test_config, test_table):
        """Test full export-import round-trip."""
        table_service = TableService(test_config)
        item_service = ItemService(test_config)
        export_service = ImportExportService(
            data_directory=test_config.storage.data_directory,
            namespace="test",
        )
        
        try:
            # Step 1: Export the original table
            export_request = ExportTableToPointInTimeRequest(
                TableArn=f"arn:aws:dynamodb:::table/{test_table}",
                S3Bucket="test-exports",
            )
            
            export_response = await export_service.export_table_to_point_in_time(
                request=export_request,
                table_manager=table_service.table_manager,
                item_service=item_service,
            )
            
            export_arn = export_response.export_description.export_arn
            
            # Wait for export to complete
            max_wait = 5
            waited = 0
            while waited < max_wait:
                describe_export = await export_service.describe_export(export_arn)
                if describe_export.export_description.export_status == ExportStatus.COMPLETED:
                    break
                await asyncio.sleep(0.5)
                waited += 0.5
            
            assert describe_export.export_description.export_status == ExportStatus.COMPLETED
            
            # Step 2: Import to a new table
            import_table_name = f"RoundTripTable_{int(time.time())}"
            
            import_request = ImportTableRequest(
                InputFormat=InputFormat.DYNAMODB_JSON,
                S3BucketSource=S3BucketSource(
                    S3Bucket="test-exports",
                    S3KeyPrefix=export_arn.split("/")[-1],
                ),
                TableCreationParameters=TableCreationParameters(
                    TableName=import_table_name,
                    AttributeDefinitions=[
                        AttributeDefinition(
                            AttributeName="pk",
                            AttributeType=ScalarAttributeType.STRING,
                        ),
                    ],
                    KeySchema=[
                        KeySchemaElement(
                            AttributeName="pk",
                            KeyType=KeyType.HASH,
                        ),
                    ],
                ),
            )
            
            import_response = await export_service.import_table(
                request=import_request,
                table_manager=table_service.table_manager,
                item_service=item_service,
            )
            
            import_arn = import_response.import_table_description.import_arn
            
            # Wait for import to complete
            waited = 0
            while waited < max_wait:
                describe_import = await export_service.describe_import(import_arn)
                if describe_import.import_table_description.import_status == ImportStatus.COMPLETED:
                    break
                await asyncio.sleep(0.5)
                waited += 0.5
            
            assert describe_import.import_table_description.import_status == ImportStatus.COMPLETED
            
            # Step 3: Verify imported data
            get_request = GetItemRequest(
                TableName=import_table_name,
                Key={"pk": {"S": "user0"}},
            )
            
            get_response = await item_service.get_item(get_request)
            assert get_response.item is not None
            assert get_response.item["pk"] == {"S": "user0"}
            assert "name" in get_response.item
            
            # Cleanup imported table
            try:
                from dyscount_core.models.operations import DeleteTableRequest
                await table_service.delete_table(
                    DeleteTableRequest(TableName=import_table_name)
                )
            except Exception:
                pass
                
        finally:
            await table_service.close()
            await item_service.close()
